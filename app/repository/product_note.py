from asyncpg import (Pool, PostgresError, UndefinedTableError,
                     InterfaceError, ConnectionFailureError, ConnectionDoesNotExistError)
from typing import NoReturn
from fastapi import HTTPException, status

from app.domain.models import ProductNoteUpdate
from app.utils.decorators import error_handler_http


class ProductNoteRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    @error_handler_http(
            status_code=500,
            message="Database error occured",
            exceptions=(
                PostgresError,
                InterfaceError,
                ConnectionFailureError,
                ConnectionDoesNotExistError
            )
    )
    async def update_note(self, data: ProductNoteUpdate) -> NoReturn | dict:
        """Обновление заметок к товару. Создаёт новую запись с переданными
        для сохранения данными, если запись существует, обновляет переданные
        данные.

        Args:
            data (ProductNotesUpdate): модель данных для обновления заметок.
        """
        key_identifier = data.identifier
        template_conditions = "nm_id = $1 AND account = $2 AND local_vendor_code = $3"
        key_params = [
            key_identifier.nm_id,
            key_identifier.account,
            key_identifier.product_id
        ]

        updated_data = data.model_dump(exclude_unset=True)
        updated_fields = {key: value for key, value in updated_data.items() if key != "identifier"}

        if "note" in updated_fields:
            updated_fields["note"] = updated_fields["note"]

        if not updated_fields:
            return {
                "message": "Нет данных для обновления."
            } 
        
        set_clauses = [] # куски SET для UPDATE
        insert_columns = ["nm_id", "account", "local_vendor_code"] # для INSERT
        insert_values = key_params.copy() # для INSERT
        all_params = key_params.copy() # все параметры для запроса

        for field_name, value in updated_fields.items():
            for field_name, value in updated_fields.items():
                set_clauses.append(f"{field_name} = ${len(all_params) + 1}")
                all_params.append(value)
                insert_columns.append(field_name)
                insert_values.append(value)
        
        async with self.pool.acquire() as conn:
            product = await conn.fetchval(
                f"SELECT EXISTS (SELECT 1 FROM article WHERE {template_conditions});",
                *key_params
            )

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Товар с указанными параметрами не найден."
                )
            
            async with conn.transaction():
                note = await conn.fetchval(
                    f"SELECT EXISTS (SELECT 1 FROM product_notes WHERE {template_conditions});",
                    *key_params
                )

                if not note:
                    placeholders = ", ".join(
                        f"${i}" for i in range(1, len(insert_values) + 1)
                    )
                    columns = ", ".join(insert_columns)
                    query = f"INSERT INTO product_notes ({columns}) VALUES ({placeholders});"
                    await conn.execute(query, *all_params)

                else:
                    set_clauses.append("updated_at = NOW()")
                    query = f"UPDATE product_notes SET {', '.join(set_clauses)} WHERE {template_conditions}"
                    await conn.execute(query, *all_params)