# from app.domain.models import SellerAccount
# from app.repository.seller_account import SellerAccountRepository


# class SellerAccountService:
#     """Сервис для управления аккаунтами продавцов."""

#     def __init__(self, repo: SellerAccountRepository):
#         self.repo = repo

#     async def get_list(self, is_active: bool | None = None) -> list[SellerAccount]:
#         """Получить список аккаунтов продавца."""
#         result = await self.repo.get_list()

#         if is_active is None:
#             return result
        
#         return [account for account in result if account.is_active == is_active]
