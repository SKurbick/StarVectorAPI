from asyncpg import Pool

from app.domain.models import ProductData


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
