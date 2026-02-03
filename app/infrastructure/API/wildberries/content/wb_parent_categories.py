import logging

from app.infrastructure.API.wildberries.base.client import HTTPMethod
from app.infrastructure.API.wildberries.content.base import ContentWBAPI
from app.infrastructure.API.wildberries.content.schemes.parent_category import ParentCategory


logger = logging.getLogger(__name__)


class ParentCategoriesWBAPI(ContentWBAPI):
    """API-клиент WB для родительских категорий."""

    GET_PARENTS_ENDPOINT = "/content/v2/object/parent/all"

    async def get_all_categories(self) -> list[ParentCategory]:
        """Метод возвращает все родительские категории."""
        response = await self._make_request(
            endpoint=self.GET_PARENTS_ENDPOINT,
            method=HTTPMethod.GET,
        )

        return [ParentCategory.model_validate(pc) for pc in response.get("data", [])]
