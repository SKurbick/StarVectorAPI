from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class CardDimensions(BaseModel):
    """Габариты и вес товара."""

    width: int = Field(..., description="Ширина, см")
    height: int = Field(..., description="Высота, см")
    length: int = Field(..., description="Длина, см")
    weight_brutto: float = Field(..., validation_alias="weightBrutto", description="Вес брутто, кг")
    is_valid: bool = Field(..., validation_alias="isValid", description="Флаг корректности габаритов")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "width": 200,
                    "height": 150,
                    "length": 300,
                    "weight_brutto": 1.25,
                    "is_valid": True
                }
            ]
        }
    )


class CardTag(BaseModel):
    """Тег карточки товара."""

    id: int = Field(..., description="ID тега")
    name: str = Field(..., description="Название тега")
    color: str = Field(..., description="Цвет тега в HEX", examples=["#FF5733"])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"id": 101, "name": "Новинка", "color": "#FF5733"}
            ]
        }
    )


class CardWholesale(BaseModel):
    """Оптовые настройки товара."""

    enabled: bool = Field(..., description="Включена ли оптовая продажа")
    quantum: Optional[int] = Field(None, description="Минимальная партия для опта")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"enabled": False, "quantum": None},
                {"enabled": True, "quantum": 10}
            ]
        }
    )


class CardCharc(BaseModel):
    """Характеристика карточки товара."""

    id: int = Field(..., description="ID характеристики в WB")
    name: str = Field(..., description="Название характеристики")
    value: Union[int, float, list[str]] = Field(..., description="Значение характеристики")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"id": 12345, "name": "Цвет", "value": "Красный"},
                {"id": 67890, "name": "Размер", "value": 42}
            ]
        }
    )


class CardSize(BaseModel):
    """Размер товара."""

    chrt_id: int = Field(..., validation_alias="chrtID", description="Уникальный ID размера в WB")
    tech_size: str = Field(..., validation_alias="techSize", description="Технический размер")
    wb_size: str = Field(..., validation_alias="wbSize", description="Российский размер товара")
    price: Optional[int] = Field(None, description="Цена за размер, руб")
    skus: list[str] = Field(..., description="Список баркодов (SKU) для размера")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "chrt_id": 1234567,
                    "tech_size": "42",
                    "wb_size": "M",
                    "price": 1990,
                    "skus": ["203847293847"]
                }
            ]
        }
    )


class Card(BaseModel):
    """Полная модель карточки товара Wildberries."""

    nm_id: int = Field(..., validation_alias="nmID", description="Артикул Wildberries (nmID)")
    imt_id: int = Field(..., validation_alias="imtID", description="ID номенклатурной матрицы")
    nm_uuid: str = Field(..., validation_alias="nmUUID", description="Уникальный UUID карточки")
    subject_id: int = Field(..., validation_alias="subjectID", description="ID предмета")
    subject_name: str = Field(..., validation_alias="subjectName", description="Название предмета")
    vendor_code: str = Field(..., validation_alias="vendorCode", description="Артикул продавца")
    brand: Optional[str] = Field(None, description="Бренд")
    title: Optional[str] = Field(None, description="Название товара")
    description: Optional[str] = Field(None, description="Описание товара",)
    need_kiz: bool = Field(..., validation_alias="needKiz", description="Требуется ли КИЗ (маркировка)")
    photos: Optional[list[dict[str, str]]] = Field([], description="Список URL фото", examples=[[{"big": "https://..."}]])
    video: Optional[str] = Field(None, description="URL видео")
    wholesale: Optional[CardWholesale] = Field(None, description="Оптовые настройки")
    dimensions: CardDimensions = Field(..., description="Габариты товара")
    characteristics: list[CardCharc] = Field([], description="Характеристики")
    sizes: list[CardSize] = Field(..., description="Размеры товара")
    tags: list[CardTag] = Field([], description="Теги")
    created_at: datetime = Field(..., validation_alias="createdAt", description="Дата создания карточки")
    updated_at: datetime = Field(..., validation_alias="updatedAt", description="Дата последнего обновления")
