from pydantic import BaseModel, Field


class Subject(BaseModel):
    """Предмет карточки товара."""

    id: int = Field(..., validation_alias="subjectID")
    name: str = Field(..., validation_alias="subjectName")
    parent_id: int = Field(..., validation_alias="parentID")
    parent_name: str = Field(..., validation_alias="parentName")
