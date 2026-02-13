from collections import defaultdict
import json

from asyncpg import Pool

from app.domain.models import  (
    ArticleResponse,
    ProductResponse,
    SubjectDataWithProductsResponse,
    ProductWBCard,
)


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

    async def get_product_wb_cards(self, product_id: str) -> list[ProductWBCard]:
        """Получить все карточки товара."""
        query = """
            WITH product_cards AS (
                SELECT
                    a.nm_id,
                    a.account,
                    a.vendor_code,
                    a.local_vendor_code
                FROM article a 
                WHERE a.local_vendor_code = $1
            ),
            card_statuses AS (
                SELECT
                    cs.nm_id,
                    cs.status
                FROM card_status cs
                WHERE cs.nm_id IN (
                    SELECT nm_id
                    FROM product_cards
                )
            ),
            prices AS (
                SELECT DISTINCT ON (pc.local_vendor_code, pc.nm_id)
                    pc.local_vendor_code,
                    pc.nm_id,
                    sh.spp_price AS price,
                    ROUND(sh.spp_percent::NUMERIC, 0) AS discount
                FROM product_cards pc
                LEFT JOIN spp_history sh ON pc.nm_id = sh.nm_id
                ORDER BY pc.local_vendor_code, pc.nm_id, created_at DESC
            ),
            stocks AS (
                SELECT
                    csq.article_id,
                    csq.quantity
                FROM current_stocks_quantity csq
                WHERE csq.article_id IN (
                    SELECT nm_id
                    FROM product_cards
                )
                AND quantity_type = 'ФБС'
            )
            SELECT
                pc.nm_id,
                pc.account,
                pc.vendor_code,
                pc.local_vendor_code,
                COALESCE(cs.status, 'active') AS status,
                cd.barcode,
                cd.rating,
                cd.photo_link AS small_photo_link,
                cd.wb_name AS name,
                cd.wb_description AS description,
                p.price,
                p.discount,
                COALESCE(s.quantity, 0) AS fbs_stock_quantity
            FROM product_cards pc
            LEFT JOIN card_statuses cs
                ON pc.nm_id = cs.nm_id
            LEFT JOIN prices p
                ON p.nm_id = pc.nm_id
            LEFT JOIN card_data cd
                ON cd.article_id = pc.nm_id 
            LEFT JOIN stocks s
                ON s.article_id = pc.nm_id
            ORDER BY pc.account, pc.vendor_code
        """

        rows = await self.pool.fetch(query, product_id)
        return [ProductWBCard(**row) for row in rows]

    async def check_product_exists(self, product_id: str) -> bool:
        """Проверить, существует ли товар."""
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM products
                WHERE id = $1
            );
        """

        return await self.pool.fetchval(query, product_id)
