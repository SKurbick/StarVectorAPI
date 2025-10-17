from clickhouse_connect.driver.asyncclient import AsyncClient


class CompetitorsPricesRepository:
    def __init__(self, client: AsyncClient):
        self.client = client

    async def get_competitors_prices(self):
        query = """
            SELECT
                wild,
                concurrent,
                article_id,
                price,
                found_article,
                position,
                processed_at
            FROM (
                SELECT
                    wild,
                    concurrent,
                    article_id,
                    price,
                    found_article,
                    position,
                    processed_at,
                    ROW_NUMBER() OVER (PARTITION BY wild, concurrent ORDER BY processed_at DESC) AS rn
                FROM mpstats.product_positions
                WHERE found_article IS NOT NULL
                    AND concurrent != 'Наш артикул'
                    AND price IS NOT NULL
                    AND position IS NOT NULL
                    AND wild IS NOT NULL
                    AND concurrent IS NOT NULL
                    AND wild != ''
            )
            WHERE rn = 1
            ORDER BY wild, concurrent
            LIMIT 10
        """

        result = await self.client.query(query)

        print(result.row_count)
        print(result.column_types)
        print(result.column_names)
        
        for row in result.result_rows:
            print(row)
