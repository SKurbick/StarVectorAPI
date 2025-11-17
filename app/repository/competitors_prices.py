from asyncpg import Pool
from clickhouse_connect.driver.asyncclient import AsyncClient
from fastapi import HTTPException
from typing import List, Dict, Any, Optional


class CompetitorPriceRepository:
    def __init__(self, pool: Pool, client: AsyncClient):
        self.client = client
        self.pool = pool

    async def get_all_competitor_prices(self) -> List[Dict[str, Any]]:
        """
        Получить цены конкурентов и цены продавца.

        Данные сгруппированы по local_vendor_code.
        """
        try:
            competitor_prices_by_lvc = await self.fetch_competitor_prices()
            lv_codes = list(competitor_prices_by_lvc.keys())
            our_prices_by_lvc = await self.fetch_seller_prices(lv_codes)

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
            raise HTTPException(status_code=500, detail=f"Ошибка во время выполнения get_all_competitor_prices: {str(e)}")

    async def fetch_competitor_prices(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получить актуальные цены конкурентов.

        Данные группируются по wild (local_vendor_code).
        """
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
                raise Exception("Не получены данные из ClickHouse")

            # Группирует данные конкурентов по wild (local_vendor_code)
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
        except Exception as e:
            raise Exception(f"Ошибка во время получения цен конкурентов: {e}")

    async def fetch_seller_prices(self, local_vendor_codes: Optional[list[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получить цены продавца.

        Данные группируются по local_vendor_code.
        """
        postgres_query = """
            SELECT DISTINCT ON (a.local_vendor_code, a.nm_id)
                a.local_vendor_code,
                a.account,
                a.nm_id,
                sh.spp_price,
                p.name
            FROM article a
            LEFT JOIN products p ON p.id = a.local_vendor_code
            LEFT JOIN spp_history sh ON a.nm_id = sh.nm_id
        """

        params = []

        if local_vendor_codes:
            params.append(local_vendor_codes)
            postgres_query += f" WHERE a.local_vendor_code = ANY(${len(params)})"

        postgres_query += " ORDER BY a.local_vendor_code, a.nm_id, sh.created_at DESC"

        try:
            async with self.pool.acquire() as conn:
                cards_data = await conn.fetch(postgres_query, *params)

            # Группирует наши цены по local_vendor_code
            grouped = {}

            for card in cards_data:

                lvc = card["local_vendor_code"]

                if lvc not in grouped:
                    grouped[lvc] = {"name": card["name"], "prices": []}

                grouped[lvc]["prices"].append({
                    "account": card["account"],
                    "article_id": card["nm_id"],
                    "price": card["spp_price"],
                })

            return grouped
        except Exception as e:
            raise Exception(f"Ошибка во время получения цен продавца: {e}")
