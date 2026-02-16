import logging

from app.infrastructure.API.wildberries.base.client import HTTPMethod
from app.infrastructure.API.wildberries.content.base import ContentWBAPI
from app.infrastructure.API.wildberries.content.schemes.characteristic import (
    Characteristic, Color, Country, Brand
)
from app.infrastructure.cache import redis_cache_async


logger = logging.getLogger(__name__)


class CharcsWBAPI(ContentWBAPI):
    """API-клиент WB для характеристик."""

    GET_CHARCS_ENDPOINT = "/content/v2/object/charcs/{subject_id}"
    GET_COLORS_ENDPOINT = "/content/v2/directory/colors"
    GET_KINDS_ENDPOINT = "/content/v2/directory/kinds"
    GET_COUNTRIES_ENDPOINT = "/content/v2/directory/countries"
    GET_SEASONS_ENDPOINT = "/content/v2/directory/seasons"
    GET_VAT_ENDPOINT = "/content/v2/directory/vat"
    GET_BRANDS_ENDPOINT = "/api/content/v1/brands?subjectId={subject_id}"

    @redis_cache_async(ttl=300)
    async def get_charcs_by_subject_id(self, subject_id: int) -> list[Characteristic]:
        """Метод возвращает параметры характеристик предмета."""
        response = await self._make_request(
            endpoint=self.GET_CHARCS_ENDPOINT.format(subject_id=subject_id),
            method=HTTPMethod.GET,
        )

        return [Characteristic.model_validate(ch) for ch in response.get("data", [])]

    @redis_cache_async(ttl=300)
    async def get_colors(self) -> list[Color]:
        """Метод возвращает возможные значения характеристики предмета Цвет."""
        response = await self._make_request(
            endpoint=self.GET_COLORS_ENDPOINT,
            method=HTTPMethod.GET,
        )

        return [Color.model_validate(c) for c in response.get("data", [])]

    @redis_cache_async(ttl=300)
    async def get_kinds(self) -> list[str]:
        """Метод возвращает возможные значения характеристики предмета Пол."""
        response = await self._make_request(
            endpoint=self.GET_KINDS_ENDPOINT,
            method=HTTPMethod.GET,
        )

        return response.get("data", [])

    @redis_cache_async(ttl=300)
    async def get_countries(self) -> list[Country]:
        """Метод возвращает возможные значения характеристики предмета Страна производства."""
        response = await self._make_request(
            endpoint=self.GET_COUNTRIES_ENDPOINT,
            method=HTTPMethod.GET,
        )

        return [Country.model_validate(c) for c in response.get("data", [])]

    @redis_cache_async(ttl=300)
    async def get_seasons(self) -> list[str]:
        """Метод возвращает возможные значения характеристики предмета Сезон."""
        response = await self._make_request(
            endpoint=self.GET_SEASONS_ENDPOINT,
            method=HTTPMethod.GET,
        )

        return response.get("data", [])

    @redis_cache_async(ttl=300)
    async def get_vat(self) -> list[str]:
        """Метод возвращает возможные значения характеристики предмета Ставка НДС."""
        response = await self._make_request(
            endpoint=self.GET_VAT_ENDPOINT,
            method=HTTPMethod.GET,
        )

        return response.get("data", [])

    @redis_cache_async()
    async def get_brands(self, subject_id: int) -> list[Brand]:
        """Метод возвращает список брендов по ID предмета."""
        response = await self._make_request(
            endpoint=self.GET_BRANDS_ENDPOINT.format(subject_id=subject_id),
            method=HTTPMethod.GET,
        )

        return [Brand.model_validate(b) for b in response.get("brands", [])]
