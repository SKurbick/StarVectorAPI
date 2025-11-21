from asyncpg import Pool
from typing import NoReturn

from app.domain.models import ProductNoteUpdate
from app.repository.product_note import ProductNoteRepository


class ProductNoteService:
    def __init__(self, repository: ProductNoteRepository):
        self.repository = repository

    async def update_note(self, data: ProductNoteUpdate) -> NoReturn | dict:
        return await self.repository.update_note(data=data)