from fastapi import APIRouter, Depends, status

from app.dependencies.product_note import get_product_note_service
from app.domain.models import ProductNoteUpdate, ResponseMessage
from app.service.product_note import ProductNoteService


router = APIRouter(prefix="/product_note", tags=["Заметки к товарам"])

@router.put("/update_note", status_code=status.HTTP_200_OK,
            description="Обновление заметок к товару")
async def update_note(
    data: ProductNoteUpdate,
    service: ProductNoteService = Depends(get_product_note_service)
) -> ResponseMessage:
    await service.update_note(data=data)
    return ResponseMessage(
        status=status.HTTP_200_OK,
        message="Product notes successfully updated."
    )