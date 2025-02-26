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
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY local_vendor_code 
                            ORDER BY created_at DESC
                        ) AS rn
                    FROM cost_price
                )
                SELECT 
                    article.account, 
                    lcp.purchase_price,
                    lcp.status_by_lvc,
                    lcp.local_vendor_code,
                    cd.*
                FROM 
                    article
                INNER JOIN 
                    LatestCostPrice lcp
                ON 
                    article.local_vendor_code = lcp.local_vendor_code
                join card_data cd
                on article.nm_id = cd.article_id
                WHERE 
                    lcp.rn = 1;
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
