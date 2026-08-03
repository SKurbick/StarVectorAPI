# from asyncpg import Pool

# from app.domain.models import BannedWBCardModel


# class BannedCardRepository:
#     """
#     Репозиторий для работы с забанеными карточками товаров.
#     """

#     def __init__(self, pool: Pool):
#         self._pool = pool

#     async def get_list(self) -> list[BannedWBCardModel]:
#         """
#         Получить список забаненых карточек товаров.
#         """
#         query = """
#             SELECT 
#                 id,
#                 wb_account,
#                 brand,
#                 nm_id,
#                 title,
#                 vendor_code,
#                 reason,
#                 created_at
#             FROM banned_products
#             ORDER BY created_at DESC;
#         """

#         rows = await self._pool.fetch(query)
#         return [BannedWBCardModel(**row) for row in rows]
