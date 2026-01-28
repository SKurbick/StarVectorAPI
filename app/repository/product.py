from collections import defaultdict
import json

from asyncpg import Pool

from app.domain.models import  ArticleResponse, ProductResponse, SubjectDataWithProductsResponse, ProductCard


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
                INNER JOIN
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
                coalesce(acd.cards, '[]') AS articles
            FROM
                products p
            LEFT JOIN
                all_cards_data acd
                ON acd.local_vendor_code = p.id
            ORDER BY acd.subject_name, p.name
            LIMIT $1
            OFFSET $2;
        """

        async with self.pool.acquire() as connection:
            data = await connection.fetch(query, limit, offset)

        subjects_dict = defaultdict(list)

        for row in data:
            subject_name = row["subject_name"]
            articles_data = json.loads(row["articles"])

            articles = [ArticleResponse(**article) for article in articles_data]

            product = ProductResponse(
                id=row["id"],
                name=row["name"],
                photo_link=row["photo_link"],
                length=row["length"],
                width=row["width"],
                height=row["height"],
                manager=row["manager"],
                articles=articles,
            )

            subjects_dict[subject_name].append(product)

        return [SubjectDataWithProductsResponse(
            subject_name=name,
            products=products
        ) for name, products in subjects_dict.items()]

    async def get_product_cards(self, product_id: str):
        """Получить все карточки товара."""
        query = """
            WITH product_cards AS (
                SELECT
                    a.nm_id,
                    a.account,
                    a.vendor_code,
                    a.local_vendor_code,
                    a.created_at
                FROM article a 
                WHERE a.local_vendor_code = $1
            )
            SELECT
                pc.nm_id,
                pc.account,
                pc.vendor_code,
                pc.local_vendor_code,
                pc.created_at,
                coalesce(cs.status, 'active') AS status,
                cd.barcode,
                cd.subject_id,
                cd.photo_link
            FROM product_cards pc
            LEFT JOIN card_status cs
                ON pc.nm_id = cs.nm_id
            LEFT JOIN card_data cd
                ON cd.article_id = pc.nm_id 
            ORDER BY pc.account, pc.vendor_code
        """

        rows = await self.pool.fetch(query, product_id)
        return [ProductCard(**row) for row in rows]
