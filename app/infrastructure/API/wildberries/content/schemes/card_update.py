from typing import Optional, Union

from pydantic import BaseModel, Field

from app.infrastructure.API.wildberries.content.schemes.card_upload import (
    CardCharcCreate, CardDimensionsCreate, CardSizeCreate
)


class CardDimensionsUpdate(CardDimensionsCreate):
    """Габариты для обновления."""
    pass


class CardCharcUpdate(CardCharcCreate):
    """Характеристика для обновления."""
    pass


class CardSizeUpdate(BaseModel):
    """Размер для обновления карточки."""

    chrt_id: int = Field(..., serialization_alias="chrtID", description="ID размера")
    tech_size: str = Field(..., serialization_alias="techSize",description="Технический размер")
    wb_size: str = Field(..., serialization_alias="wbSize", description="Российский размер товара")
    price: Optional[int] = Field(None, description="Цена")
    skus: list[str] = Field(..., description="Баркоды")


class CardUpdate(BaseModel):
    """Модель обновления карточки (WB API)."""

    nm_id: int = Field(..., serialization_alias="nmID", description="Артикул WB")
    vendor_code: str = Field(..., serialization_alias="vendorCode", description="Артикул продавца")
    brand: str = Field("", description="Бренд")
    title: str = Field(..., description="Название")
    description: str = Field(..., description="Описание")
    dimensions: CardDimensionsUpdate = Field(..., description="Габариты")
    characteristics: list[CardCharcUpdate] = Field(..., description="Характеристики")
    sizes: list[Union[CardSizeUpdate, CardSizeCreate]] = Field(..., description="Размеры")
