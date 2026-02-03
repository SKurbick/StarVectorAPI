from pydantic import BaseModel, Field


class CardMediaUploadByLinks(BaseModel):
    """Модель для загрузки медиа по ссылкам."""

    nm_id: int = Field(..., serialization_alias="nmId", description="Артикул WB")
    data: list[str] = Field(default_factory=list, description="Список ссылок на медиа")
