from asyncpg import Pool

from domain.shemas.sopost import SopostItemResponse


class SopostRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_sopost_items(
        self,
        limit: int = 10, 
        offset: int = 0,
    ) -> list[SopostItemResponse]:
        async with self.pool.acquire() as connection:
            query = """
                SELECT * FROM products
                LIMIT $1
                OFFSET $2;
            """

            rows = await connection.fetch(query, limit, offset)
            return [SopostItemResponse.model_dump(dict(row)) for row in rows]
