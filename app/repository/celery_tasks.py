from typing import Optional, Dict, Any
import json

from asyncpg import Pool


class CeleryTaskRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def create_task(
        self,
        task_id: str,
        account: str,
        operation_type: str,
        task_data: Optional[Dict[str, Any]] = None,
    ) -> int:
        query = """
            INSERT INTO crm_background_tasks (
                task_id,
                account,
                operation_type,
                task_data,
                status
            )
            VALUES ($1, $2, $3, $4, 'pending')
            RETURNING id;
        """

        task_data_json = json.dumps(task_data) if task_data else None

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                task_id,
                account,
                operation_type,
                task_data_json,
            )
            return row["id"]
