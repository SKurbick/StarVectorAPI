from collections import defaultdict

from asyncpg import Pool, PostgresError, InterfaceError, ConnectionFailureError, ConnectionDoesNotExistError

from app.domain.models import ICNetProfitResponseModel
from app.utils.decorators import error_handler_http


class ICNetProfitRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    @error_handler_http(
        status_code=500,
        message='Database error occurred',
        exceptions=(
            PostgresError,
            InterfaceError,
            ConnectionFailureError,
            ConnectionDoesNotExistError
        )
    )
    async def get_net_profit(self) -> list[ICNetProfitResponseModel]:
        """
        Метод для получения суммы честой прибыли по ИУ за месяц, отсортированных по дате в порядке возрастания.
        """

        async with self.pool.acquire() as conn:
            query = """
                SELECT
                    anpc.article_id,
                    anpc.date,
                    anpc.sum_net_profit
                FROM accurate_npd_purchase_calculation anpc
                WHERE anpc.date > NOW() - INTERVAL '32 day'
                ORDER BY anpc.date;
            """

            result = await conn.fetch(query)
            grouped_data = defaultdict(list)

            for record in result:
                article_id = record.get("article_id")
                grouped_data[article_id].append(
                    {
                        "date": record.get("date"),
                        "net_profit": record.get("sum_net_profit")
                     }
                )

            return [
                ICNetProfitResponseModel(
                    article_id=article_id,
                    data=grouped_data[article_id]
                ) for article_id in grouped_data
            ]