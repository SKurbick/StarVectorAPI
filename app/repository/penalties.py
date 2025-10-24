from collections import defaultdict
from typing import NoReturn

from asyncpg import Pool, PostgresError, UndefinedTableError
from fastapi import HTTPException, status

from app.domain.models import (DaylyPenaltiesReport, PenaltyDetailsResponse,
                               PeriodRequestModel, PenaltyAnnotationUpdate)


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
            pmv.sale_dt::date,
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

    async def update_penalty_annotation(self, data: PenaltyAnnotationUpdate) -> NoReturn:
        """Обновить аннотации к штрафу. Создаёт запись, если она отсутствует и переданы данные для сохранения."""
        # Извлекаем ключевые поля
        key = data.penalty
        key_conditions = "date = $1 AND nm_id = $2 AND bonus_type_name = $3 AND srid = $4"
        key_params = [
            key.penalty_date,
            key.nm_id,
            key.bonus_type_name,
            key.srid,
        ]

        update_data = data.model_dump(exclude_unset=True)
        update_fields = {k: v for k, v in update_data.items() if k != "penalty"}

        if not update_fields:
            return {"message": "No fields to update"}

        set_clauses = []
        insert_columns = ["date", "nm_id", "bonus_type_name", "srid"]
        insert_values = key_params.copy()
        all_params = key_params.copy()

        for field_name, value in update_fields.items():
            set_clauses.append(f"{field_name} = ${len(all_params) + 1}")
            all_params.append(value)
            insert_columns.append(field_name)
            insert_values.append(value)

        try:
            async with self.pool.acquire() as conn:
                # Проверяем существование штрафа
                penalty_exists = await conn.fetchval(
                    f"SELECT EXISTS (SELECT 1 FROM penalties_mv WHERE {key_conditions});",
                    *key_params,
                )
                if not penalty_exists:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Штраф с указанными параметрами не найден"
                    )

                async with conn.transaction():
                    # Проверяем существование аннотации
                    annotation_exists = await conn.fetchval(
                        f"SELECT EXISTS (SELECT 1 FROM penalty_annotations WHERE {key_conditions});",
                        *key_params,
                    )

                    if not annotation_exists:
                        placeholders = ", ".join(f"${i}" for i in range(1, len(insert_values) + 1))
                        columns = ", ".join(insert_columns)
                        query = f"INSERT INTO penalty_annotations ({columns}) VALUES ({placeholders});"
                        
                        await conn.execute(query, *insert_values)
                    else:
                        query = f"UPDATE penalty_annotations SET {', '.join(set_clauses)} WHERE {key_conditions};"
                        await conn.execute(query, *all_params)
        except PostgresError as e:
            raise HTTPException(
                status_code=422,
                detail=f"PoistgresError: {e}"
            )
