from collections import defaultdict
from typing import Optional

from asyncpg import Pool

from app.domain.models import WBParentCategoryWithSubjects, WBSubject


class WBSubjectRepository:
    """Репозиторий для предметов WB."""

    def __init__(self, pool: Pool):
        self.pool = pool

    async def get(self, subject_id: int) -> Optional[WBSubject]:
        """Получить предмет WB по ID."""
        query = """
            SELECT
                id,
                name,
                parent_id
            FROM
                wb_subjects
            WHERE id = $1
        """

        row = await self.pool.fetchrow(query, subject_id)
        return WBSubject(**row) if row else None

    async def list(self, parent_id: Optional[int] = None) -> list[WBParentCategoryWithSubjects]:
        """
        Получить список предметов WB.

        Args:
            parent_id: ID родительской категории.
        """
        parent_category_query = """
            SELECT
                id,
                name,
                is_visible
            FROM wb_parent_categories
        """

        params = []
        if parent_id and isinstance(parent_id, int):
            parent_category_query += " WHERE id = $1 "
            params.append(parent_id)

        query = f"""
            SELECT
                wbs.id,
                wbs.name,
                wbs.parent_id,
                wbpc.name as parent_name,
                wbpc.is_visible
            FROM
                wb_subjects wbs
            INNER JOIN
                ({parent_category_query}) wbpc
                ON wbs.parent_id = wbpc.id
            ORDER BY wbpc.name, wbs.name
        """

        rows  = await self.pool.fetch(query, *params)
        result = defaultdict(list)

        for row in rows:
            result[(row["parent_id"], row["parent_name"], row["is_visible"])].append(
                WBSubject(
                    id=row["id"],
                    name=row["name"],
                    parent_id=row["parent_id"],
                )
            )

        return [
            WBParentCategoryWithSubjects(
                id=parent_id,
                name=parent_name,
                is_visible=is_visible,
                subjects=subjects,
            )
            for (parent_id, parent_name, is_visible), subjects in result.items()
        ]
