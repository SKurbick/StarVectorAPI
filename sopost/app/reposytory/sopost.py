from asyncpg import Pool, Record

from domain.shemas.sopost import SubjectsResponse


class SopostRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_sopost_items(
        self,
        limit: int = 100, 
        offset: int = 0,
    ) -> list[SubjectsResponse]:
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

            rows = await connection.fetch(query, limit, offset)
        return self.__rows_to_subject_of_sopost_items(rows)
    
    @staticmethod
    def __rows_to_subject_of_sopost_items(
        rows: list[Record]
    ) -> SubjectsResponse:
        """Конвертировать объекты Record в список SopostItemResponse."""
        subjects = {}

        for row in rows:
            data = dict(row)
            subject_name = data.pop("subject_name")

            subjects.setdefault(subject_name, []).append(data)

        return [
            SubjectsResponse(
                subject_name=name,
                sopost_items=items
            )
            for name, items in subjects.items()
        ]
