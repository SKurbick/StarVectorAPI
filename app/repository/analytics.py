

from asyncpg import Pool


class AnalyticsRepository:
    """Репозиторий для аналитических запросов"""

    def __init__(self, pool: Pool) -> None:
        self.pool = pool

    async def get_warehouse_time_execution(self):
        """Запрос к бд на получение времени исполнения поставки"""
        query = """
            WITH status_sorted AS (SELECT atsm.id,
            atsm.created_at_db FROM assembly_task_status_model atsm
            WHERE atsm.supplier_status = 'new' 
            AND atsm."date" BETWEEN (now()- '1 month'::interval) AND now()
            ) SELECT atsm.account,
            ROUND(AVG(EXTRACT(epoch FROM (atsm.created_at_db - ss.created_at_db))/3600), 0) AS time_executing 
            FROM assembly_task_status_model atsm
            JOIN status_sorted ss ON ss.id = atsm.id
            WHERE atsm.wb_status = 'sorted' 
            AND atsm."date" BETWEEN (now()- '1 month'::interval) AND now()
            GROUP BY atsm.account ORDER BY time_executing;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
        return rows