# from asyncpg import Pool
# from fastapi import Depends

# from app.dependencies.database import get_pool
# from app.repository.products_data import ProducsDataRepository


# def get_products_data_repository(
#         pool: Pool = Depends(get_pool)
# ) -> ProducsDataRepository:
#     return ProducsDataRepository(pool)
