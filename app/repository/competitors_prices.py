from asyncpg import Pool
from clickhouse_connect.driver.asyncclient import AsyncClient
from fastapi import HTTPException


class CompetitorPriceRepository:
    def __init__(self, pool: Pool, client: AsyncClient):
        self.client = client
        self.pool = pool

    async def get_all_competitors_prices(self):
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
        """
        try:
            # получаем данные из clickhouse
            result = await self.client.query(query)

            if result is None:
                raise HTTPException(status_code=500, detail="Failed to fetch data")

            columns = result.column_names
            rows = result.result_rows
            all_data = [dict(zip(columns, row)) for row in rows]

            competirors_prices = {}

            for item in all_data:
                if item["wild"] not in competirors_prices:
                    competirors_prices[item["wild"]] = []

                competirors_prices[item["wild"]].append(
                    {
                        "concurrent": item["concurrent"],
                        "article_id": item["article_id"],
                        "price": item["price"],
                        "found_article": item["found_article"],
                        "position": item["position"],
                        "processed_at": item["processed_at"],
                    }
                )

            card_info_query = """
                SELECT
                    a.local_vendor_code,
                    cd.article_id,
                    cd.price,
                    cd.local_card_name
                FROM
                    article a
                INNER JOIN
                    card_data cd
                    ON a.nm_id = cd.article_id
                WHERE a.local_vendor_code = ANY($1)
                ORDER BY a.local_vendor_code
            """

            wilds = list(competirors_prices.keys())
            async with self.pool.acquire() as conn:
                cards = await conn.fetch(card_info_query, wilds)
            
            our_prices = {}

            for card in cards:
                if card["local_vendor_code"] not in our_prices:
                    our_prices[card["local_vendor_code"]] = []
                
                our_prices[(card["local_vendor_code"], card["local_card_name"])].append(
                    {
                        "article_id": card["article_id"],
                        "price": card["price"],
                    }
                )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        return competirors_prices
