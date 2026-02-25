from aiohttp import ClientSession

from app.config.settings import settings


class MarketplaceCardsAPI:
    """API-клиент для подключения к сервису карточек товаров на маркетплейсах."""
    _ip_address = settings.MARKETPLACE_CARDS_APP_IP_ADDRESS
    _port = settings.MARKETPLACE_CARDS_APP_PORT

    def __init__(self, session: ClientSession):
        self._base_url = f"http://{self._ip_address}:{self._port}/api"
        self._session = session

    async def _get_request(self, endpoint: str):
        async with self._session.get(
            url=self._base_url + endpoint
        ) as respone:
            return await respone.json()

    async def get_vat(self) -> list[str]:
        endponit = "/v1/wb/specifications/charcs/vat"
        return await self._get_request(endponit)

    async def get_brands(self, subject_id: int, limit: int = 1, offset: int = 0):
        endponit = f"/v1/wb/specifications/charcs/brands/{subject_id}?limit={limit}&offset={offset}"
        return await self._get_request(endponit)

    async def get_seasons(self):
        endponit = "/v1/wb/specifications/charcs/seasons"
        return await self._get_request(endponit)

    async def get_countries(self):
        endponit = "/v1/wb/specifications/charcs/countries"
        return await self._get_request(endponit)

    async def get_kinds(self):
        endponit = "/v1/wb/specifications/charcs/kinds"
        return await self._get_request(endponit)

    async def get_colors(self):
        endponit = "/v1/wb/specifications/charcs/colors"
        return await self._get_request(endponit)

    async def get_charcs_by_subject_id(self, subject_id: int):
        endponit = f"/v1/wb/specifications/charcs/list/{subject_id}"
        return await self._get_request(endponit)

    async def get_product_cards(self, product_id: str):
        endpoint = f"/v1/products/{product_id}/cards"
        return await self._get_request(endpoint)

    async def get_product_wb_specifications(self, product_id: str):
        endpoint = f"/v1/products/{product_id}/wb/specifications"
        return await self._get_request(endpoint)

    async def get_subjects_by_filters(self, parent_id: int | None = None):
        endpoint = "/v1/wb/specifications/subjects"
        if parent_id:
            endpoint += f"?parent_id={parent_id}"
        return await self._get_request(endpoint)

    async def get_all_categories(self):
        endpoint = "/v1/wb/specifications/categories"
        return await self._get_request(endpoint)

    async def get_predifined_charc_ids(self):
        endpoint = "/v1/wb/specifications/charcs/predifined"
        return await self._get_request(endpoint)
