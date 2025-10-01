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
            WITH distinct_vendors AS (
                SELECT DISTINCT ON (local_vendor_code)
                    nm_id,
                    local_vendor_code
                FROM article
            )
            SELECT
                cd.subject_name,
                p.id,
                p.name,
                p.photo_link,
                cd.length,
                cd.width,
                cd.height,
                cd.manager
            FROM 
                products p
            LEFT JOIN
                distinct_vendors dv
                ON p.id = dv.local_vendor_code
            LEFT JOIN
                card_data cd
                ON dv.nm_id = cd.article_id
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
