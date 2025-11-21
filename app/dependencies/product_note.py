from asyncpg import Pool
from fastapi import Depends, Request

from app.repository.product_note import ProductNoteRepository
from app.service.product_note import ProductNoteService


def get_pool(request: Request) -> Pool:
    return request.app.state.pool

def get_product_note_repository(pool: Pool = Depends(get_pool)) -> ProductNoteRepository:
    return ProductNoteRepository(pool=pool)

def get_product_note_service(repository: ProductNoteRepository = Depends(get_product_note_repository)) -> ProductNoteRepository:
    return ProductNoteService(repository=repository)