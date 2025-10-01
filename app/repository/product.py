from asyncpg import Pool, Record

from app.domain.models import SubjectDataWithProductsResponse


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
        async with self.pool.acquire() as connection:
            query = """
            SELECT
                p.id,
                p.name,
                p.photo_link,
                cd.article_id,
                cd.subject_name,
                cd.photo_link as card_photo_link,
                cd.price,
                cd.discount,
                cd.length,
                cd.width,
                cd.height,
                cd.barcode,
                cd.rating,
                cd.manager
            FROM 
                products p
            LEFT JOIN (
                select
                    a.nm_id,
                    a.local_vendor_code 
                from article a
            ) lvc on p.id = lvc.local_vendor_code
            LEFT JOIN
                card_data cd
                ON lvc.nm_id = cd.article_id
            ORDER BY
                cd.subject_name,
                p.id
            LIMIT $1
            OFFSET $2;
            """

            data = await connection.fetch(query, limit, offset)

        return self.__transform_asyncpg_data(data)

    @staticmethod
    def __transform_asyncpg_data(
        data: list[Record]
    ) -> SubjectDataWithProductsResponse:
        """Привести сырые данные из БД в структурированный ответ."""
        subjects = {}

        for row in data:
            data = dict(row)
            subject_name = data.pop("subject_name")

            subjects.setdefault(subject_name, []).append(data)

        return [
            SubjectDataWithProductsResponse(
                subject_name=name,
                products=products
            )
            for name, products in subjects.items()
        ]
