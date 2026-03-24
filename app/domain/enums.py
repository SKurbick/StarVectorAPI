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


class PredefinedWBCharcEnum(int, Enum):
    """ID характеристик WB для которых можно получить варианты значений."""

    VAT = 15001405
    COUNTRY = 14177451
    COLOR = 14177449
    KIND = 204557
    SEASON = 18769


class CertificationCharсEnum(int, Enum):
    "ID характеристик WB, которые хранят информацию о сертификатах и декларациях товаров."

    EXPIRATION_DATE = 15001138  # Дата окончания действия сертификата/декларации
    REGISTRATION_DATE = 15001137  # Дата регистрации сертификата/декларации
    DECLARATION_NUMBER = 15001135  # Номер декларации соответствия
    CERTIFICATE_NUMBER = 15001136  # Номер сертификата соответствия


class GlobalProductWBStatus(str, Enum):
    """Статус товара по состоянию карточек на ВБ"""

    OK = "ok"
    HAS_WARNING = "has_warning"
    HAS_ERROR = "has_error"


class ProductAccountHealthWBStatus(str, Enum):
    """Статус аккаунта по состоянию карточек на ВБ"""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class ProductWBIssueType(str, Enum):
    """
    Список проблемных состояний товара по карточкам на WB.

    Args:
        PRICE_DEVIATION: Разброс цен выше порогового значения.
    """

    PRICE_DEVIATION = "price_deviation"


class AccountWBIssueType(str, Enum):
    """
    Список проблемных состояний аккаунта по товару карточек на WB.
    
    Args:
        MULTIPLE_ACTIVE_CARDS: Несколько активных карточек товара.
        VAT_MISMATCH: Расхождение НДС карточки и установленного для аккаунта.
        LOW_RATING: Рейтинг карточки ниже порогового значения.
        NO_ACTIVE_CARDS: Нет активных карточек.
        READY_TO_ACTIVATE: Есть карточки, готовые стать активными.
    """

    MULTIPLE_ACTIVE_CARDS = "multiple_active_cards"
    VAT_MISMATCH = "vat_mismatch"
    LOW_RATING = "low_rating"
    NO_ACTIVE_CARDS = "no_active_cards"
    READY_TO_ACTIVATE = "ready_to_activate"
