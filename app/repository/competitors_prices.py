from asyncpg import Pool
from clickhouse_connect.driver.asyncclient import AsyncClient
from fastapi import HTTPException
from typing import List, Dict, Any


class CompetitorPriceRepository:
    def __init__(self, pool: Pool, client: AsyncClient):
        self.client = client
        self.pool = pool

    async def get_all_competitor_prices(self) -> List[Dict[str, Any]]:
        # Запрос к ClickHouse: получаем актуальные цены конкурентов
        clickhouse_query = """
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
            clickhouse_result = await self.client.query(clickhouse_query)

            if clickhouse_result is None:
                raise HTTPException(status_code=500, detail="Failed to fetch competitor data from ClickHouse")

            competitor_prices_by_lvc = self.group_competitor_prices(clickhouse_result)

            # Запрос к PostgreSQL: получаем наши карточки по local_vendor_code
            lv_codes = list(competitor_prices_by_lvc.keys())

            if not lv_codes:
                return []

            postgres_query = """
                SELECT
                    a.local_vendor_code,
                    a.account,
                    cd.article_id,
                    cd.price,
                    p.name
                FROM article a
                LEFT JOIN products p ON p.id = a.local_vendor_code
                LEFT JOIN card_data cd ON a.nm_id = cd.article_id
                WHERE a.local_vendor_code = ANY($1)
                ORDER BY a.local_vendor_code
            """

            async with self.pool.acquire() as conn:
                cards_data = await conn.fetch(postgres_query, lv_codes)

            our_prices_by_lvc = self.group_our_prices(cards_data)

            # Сборка финального результата
            result = []

            for lv_code, our_prices in our_prices_by_lvc.items():
                if lv_code not in competitor_prices_by_lvc:
                    continue

                result.append({
                    "local_vendor_code": lv_code,
                    "name": our_prices["name"],
                    "our_prices": our_prices["prices"],
                    "competitor_prices": competitor_prices_by_lvc[lv_code],
                })

            return result

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching competitor prices: {str(e)}")

    def group_competitor_prices(self, clickhouse_result) -> Dict[str, List[Dict[str, Any]]]:
        """Группирует данные конкурентов по wild (local_vendor_code)."""
        grouped = {}
        columns = clickhouse_result.column_names

        for row in clickhouse_result.result_rows:
            item = dict(zip(columns, row))
            wild = item["wild"]

            if wild not in grouped:
                grouped[wild] = []

            grouped[wild].append({
                "concurrent": item["concurrent"],
                "article_id": item["article_id"],
                "price": item["price"],
                "found_article": item["found_article"],
                "position": item["position"],
                "processed_at": item["processed_at"],
            })

        return grouped

    def group_our_prices(self, our_cards) -> Dict[str, List[Dict[str, Any]]]:
        """Группирует наши цены по local_vendor_code."""
        grouped = {}

        for card in our_cards:

            lvc = card["local_vendor_code"]

            if lvc not in grouped:
                grouped[lvc] = {"name": card["name"], "prices": []}

            grouped[lvc]["prices"].append({
                "account": card["account"],
                "article_id": card["article_id"],
                "price": card["price"],
            })

        return grouped
