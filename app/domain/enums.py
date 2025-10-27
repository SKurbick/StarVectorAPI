from enum import Enum


class LossOwnerEnum(str, Enum):
    """Список владельцев потерь."""

    warehouse = "Склад"
    office = "Офис"
    supplier = "Поставщик"
    wb = "ВБ"
    manager_wb = "Менеджер ВБ"
    purchase = "Закупки"
    other = "Прочее"
