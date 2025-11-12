from asyncpg import Pool

from app.domain.models import OpenCardsRequest
from app.use_cases.card_use_cases import OpenCardUseCase


class OpenCardService:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def open_cards(self, data: OpenCardsRequest):
        card_opener = OpenCardUseCase(
            pool=self.pool
        )

        result = await card_opener.execute(data)
        return result
