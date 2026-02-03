import json

from asyncpg import Pool

from app.domain.models import ProductWBCharc


class WBCharcRepository:
    """Репозиторий для характеристик WB."""

    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_charcs_by_product_id(self, product_id: int) -> list[ProductWBCharc]:
        """
        Получить список характеристик WB для товара.

        Args:
            product_id: локальный ID товара.
        """
        query = """
            WITH product_charc AS (
                SELECT
                    pch.product_id,
                    pch.charc_id,
                    pch.value
                FROM wb_product_characteristics pch
                WHERE pch.product_id = $1
            )
            SELECT
                pch.charc_id AS id,
                pch.product_id,
                pch.value,
                wch.name,
                wch.unit_name,
                wch.max_count,
                wch.required,
                wch.popular,
                wch.charc_type
            FROM product_charc pch
            JOIN wb_characteristics wch
                ON wch.id = pch.charc_id
            ORDER BY wch.name
        """

        rows  = await self.pool.fetch(query, product_id)
        result = []

        for row in rows:
            data = dict(**row)
            parsed_value = json.loads(data.pop("value"))
            normalized_value = [parsed_value] if isinstance(parsed_value, str) else parsed_value
            result.append(
                ProductWBCharc(
                    **data, value=normalized_value
                )
            )

        return result
