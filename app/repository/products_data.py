import logging
from typing import Optional

from asyncpg import Pool

from app.domain.models import ProductData


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
        
        if width is not None:
            query += f" wb_width = ${len(params) + 2}"
            params.append(width)

        if height is not None:
            query += f" wb_height = ${len(params) + 2}"
            params.append(height)

        if length is not None:
            query += f" wb_length = ${len(params) + 2}"
            params.append(length)

        if weight_brutto is not None:
            query += f" wb_weight_brutto = ${len(params) + 2}"
            params.append(weight_brutto)

        if brand is not None:
            query += f" wb_brand = ${len(params) + 2}"
            params.append(brand)

        if subject_id is not None:
            query += f" wb_subject_id = ${len(params) + 2}"
            params.append(subject_id)

        if user_id is not None:
            query += f" last_modified_by_user_id = ${len(params) + 2}"
            params.append(user_id)

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
