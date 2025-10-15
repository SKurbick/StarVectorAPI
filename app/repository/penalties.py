from collections import defaultdict

from asyncpg import Pool, UndefinedTableError
from fastapi import HTTPException, status

from app.domain.models import DaylyPenaltiesReport, PenaltyDetailsResponse,  PeriodRequestModel, PenaltyAnnotationUpdate, LossOwnerEnum


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
            pmv.date as penalty_date,
            pmv.sale_dt,
            pmv.penalty,
            pmv.count_items,
            pmv.bonus_type_name,
            pmv.nm_id,
            pmv.subject_name,
            pmv.account,
            pmv.srid,
            pmv.warehouse_type,
            pmv.order_date,
            pmv.local_vendor_code,
            pmv.shk_id,
            pmv.assembly_id,
            pmv.supplier_status,
            pmv.wb_status,
            pmv.supply_id,
            pa.loss_owner,
            pa.comment
        FROM penalties_mv pmv
        LEFT JOIN penalty_annotations pa ON (
            pmv.date = pa.date
            and pmv.nm_id = pa.nm_id
            and pmv.bonus_type_name = pa.bonus_type_name
            and pmv.srid = pa.srid
        )
        WHERE pmv.date BETWEEN $1 AND $2
        ORDER BY pmv.date DESC;
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

            penalties_by_date[penalties_date].append(PenaltyDetailsResponse(**data))

        return [DaylyPenaltiesReport(
            penalties_date=date,
            penalties=penalties
        ) for date, penalties in penalties_by_date.items()]

    async def update_penalty_annotation(self, data: PenaltyAnnotationUpdate):
        """Обновить аннотации к штрафу."""
        check_query = """
            SELECT EXISTS (
                SELECT 1
                FROM penalties_mv
                WHERE date = $1 AND nm_id = $2 AND bonus_type_name = $3 AND srid = $4
            );
        """
        delete_query = """
            DELETE FROM penalty_annotations
            WHERE date = $1 AND nm_id = $2 AND bonus_type_name = $3 AND srid = $4
        """
        add_or_update_query = """
            INSERT INTO penalty_annotations
                (date, nm_id, bonus_type_name, srid, loss_owner, comment)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (date, nm_id, bonus_type_name, srid)
            DO UPDATE SET
                loss_owner = EXCLUDED.loss_owner,
                comment = EXCLUDED.comment;
        """

        key = data.penalty
        owner = data.loss_owner or LossOwnerEnum.warehouse if data.loss_owner is not None else None
        should_store = (
            (data.loss_owner is not None and data.loss_owner != LossOwnerEnum.warehouse)
            or data.comment is not None
        )

        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(
                check_query,
                key.penalty_date,
                key.nm_id,
                key.bonus_type_name,
                key.srid,
            )

            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Штраф с указанными параметрами не найден"
                )

            async with conn.transaction() as transaction:
                if not should_store:
                    await conn.execute(
                        delete_query,
                        key.penalty_date,
                        key.nm_id,
                        key.bonus_type_name,
                        key.srid,
                    )
                else:
                    await conn.execute(
                        add_or_update_query,
                        key.penalty_date,
                        key.nm_id,
                        key.bonus_type_name,
                        key.srid,
                        owner,
                        data.comment,
                    )

        return {"message": "update success"}
