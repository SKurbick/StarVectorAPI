from collections import defaultdict
import logging

import asyncpg


logger = logging.getLogger(__name__)


class SubjectDataRepository:
    """
    Репозиторий для работы с предметами с маркетплейсов.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_subject_data_from_wb(self):
        """
        Получить предметы по категориям маркетплейса Wildberries.
        """
        query = """
        SELECT
            pd.parent_wb_id,
            pd.parent_name,
            sd.subject_wb_id,
            sd.subject_name
        FROM parent_data pd
        LEFT JOIN subject_data sd
            ON pd.parent_wb_id = sd.parent_id
        ORDER BY pd.parent_name, sd.subject_name
        """
        logger.info("Получение предметов маркетплейса Wildberries...")

        try:
            rows  = await self.pool.fetch(query)
        except asyncpg.PostgresError as e:
            error_message = f"Ошибка во время получения предметов из базы данных: {e}"
            logger.exception(error_message)
            raise Exception(error_message)
        
        result = defaultdict(list)

        for row in rows:
            result[(row["parent_wb_id"], row["parent_name"])].append({
                "id": row["subject_wb_id"],
                "name": row["subject_name"]
            })

        return {"categories": [
            {
                "id": parent_id,
                "name": parent_name,
                "subjects": subjects
            }
            for (parent_id, parent_name), subjects in result.items()
        ]}
