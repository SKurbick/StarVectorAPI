from typing import List

from app.repository.card_data import CardDataRepository
from app.domain.models import CardData


class CardDataService:
    def __init__(self, card_data_repository: CardDataRepository):
        self.card_data_repository = card_data_repository

    async def get_card_data_by_article_id(self, article_id: int) -> CardData:
        return await self.card_data_repository.get_card_data_by_article_id(article_id)

    async def get_all_card_data(self) -> List[CardData]:
        return await self.card_data_repository.get_all_card_data()
