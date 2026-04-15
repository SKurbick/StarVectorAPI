import logging
from typing import Optional

from asyncpg import Pool

from app.domain.models import ProductData, ProductBase


logger = logging.getLogger(__name__)


class ProducsDataRepository:
    def __init__(self, pool: Pool):
        self.pool = pool
    
    async def get(self, product_id: str) -> ProductData | None:
        """
        Получить информацию о товаре из products_data.
        
        Args:
            product_id: локальный id товара.
        """
        query = """
            SELECT
                pd.product_id,
                p.name,
                pd.length,
                pd.width,
                pd.height,
                pd.volume,
                pd.wb_length,
                pd.wb_width,
                pd.wb_height,
                pd.wb_volume,
                pd.wb_weight_brutto,
                pd.wb_subject_id,
                pd.wb_brand
            FROM products_data pd
            JOIN (
                SELECT
                    id,
                    name 
                FROM products
                WHERE id = $1
            ) as p ON p.id = pd.product_id
            WHERE product_id = $1;
        """

        row = await self.pool.fetchrow(query, product_id)
        return ProductData(**row) if row else None

    async def update_wb_specifications(
        self,
        product_id: str,
        *,
        width: int | None = None,
        height: int | None = None,
        length: int | None = None,
        weight_brutto: float | None = None,
        brand: str | None = None,
        subject_id: int | None = None,
        user_id: int | None = None,
    ) -> None:
        """Обновить WB-спецификации товара в products_data."""
        query = """
            UPDATE products_data
            SET
        """

        params = []
        set_conditions = []
        
        if width is not None:
            set_conditions.append(f"wb_width = ${len(params) + 2}")
            params.append(width)

        if height is not None:
            set_conditions.append(f"wb_height = ${len(params) + 2}")
            params.append(height)

        if length is not None:
            set_conditions.append(f"wb_length = ${len(params) + 2}")
            params.append(length)

        if weight_brutto is not None:
            set_conditions.append(f"wb_weight_brutto = ${len(params) + 2}")
            params.append(weight_brutto)

        if brand is not None:
            set_conditions.append(f"wb_brand = ${len(params) + 2}")
            params.append(brand)

        if subject_id is not None:
            set_conditions.append(f"wb_subject_id = ${len(params) + 2}")
            params.append(subject_id)

        if user_id is not None:
            set_conditions.append(f"last_modified_by_user_id = ${len(params) + 2}")
            params.append(user_id)

        query += " " + ", ".join(set_conditions)
        query += " WHERE product_id = $1"

        if not params:
            return

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, product_id, *params)

    async def update_wb_subject(
        self,
        product_id: str,
        *,
        subject_id: int | None = None,
        user_id: int | None = None,
    ) -> None:
        """Обновить WB-спецификации товара в products_data."""
        query = """
            UPDATE products_data
            SET
        """

        params = []
        set_conditions = []

        if subject_id is None:
            return

        set_conditions.append(f"wb_subject_id = ${len(params) + 2}, wb_group_id = id")
        params.append(subject_id)

        if user_id is not None:
            set_conditions.append(f"last_modified_by_user_id = ${len(params) + 2}")
            params.append(user_id)

        query += " " + ", ".join(set_conditions)
        query += " WHERE product_id = $1"

        if not params:
            return

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, product_id, *params)

    async def create(self, product_id: str, user_id: Optional[int] = None):
        into_cols = "product_id"
        params_placeholders = "$1"
        params = [product_id]

        if user_id is not None:
            into_cols += ", last_modified_by_user_id"
            params_placeholders += ", $2"
            params.append(user_id)

        query = f"""
            INSERT INTO products_data ({into_cols})
            VALUES ({params_placeholders})
            ON CONFLICT (product_id) DO NOTHING;
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, *params)

    async def get_product_group_items(self, product_id: str) ->  list[ProductBase]:
        """
        Получить группу объединенных товаров из products_data.

        Args:
            product_id: локальный id товара.
        """
        query = """
            SELECT
                pd.product_id,
                mvph.product_name,
                mvph.product_photo_link
            FROM products_data pd
            JOIN (
                SELECT
                    product_id,
                    product_name,
                    MAX(product_photo_link) AS product_photo_link
                FROM mv_wb_product_health_analytics
                GROUP BY product_id, product_name
            ) mvph ON pd.product_id = mvph.product_id AND pd.wb_group_id = (
                    SELECT wb_group_id
                    FROM products_data
                    WHERE product_id = $1
                )
            ORDER BY pd.product_id ASC;
        """

        rows = await self.pool.fetch(query, product_id)

        return [ProductBase(**row) for row in rows]
    
    async def join_to_wb_group(self, target: str, product_ids: list[str]):
        if not product_ids:
            return

        query = """
            UPDATE products_data
            SET wb_group_id = t.wb_group_id
            FROM (
                SELECT wb_group_id
                FROM products_data
                WHERE product_id = $1
            ) t
            WHERE product_id = ANY($2)
            AND t.wb_group_id IS NOT NULL
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, target, product_ids)

    async def split_from_wb_group(self, product_ids: list[str]):
        if not product_ids:
            return

        query = """
            WITH current_group AS (
                SELECT 
                    id,
                    product_id, 
                    (product_id = ANY($2))::boolean AS is_moving
                FROM products_data
                WHERE wb_group_id = (
                    SELECT wb_group_id FROM products_data WHERE product_id = $1 LIMIT 1
                )
            ),
            new_group_values AS (
                SELECT 
                    is_moving,
                    MIN(id) 
                    AS new_wb_group_id
                FROM current_group
                GROUP BY is_moving
            )
            UPDATE products_data p
            SET wb_group_id = ng.new_wb_group_id
            FROM current_group cg
            JOIN new_group_values ng ON cg.is_moving = ng.is_moving
            WHERE p.product_id = cg.product_id;
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, product_ids[0], product_ids)
