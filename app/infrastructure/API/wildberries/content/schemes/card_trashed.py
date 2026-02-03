from datetime import datetime

from pydantic import BaseModel, Field

from app.infrastructure.API.wildberries.content.schemes.card import (
    CardDimensions, CardCharc, CardSize
)


class CardTrashed(BaseModel):
    """Модель карточки, перемещённой в корзину."""

    nm_id: int = Field(..., validation_alias="nmID", description="Артикул Wildberries")
    subject_id: int = Field(..., validation_alias="subjectID", description="ID предмета", examples=[100])
    subject_name: str = Field(..., validation_alias="subjectName", description="Название предмета")
    vendor_code: str = Field(..., validation_alias="vendorCode", description="Артикул продавца")
    dimensions: CardDimensions = Field(..., description="Габариты")
    characteristics: list[CardCharc] = Field(..., description="Характеристики")
    sizes: list[CardSize] = Field(..., description="Размеры товара")
    created_at: datetime = Field(..., validation_alias="createdAt", description="Дата создания")
    trashed_at: datetime = Field(..., validation_alias="trashedAt", description="Дата перемещения в корзину")


class CardsToTrash(BaseModel):
    """Карточки товаров на перемещение в корзину."""

    nm_ids: int = Field(..., serialization_alias="nmIDs", description="Артикулы WB")
