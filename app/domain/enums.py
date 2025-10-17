from enum import Enum


class LossOwnerEnum(str, Enum):
    """Список владельцев потерь."""

    warehouse = "Склад"
    office = "Офис"
    supplier = "Поставщик"
    wb = "ВБ"
    other = "Прочее"
