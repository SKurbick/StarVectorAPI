from pprint import pprint
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
            )
            SELECT 
                a.account, 
                lcp.purchase_price,
                lcp.status_by_lvc,
                lcp.local_vendor_code,
                -- Явно перечисляем нужные поля из card_data вместо cd.*
                cd.article_id,
                cd.barcode,
                cd.article_id,
                cd.subject_name,
                cd.photo_link,
                cd.length,
                cd.width,
                cd.height,
                cd.barcode,
                cd.rating,
                cd.manager,
                cd.local_card_name,
                -- Добавляем остальные нужные поля из card_data...
                crfs.stocks_quantity
            FROM 
                article a
            INNER JOIN 
                LatestCostPrice lcp
                ON a.local_vendor_code = lcp.local_vendor_code
            INNER JOIN 
                card_data cd
                ON a.nm_id = cd.article_id
            LEFT JOIN 
                current_real_fbs_stocks_qty crfs 
                ON a.local_vendor_code = crfs.local_vendor_code;
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
