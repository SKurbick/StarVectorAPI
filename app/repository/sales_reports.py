import asyncpg
from datetime import date
from typing import Iterable, List, Tuple, Type, AsyncGenerator
from contextlib import asynccontextmanager
import logging
from pydantic import BaseModel

from app.infrastructure.API.wildberries.finance.schemes.sales_report import SalesReportRow

class SalesReportRepository:
    """
    Репозиторий для финансовых отчётов по реализации товаров на WB.
    """

    # def __init__(self, pool: asyncpg.Pool, model: Type[BaseModel]):
    #     self.pool = pool
    #     self.model = model
    #     self._columns: List[str] = list(model.model_fields.keys())
    #     self._columns_sql = ", ".join(self._columns)

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool        
        self._columns: list[str] | None = None
        self._columns_sql: str | None = None

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Получить соединение с БД в рамках транзакции.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                logging.debug(f"Открыта транзакция в {SalesReportRepository.__name__}")
                yield conn
                logging.debug(f"Закрыта транзакция в {SalesReportRepository.__name__}")

    async def _ensure_columns_loaded(self, conn: asyncpg.Connection, main_table: str) -> None:
        """
        Загрузить актуальный список колонок из основной таблицы БД.
        """
        if self._columns is not None:
            return

        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position ASC
        """
        rows = await conn.fetch(query, main_table)
        
        if not rows:
            raise ValueError(f"Таблица '{main_table}' не найдена или не имеет колонок.")

        print(self._columns)
        self._columns = [row["column_name"] for row in rows]
        self._columns_sql = ", ".join(self._columns)

    async def create_temp_table(
            self, 
            conn: asyncpg.Connection, 
            main_table_name: str, 
            tmp_table_name: str
    ) -> str:
        """
        Создаёт временную таблицу с той же структурой, что и основная.
        """
        if not main_table_name.strip():
            raise ValueError(f"Передано пустое значение названия основной таблицы.")

        if not tmp_table_name.strip():
            raise ValueError(f"Передано пустое значение для названия временной таблицы.")

        await self._ensure_columns_loaded(conn, main_table_name)

        query = f"""
            CREATE TEMPORARY TABLE {tmp_table_name}
            ON COMMIT DROP
            AS SELECT * FROM {main_table_name}
            WITH NO DATA;
        """

        await conn.execute(query)
        return tmp_table_name

    async def insert_batch(
            self, 
            conn: asyncpg.Connection, 
            table_name: str, 
            records: Iterable[SalesReportRow]
    ) -> int:
        """
        Пакетная вставка данных в таблицу через COPY протокол PostgreSQL.
        """
        if not records:
            return

        tuples = [tuple(getattr(record, col, None) for col in self._columns) for record in records]

        result = await conn.copy_records_to_table(
            table_name=table_name,
            records=tuples,
            columns=self._columns
        )
        logging.debug(f"Выполнена вставка в БД: [{table_name=}|records-in={len(tuples)}|{result}]")
        return len(tuples)

    async def clean_data_from_table_by_period(
            self,
            conn: asyncpg.Connection,
            table_name: str,
            date_from: date,
            date_to: date | None = None,
    ) -> None:
        """
        Удалить данные из таблицы за период.
        """

        params = [date_from]

        delete_query = f"""
            DELETE FROM {table_name}
            WHERE date_from = $1
        """

        if date_to is not None:
            delete_query += " AND date_to = $2"
            params.append(date_to)

        await conn.execute(delete_query, *params)

    async def merge_tmp_to_main_table(
            self,
            conn: asyncpg.Connection,
            main_table_name: str,
            tmp_table_name: str,
    ) -> None:
        """
        Залить данные из временной таблицы в основную.
        """
        update_set_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in self._columns])

        query = f"""
            INSERT INTO {main_table_name} ({self._columns_sql})
            SELECT {self._columns_sql}
            FROM {tmp_table_name}
            ON CONFLICT (realizationreport_id, rrd_id) 
            DO UPDATE SET {update_set_clause};
        """

        await conn.execute(query)
