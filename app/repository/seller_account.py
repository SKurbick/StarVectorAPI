# import asyncpg

# from app.domain.models import SellerAccount


# class SellerAccountRepository:
#     """Репозиторий для управления аккаунтами продавцов."""

#     def __init__(self, pool: asyncpg.Pool):
#         self.pool = pool

#     async def get_list(self) -> list[SellerAccount]:
#         """Получить список всех аккаунтов продавца."""
#         query = """
#             SELECT
#                 sa.id,
#                 sa.account_name,
#                 sa.is_active,
#                 sa.inn,
#                 sa.vat_rate
#             FROM
#                 seller_account sa
#             ORDER BY sa.account_name
#         """

#         rows =  await self.pool.fetch(query)

#         return [SellerAccount(**row) for row in rows]
