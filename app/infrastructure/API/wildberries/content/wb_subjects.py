import logging
from typing import Optional

from app.infrastructure.API.wildberries.base.client import HTTPMethod
from app.infrastructure.API.wildberries.content.base import ContentWBAPI
from app.infrastructure.API.wildberries.content.schemes.subject import Subject
from app.infrastructure.cache import redis_cache_async


logger = logging.getLogger(__name__)


class SubjectsWBAPI(ContentWBAPI):
    """API-клиент WB для предметов."""

    GET_OBJECT_ENDPOINT = "/content/v2/object/all?limit={limit}&offset={offset}"

    @redis_cache_async(ttl=300)
    async def get_subjects_by_filters(
            self,
            name: Optional[str] = None,
            parent_id: Optional[int] = None,
    ) -> list[Subject]:
        """
        Получить предметы.

        Args:
            name: Название предметов (Находит по частичному совпадению).
            parent_id: id родительской категории.
        """
        finally_endpoint = self.GET_OBJECT_ENDPOINT

        if name:
            finally_endpoint += f"&name={name}"
        
        if parent_id:
            finally_endpoint += f"&parentID={parent_id}"

        all_subjects = []
        has_subjects = True
        step = 1000
        offset = 0
        limit = step

        while has_subjects:
            response = await self._make_request(
                endpoint=finally_endpoint.format(
                    limit=limit,
                    offset=offset
                ),
                method=HTTPMethod.GET,
            )

            subjects = response.get("data", [])

            if not subjects:
                has_subjects = False
                continue

            all_subjects.extend(subjects)
            offset += step
            limit += step

        return [Subject.model_validate(s) for s in all_subjects]
