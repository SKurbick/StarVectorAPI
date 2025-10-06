import json

from asyncpg import Pool, Record
from collections import defaultdict
from typing import Any

from app.domain.models import  ArticleResponse, ProductResponse, SubjectDataWithProductsResponse


ProductsData = defaultdict[str, str | int | None | list[ArticleResponse]]
SubjectsData = defaultdict[str, ProductsData]


class ProductRepository:
    """Репозиторий для работы с товарами в базе данных."""

    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_products_grouped_by_subjects(
        self,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[SubjectDataWithProductsResponse]:
        """Получить список товаров с группировкой по предметам."""
        query = """
                WITH all_cards_data AS (
                    SELECT
                        a.local_vendor_code,
                        cd.subject_name,
                        json_agg(
                            json_build_object(
                                'article_id', cd.article_id,
                                'subject_name', cd.subject_name,
                                'photo_link', cd.photo_link,
                                'price', cd.price,
                                'discount', cd.discount,
                                'length', cd.length,
                                'width', cd.width,
                                'height', cd.height,
                                'barcode', cd.barcode,
                                'rating', cd.rating,
                                'manager', cd.manager
                            )
                        ) AS cards
                    FROM 
                        article a
                    JOIN 
                        card_data AS cd
                        ON a.nm_id = cd.article_id
                    GROUP BY 
                        a.local_vendor_code, cd.subject_name 
                )
                SELECT
                    p.id,
                    p.name,
                    p.photo_link,
                    p.length,
                    p.width,
                    p.height,
                    p.manager,
                    acd.subject_name,
                    COALESCE(acd.cards, '[]') AS articles 
                FROM 
                    products p
                LEFT JOIN
                    all_cards_data acd
                    on acd.local_vendor_code = p.id
                ORDER BY
                    acd.subject_name,
                    p.id
                LIMIT $1
                OFFSET $2;
            """

        async with self.pool.acquire() as connection:
            data = await connection.fetch(query, limit, offset)

        return self.transform_asyncpg_data_to_subjects_response(data)

    @staticmethod
    def transform_asyncpg_data_to_subjects_response(
        data: list[Record]
    ) -> list[SubjectDataWithProductsResponse]:
        subjects_data = defaultdict(lambda: [])

        for row in data:
            subject_name = row["subject_name"]
            articles_data = json.loads(row["articles"])

            subjects_data[subject_name].append(
                ProductResponse(
                    id=row["id"],
                    name=row["name"],
                    photo_link=row["photo_link"],
                    length=row["length"],
                    width=row["width"],
                    height=row["height"],
                    manager=row["manager"],
                    articles=[ArticleResponse(**article) for article in articles_data],
                )
            )

        return [SubjectDataWithProductsResponse(
            subject_name=name,
            products=products
        ) for name, products in subjects_data.items()]
