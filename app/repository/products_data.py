import logging

from asyncpg import Pool

from app.domain.models import ProductData


logger = logging.getLogger(__name__)


class ProducsDataRepository:
    def __init__(self, pool: Pool):
        self.pool = pool
    
    async def get(self, product_id: str) -> ProductData:
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
                pd.wb_subject_id
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
        width: int,
        height: int,
        length: int,
        weight_brutto: float,
    ) -> None:
        """Обновить WB-спецификации товара в products_data."""
        query = """
            UPDATE products_data
            SET
                wb_width = $2,
                wb_height = $3,
                wb_length = $4,
                wb_weight_brutto = $5
            WHERE product_id = $1
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    query,
                    product_id,
                    width,
                    height,
                    length,
                    weight_brutto,
                )
