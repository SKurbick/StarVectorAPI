# from app.repository.banned_cards import BannedCardRepository
# from app.domain.models import BannedWBCardScheme

# class BannedCardService:
#     """
#     Сервис для работы с забанеными карточками WB.
#     """

#     def __init__(self, banned_card_repo: BannedCardRepository):
#         self._banned_card_repo = banned_card_repo

#     async def get_list(self) -> list[BannedWBCardScheme]:
#         """
#         Получить список забаненых карточек товаров на WB.
#         """
#         data = await self._banned_card_repo.get_list()

#         return [
#             BannedWBCardScheme(
#                 account=item.wb_account,
#                 nm_id=item.nm_id,
#                 vendor_code=item.vendor_code,
#                 brand=item.brand,
#                 title=item.title,
#                 reason=item.reason,
#                 banned_date=item.created_at,
#             )
#             for item in data
#         ]
