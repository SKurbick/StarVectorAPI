from typing import List

from asyncpg import Pool
from app.domain.models import PercentByTaxResponseModel, DefaultPercentByTaxResponseModel


class PercentByTaxRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def update_percent_by_tax(self, data: List[PercentByTaxResponseModel]):
        # Проверяем, что данные не пустые
        if not data:
            return

        # Подготавливаем SQL-запрос
        query = """
        UPDATE unit_economics
        SET percent_by_tax = d.percent_by_tax
        FROM (VALUES ($1::int, $2::int)) AS d(article_id, percent_by_tax)
        WHERE unit_economics.article_id = d.article_id
        """

        # Преобразуем данные в список кортежей (article_id, percent_by_tax)
        records = [(item.article_id, item.percent_by_tax) for item in data]

        # Выполняем массовое обновление
        async with self.pool.acquire() as connection:
            await connection.executemany(query, records)

    async def update_default_percent_by_tax(self, data: DefaultPercentByTaxResponseModel):
        query = """
        UPDATE settings
        SET
        num_value = $1
        WHERE setting_name = 'default_percent_by_tax'

        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, data.default_percent_by_tax)
