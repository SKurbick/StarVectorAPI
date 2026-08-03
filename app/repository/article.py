from typing import List

from asyncpg import Pool
from pydantic import ValidationError

from app.domain.models import ArticleDetails


class ArticleRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_article_details(self) -> List[ArticleDetails]:
        async with self.pool.acquire() as conn:
            query = """
            WITH LatestCostPrice AS (
                SELECT
                    local_vendor_code,
                    purchase_price,
                    status_by_lvc,
                    created_at
                FROM (
                    SELECT
                        local_vendor_code,
                        purchase_price,
                        status_by_lvc,
                        created_at,
                        ROW_NUMBER() OVER (
                            PARTITION BY local_vendor_code
                            ORDER BY created_at DESC
                        ) AS rn
                    FROM cost_price
                ) t
                WHERE rn = 1
            ), FeedbackCounts AS (
                SELECT
                    nmid AS article_id,
                    COUNT(*) AS reviews_count
                FROM wb_feedbacks
                GROUP BY nmid
            )
            SELECT
                a.account,
                lcp.purchase_price,
                lcp.status_by_lvc,
                a.local_vendor_code,
                cd.article_id,
                cd.barcode,
                cd.subject_name,
                cd.photo_link,
                cd.length,
                cd.width,
                cd.height,
                cd.rating,
                COALESCE(fc.reviews_count, 0) AS reviews_count,
                cd.manager,
                cd.local_card_name,
                cd.chrt_id,
                crfs.stocks_quantity,
                pn.note
            FROM
                article a
            LEFT JOIN
                LatestCostPrice lcp
                ON a.local_vendor_code = lcp.local_vendor_code
            INNER JOIN
                card_data cd
                ON a.nm_id = cd.article_id
            LEFT JOIN
                current_real_fbs_stocks_qty crfs
                ON a.local_vendor_code = crfs.local_vendor_code
            LEFT JOIN product_notes pn
            	on a.nm_id = pn.nm_id and a.account = pn.account and a.local_vendor_code = pn.local_vendor_code
            LEFT JOIN FeedbackCounts fc
                ON fc.article_id = a.nm_id;
                            """
            rows = await conn.fetch(query)
            result = []
            for row in rows:
                try:
                    # Преобразуем row в словарь
                    row_dict = dict(row)

                    # Создаем экземпляр плоской модели
                    flat_article_details = ArticleDetails.model_validate(row_dict)

                    result.append(flat_article_details)

                except ValidationError as e:
                    # Логируем ошибку валидации и пропускаем текущую строку
                    print(f"Validation error for row {row}: {e}")
                    continue

            return result
