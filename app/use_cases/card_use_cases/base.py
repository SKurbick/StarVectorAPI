# from abc import ABC, abstractmethod
# from typing import Optional

# from asyncpg import Pool

# from app.repository.article import ArticleRepository
# from app.domain.models import CardDataByAccountRequest


# class BaseCardUseCase(ABC):
#     def __init__(
#         self,
#         pool: Pool,
#     ) -> None:
#         self.pool = pool

#     @abstractmethod
#     async def execute(self, *args, **kwargs):
#         raise NotImplementedError

#     async def get_validated_data(self, data: CardDataByAccountRequest) -> tuple[dict[str, list[int]], list[str], list[int]]:
#         article_repo = ArticleRepository(self.pool)

#         all_nm_ids = set()

#         if data.accounts:
#             nm_ids_request = [nm for acc, nms in data.accounts.items() for nm in nms.nm_ids]
#             all_nm_ids.update(set(nm_ids_request))

#         not_found_local_codes = []

#         if data.local_vendor_codes:
#             found_by_local, not_found_lvc = await article_repo.get_articles_by_local_vendor_codes(
#                 data.local_vendor_codes
#             )

#             for nm_list in found_by_local.values():
#                 all_nm_ids.update(nm_list)

#             not_found_local_codes = not_found_lvc


#         if all_nm_ids:
#             existing_nm, missing_nm = await article_repo.check_nm_ids_exist(list(all_nm_ids))
#             not_found_nm_ids = missing_nm
#             valid_nm_ids = existing_nm
#         else:
#             valid_nm_ids = []
#             not_found_nm_ids = []

#         nms_by_accounts = await article_repo.get_accounts_by_nm_ids(valid_nm_ids)

#         return nms_by_accounts, not_found_local_codes, not_found_nm_ids
