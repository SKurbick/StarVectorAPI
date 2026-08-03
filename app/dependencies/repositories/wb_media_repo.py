# from asyncpg import Pool
# from fastapi import Depends

# from app.dependencies.database import get_pool
# from app.repository.wb_media import WBMediaRepository


# def get_wb_media_repository(
#         pool: Pool = Depends(get_pool)
# ) -> WBMediaRepository:
#     return WBMediaRepository(pool)
