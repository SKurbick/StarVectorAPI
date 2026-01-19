from typing import Self
from enum import Enum


class LossOwnerEnum(Enum):
    """Список владельцев потерь."""

    warehouse = (1, "Склад")
    office = (2, "Офис")
    supplier = (3, "Поставщик")
    wb = (4, "ВБ")
    manager_wb = (5, "Менеджер ВБ")
    purchase = (6, "Закупки")
    other = (7, "Прочее")

    def __init__(self, id_: int, value_for_db: str):
        self._id = id_
        self._value_for_db = value_for_db

    @property
    def id(self) -> int:
        return self._id

    @property
    def value_for_db(self) -> str:
        return self._value_for_db

    @classmethod
    def from_id(cls, id_: int) -> Self:
        for item in cls:
            if item.id == id_:
                return item

        raise ValueError(f"Invalid loss owner ID: {id_}")

    @classmethod
    def from_db_value(cls, value: str) -> Self:
        for item in cls:
            if item.value_for_db == value:
                return item

        raise ValueError(f"Invalid loss owner DB value: {value}")


class CardStatusEnum(str, Enum):
    """Список возможных статусов карточек товара"""

    closed = "closed"
    active = "active"
    closing_pending = "closing_pending"
    new = "new"
    on_sale = "on_sale"
    trashed = "trashed"
    deleted = "deleted"


class ExcelParserEnum(Enum):
    "Соответствие названия ключа с позицией столбца в Excel файле"

    penalty_date = 1
    nm_id = 5
    bonus_type_name = 4
    srid = 13
    loss_owner = 28
    comment = 29


class FinancialReportingEnum(str, Enum):
    """Временные периоды для формирования отчётности."""
    month = "month"
    week = "week"
