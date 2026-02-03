from asyncpg import Pool

from app.domain.models import WBParentCategory


class WBParentCategoryRepository:
    """Репозиторий для родительских категорий WB."""

    def __init__(self, pool: Pool):
        self.pool = pool

    async def list(self) -> list[WBParentCategory]:
        """Получить список родительских категорий."""
        query = """
        SELECT
            id,
            name,
            is_visible
        FROM 
            wb_parent_categories
        ORDER BY name;
        """

        rows = await self.pool.fetch(query)

        return [WBParentCategory(**row) for row in rows]
