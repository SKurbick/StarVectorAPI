from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Characteristic(BaseModel):
    """Характеристика карточки товара."""

    id: int = Field(..., validation_alias="charcID")
    name: str
    subject_name: str = Field(..., validation_alias="subjectName")
    subject_id: int = Field(..., validation_alias="subjectID")
    required: bool
    unit_name: str = Field(..., validation_alias="unitName")
    max_count: int = Field(..., validation_alias="maxCount")
    popular: bool
    charc_type: str = Field(..., validation_alias="charcType")
    is_variable: bool = Field(..., validation_alias="isVariable")
    has_filter: bool = Field(..., validation_alias="hasFilter")
    exist_named_field: bool = Field(..., validation_alias="existNamedField")

    @field_validator("charc_type", mode="before")
    @classmethod
    def validate_charc_type(cls, value):
        char_types = {
            1: "array_of_str",
            4: "number",
            0: "notused"
        }
        if isinstance(value, int):
            return char_types.get(value, "unknown_type")

        return value

class Color(BaseModel):
    """Характеристика карточки товара Цвет."""

    name: str
    parent_name: str = Field(..., validation_alias="parentName")


class Country(BaseModel):
    """Характеристика карточки товара Страна производства."""

    id: int
    name: str
    full_name: str = Field(..., validation_alias="fullName")


class Brand(BaseModel):
    """Бренд карточки товара."""

    id: int
    logo_url: Optional[str] = Field(None, validation_alias="logoUrl")
    name: str
