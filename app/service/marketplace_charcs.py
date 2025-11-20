from aiohttp import ClientSession

from app.config.settings import settings
from app.domain.models import GetWbCharcsResponse

class MarketplaceCharcsService:
    async def get_subjects_charcs_from_wb(self, subject_id: int) -> GetWbCharcsResponse:
        """
        Получить характеристики предмета Wildberries.
        """
        url = settings.MARKETPLACE_CLIENT_APP_URL + f"/api/v1/charcs/wb?subject_id={subject_id}"
        
        async with ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
