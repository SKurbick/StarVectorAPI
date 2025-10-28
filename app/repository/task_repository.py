from asyncpg import Pool


class TaskRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def update_task_status(self, task_id: str, status: str, error_message: str = None):
        query = """
            UPDATE stock_clearance_task
            SET status = $1, updated_at = NOW(), error_message = $2
            WHERE task_id = $3
        """

        async with self.pool.acquire() as conn:
            await conn.execute(query, status, error_message, task_id)
