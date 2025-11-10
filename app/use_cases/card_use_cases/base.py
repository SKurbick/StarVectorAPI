from abc import ABC, abstractmethod
from typing import Optional

from asyncpg import Pool

from app.repository.article import ArticleRepository


class BaseCardUseCase(ABC):
    def __init__(
        self, 
        pool: Pool,
    ) -> None:
        self.pool = pool

    @abstractmethod
    async def execute(self, *args, **kwargs):
        raise NotImplementedError


    async def get_validated_data(self, nm_ids: Optional[list[int]], local_vendor_codes: Optional[list[str]]) -> tuple[list[int], list[str], list[int]]:
        """
        Возвращает:
            - валидные nm_id (объединённые из nm_ids и local_vendor_codes),
            - local_vendor_codes, по которым ничего не найдено,
            - nm_ids, которых нет в БД.
        """
        article_repo = ArticleRepository(self.pool)
        all_nm_ids = set(nm_ids)

        not_found_local_codes = []

        if local_vendor_codes:
            found_by_local, not_found_local = await article_repo.get_articles_by_local_vendor_codes(
                local_vendor_codes
            )

            for nm_list in found_by_local.values():
                all_nm_ids.update(nm_list)

            not_found_local_codes = not_found_local


        if all_nm_ids:
            existing_nm, missing_nm = await article_repo.check_nm_ids_exist(list(all_nm_ids))
            not_found_nm_ids = missing_nm
            valid_nm_ids = existing_nm
        else:
            valid_nm_ids = []
            not_found_nm_ids = []

        return valid_nm_ids, not_found_local_codes, not_found_nm_ids
