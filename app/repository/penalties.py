from collections import defaultdict
from typing import NoReturn

from asyncpg import Pool, PostgresError, UndefinedTableError, InterfaceError, ConnectionFailureError, ConnectionDoesNotExistError
from fastapi import HTTPException, status, UploadFile

from app.domain.enums import LossOwnerEnum, ExcelParserEnum
from app.domain.models import (DaylyPenaltiesReport, PenaltyDetailsResponse,
                               PeriodRequestModel, PenaltyAnnotationUpdate)
from app.utils.decorators import error_handler_http
from app.utils.utils import get_columns_values_from_excel_file


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
                pmv.price AS converted_price,
                pmv.penalty_rate,
                pmv.count_items,
                pmv.bonus_type_name,
                pmv.nm_id,
                pmv.subject_name,
                pmv.account,
                pmv.srid,
                pmv.warehouse_type,
                pmv.order_date,
                CASE
                    WHEN pmv.nm_id != 0 AND pmv.local_vendor_code IS NULL
                    THEN 'Неопознанный товар'
                    ELSE pmv.local_vendor_code
                END as local_vendor_code,
                pmv.shk_id,
                pmv.supplier_status,
                pmv.wb_status,
                pmv.wb_status_at as wb_status_setting_date,
                pmv.supply_id,
                pmv.assembly_id,
                pmv.assembly_status as internal_status,
                pmv.assembly_status_at as internal_status_setting_date,
                pmv.assembly_start_at as assembly_start_date,
                pmv.assembly_end_at as assembly_end_date,
                pmv.delivered_at as transferred_to_delivery_at,
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
            loss_owner = data.get("loss_owner")

            if not loss_owner:
                data["loss_owner"] = LossOwnerEnum.warehouse.id
            else:
                data["loss_owner"] = LossOwnerEnum.from_db_value(loss_owner).id

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

        # Подставляем значение для БД
        if "loss_owner" in update_fields:
            update_fields["loss_owner"] = update_fields["loss_owner"].value_for_db

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
    @error_handler_http(
            status_code=500,
            message='Database error occured',
            exceptions=(
                PostgresError,
                InterfaceError,
                ConnectionFailureError,
                ConnectionDoesNotExistError
            )
    )    
    async def update_penalty_annotations_from_excel(
            self,
            upload_file: UploadFile
    ) -> NoReturn:
        
        PARSER_TO_DB = {
            "penalty_date": "date",
            "nm_id": "nm_id",
            "bonus_type_name": "bomus_type_name",
            "srid": "srid",
            "loss_owner": "loss_owner",
            "comment": "comment",
        }

        column_indices = [e.value for e in ExcelParserEnum]

        try:
            rows = get_columns_values_from_excel_file(
                upload_file=upload_file,
                column_indices=column_indices,
                enum_mapping=ExcelParserEnum,
                start_row=2
            )
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка чтения Excel: {error}"
            )
        
        conflict_cols_sql = "date, nm_id, bonus_type_name, srid"

        async with self.pool.acquire() as conn:

            async with conn.transaction():

                for row_idx, row in enumerate(rows, start=2):
                    key = {
                        "date": row.get("penalty_date"),
                        "nm_id": row.get("nm_id"),
                        "bonus_type_name": row.get("bonus_type_name"),
                        "srid": row.get("srid"),
                    }
                        
                        
                    await conn.fetchval(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM penalties_mv
                            WHERE date = $1 AND nm_id = $2 AND bonus_type_name = $3 AND srid = $4
                        )
                        """,
                        key["date"], key["nm_id"], key["bonus_type_name"], key["srid"]
                    )

                    data_cols = {}

                    for parser_key, db_col in PARSER_TO_DB.items():

                        if parser_key in ("penalty_date", "nm_id", "bonus_type_name", "srid"):
                            continue

                        if parser_key in row:
                            val = row.get(parser_key)

                            if parser_key == "loss_owner" and val is not None:
                                val = getattr(val, "value_for_db", val)

                            data_cols[db_col] = val
                    
                    insert_cols = list(key.keys()) + list(data_cols.keys())
                    insert_vals = list(key.values()) + list(data_cols.values())

                    placeholders = ", ".join(f"{i}" for i in range(1, len(insert_vals) + 1))
                    cols_sql = ", ".join(insert_cols)

                    if data_cols:
                        update_sql = ", ".join(f"{col} = EXCLUDED.{col}" for col in data_cols.keys())
                    else:
                        update_sql = None

                    if update_sql:
                        sql = (
                            f"INSERT INTO penalty_annotations ({cols_sql}) VALUES ({placeholders}) "
                            f"ON CONFLICT ({conflict_cols_sql}) DO UPDATE SET {update_sql};"
                        )
                    else:
                        sql = (
                            f"INSERT INTO penalty_annotations ({cols_sql}) VALUES ({placeholders}) "
                            f"ON CONFLICT ({conflict_cols_sql}) DO NOTHING;"
                        )

                    await conn.execute(sql, *insert_vals)
