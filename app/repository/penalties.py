from collections import defaultdict

from asyncpg import Pool, UndefinedTableError
from fastapi import HTTPException, status

from app.domain.models import PenaltyDetails, DaylyPenaltiesReport, PeriodRequestModel


class PenaltyRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_penalties_details(
        self,
        period: PeriodRequestModel
    ) -> list[DaylyPenaltiesReport]:
        """Получить данные о штрафах по каждому дню."""
        query = """
        SELECT
            date as penalty_date,
            sale_dt,
            penalty,
            count_items,
            bonus_type_name,
            nm_id,
            subject_name,
            account,
            srid,
            warehouse_type,
            order_date,
            local_vendor_code,
            shk_id,
            assembly_id,
            supplier_status,
            wb_status,
            supply_id
        FROM penalties_mv
        WHERE date BETWEEN $1 AND $2
        ORDER BY date DESC;
        """

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, period.date_from, period.date_to)
        except UndefinedTableError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table or materialized view not found",
            )

        penalties_by_date = defaultdict(list)

        for row in rows:
            data = dict(row)
            penalties_date = data.pop("penalty_date")

            penalties_by_date[penalties_date].append(PenaltyDetails(**data))

        return [DaylyPenaltiesReport(
            penalties_date=date,
            penalties=penalties
        ) for date, penalties in penalties_by_date.items()]
