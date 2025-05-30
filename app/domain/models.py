from datetime import datetime, date
from typing import Optional, List, Union, Dict, Literal

from pydantic import BaseModel, field_validator, model_validator, RootModel, field_validator
from pydantic import ConfigDict

from pydantic import Field

# Общий словарь с конфигурациями полей
field_configs = {
    "article_id": Field(..., description="Артикул WB"),
    "account": Field(..., description="ЛК. Аккаунт продавца"),
    "subject_name": Field(description="Предмет"),
    "price": Field(description="Цена товара"),
    "discount": Field(description="Скидка на товар"),
    "length": Field(description="Длина (в см)"),
    "width": Field(description="Ширина (в см)"),
    "height": Field(description="Высота (в см)"),
    "barcode": Field(..., description="Баркод", min_length=8, max_length=128),
    "logistic_from_wb_wh_to_opp": Field(..., description="Логистика от склада WB до ПВЗ", ge=1),
    "commission_wb": Field(..., description="Комиссия WB"),
    "last_update_time": Field(..., description="Время последнего обновления данных"),
    "vendor_code": Field(..., description="Артикул продавца"),
    "local_vendor_code": Field(..., description="Wild. Локальный артикул продавца"),
    "photo_link": Field(..., description="Ссылка на фотографию товара"),
    "purchase_price": Field(default=None, description="Закупочная стоимость"),
    "status_by_lvc": Field(default=None, description="Состояние если нет закупочной стоимости"),
    "rating": Field(default=None, description="Рейтинг")
}


class ResponseMessage(BaseModel):
    status: int
    message: str


class ArticleBase(BaseModel):
    article_id: int = field_configs['article_id']


class AccountBase(BaseModel):
    account: str = field_configs['account']


class ArticleInDB(ArticleBase, AccountBase):
    vendor_code: str = field_configs['vendor_code']
    local_vendor_code: str = field_configs['local_vendor_code']


class CardData(ArticleBase):
    local_card_name: Union[str, None]
    manager: Union[str, None]
    subject_name: Union[str, None] = field_configs['subject_name']
    photo_link: Union[str, None] = field_configs['photo_link']
    # price: Union[int, None] = field_configs['price']
    # discount: Union[int, None] = field_configs['discount']
    length: Union[int, None] = field_configs['length']
    width: Union[int, None] = field_configs['width']
    height: Union[int, None] = field_configs['height']
    barcode: Union[str, None] = field_configs['barcode']
    # logistic_from_wb_wh_to_opp: Union[float, None] = field_configs['logistic_from_wb_wh_to_opp']
    # commission_wb: Union[float, None] = field_configs['commission_wb']
    rating: Union[float, None] = field_configs['commission_wb']

    # last_update_time: datetime = field_configs['last_update_time']

    class Config:
        json_schema_extra = {
            "examples": [{
                "local_card_name": "Мультиварка супер power editions пяу мяу",
                "manager": "Андрей Мухоморов",
                "article_id": 174998583,
                "subject_name": "Мультиварки",
                "photo_link": "https://basket-12.wbbasket.ru/vol1749/part174998/174998583/images/tm/1.webp",
                "price": 123,
                "discount": 123,
                "length": 12,
                "width": 12,
                "height": 12,
                "barcode": "123456789123",
                "logistic_from_wb_wh_to_opp": 123.12,
                "commission_wb": 12.12,
            }]
        }


class CostPrice(BaseModel):
    local_vendor_code: str = field_configs['local_vendor_code']
    # purchase_price: Optional[int] = field_configs['purchase_price']
    status_by_lvc: Optional[str] = field_configs['status_by_lvc']

    # purchase_price: Optional[int] = Field(default=None, description="Закупочная стоимость")
    # status_by_lvc: Optional[str] = Field(default=None, description="Состояние если нет закупочной стоимости")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "local_vendor_code": "wild123",
                    "purchase_price": 1999,
                    "status_by_lvc": None,
                },
                {
                    "local_vendor_code": "wild123",
                    "purchase_price": None,
                    "status_by_lvc": "Нет в продаже",
                },
            ]
        }


class ArticleDetails(AccountBase, CostPrice, CardData):
    stocks_quantity: Union[int, None]

    class Config:
        json_schema_extra = {
            "examples": [
                {"article_id": 174998583,
                 "local_card_name": "Мультиварка супер power editions пяу мяу",
                 "manager": "Андрей Мухоморов",
                 "account": "ТОНОЯН",
                 "local_vendor_code": "wild123",
                 # "purchase_price": 1999,
                 "status_by_lvc": None,
                 "subject_name": "Фены",
                 "photo_link": "https://basket-12.wbbasket.ru/vol1749/part174998/174998583/images/tm/1.webp",
                 # "price": 123,
                 # "discount": 123,
                 "length": 12,
                 "width": 12,
                 "height": 12,
                 "barcode": "123456789123",
                 # "logistic_from_wb_wh_to_opp": 123.12,
                 # "commission_wb": 12.12,
                 "rating": 4.99,
                 "stocks_quantity": 123
                 },
            ]
        }


class PriceDiscountDB(ArticleBase):
    price: Optional[int] = None
    discount: Optional[int] = None


class CreatePriceDiscount(BaseModel):
    nmID: int
    price: Optional[int] = None
    discount: Optional[int] = None

    @classmethod
    @field_validator('price', 'discount', mode='before')
    def check_at_least_one_provided(cls, value, info):
        """
        Проверка: должно быть указано хотя бы одно из полей price или discount.
        """
        fields = info.data  # Доступ к другим полям модели
        if 'price' in fields and fields['price'] is not None:
            return value  # Если price указан, проверка пройдена
        if 'discount' in fields and fields['discount'] is not None:
            return value  # Если discount указан, проверка пройдена
        if value is not None:
            return value  # Если текущее поле указано, проверка пройдена

        raise ValueError("At least one of 'price' or 'discount' must be provided")

    @model_validator(mode='after')
    def check_at_least_one_provided(self) -> 'CreatePriceDiscount':
        """
        Проверка: должно быть указано хотя бы одно из полей price или discount.
        """
        if self.price is not None or self.discount is not None:
            return self  # Проверка пройдена

        raise ValueError("At least one of 'price' or 'discount' must be provided")


class PriceDiscountContainer(BaseModel):
    data: List[CreatePriceDiscount]


class PriceDiscountResponseModel(BaseModel):
    update_data: Dict[str, PriceDiscountContainer]

    class Config:
        json_schema_extra = {
            "example": {
                "update_data": {
                    "ЛОПАТИНА": {
                        "data": [
                            {
                                "nmID": 1234,
                                "price": 63,
                                "discount": 63
                            }
                        ]
                    },
                    "ХАЧАТРЯН": {
                        "data": [
                            {
                                "nmID": 5678,
                                "price": 63,
                                "discount": 63
                            }
                        ]
                    },
                    "ПИЛОСЯН": {
                        "data": [
                            {
                                "nmID": 9101,
                                "price": 63,
                                "discount": 63
                            }
                        ]
                    }
                }
            }
        }


class OrdersRevenues(BaseModel):
    date: date
    orders_sum_rub: int  # заказали на сумму в руб.
    orders_count: int  # заказали товаров, шт
    open_card_count: int  # количество переходов в карточку товара
    add_to_cart_count: int  # положили в корзину, штук
    buyouts_count: int  # выкупили товаров
    buyouts_sum_rub: int  # выкупили на сумму в руб
    cancel_count: int  # отменили товаров шт.
    cancel_sum_rub: int  # отменили на сумму в руб

    class Config:
        json_schema_extra = {
            "example": {
                'article_id': 123123123,
                'date': '2024-12-12',
                'orders_sum_rub': 123,
                'orders_count': 123,
                'open_card_count': 123,
                'add_to_cart_count': 123,
                'buyouts_count': 123,
                'buyouts_sum_rub': 123,
                'cancel_count': 123,
                'cancel_sum_rub': 123,
            }
        }


class OrdersRevenuesResponseModel(ArticleBase):
    data: List[OrdersRevenues]


class UnitEconomics(PriceDiscountDB):
    discounted_price: Union[float, None]
    will_be_credited_bank_account: Union[float, None]
    logistic_from_wb_wh_to_opp: Union[float, None]
    commission_wb: Union[float, None]
    simplified_tax_system: Union[float, None]
    percent_by_tax: Union[int, None]
    will_receive_wb: Union[float, None]
    wb_expenses: Union[float, None]
    profitability_percent: Union[float, None]
    marginality_percent: Union[float, None]
    net_profit: Union[float, None]
    cost_price: Union[int, None]
    net_profit_by_personal_terms: Union[float, None]
    marginality_percent_on_personal_terms: Union[float, None]

    @field_validator(
        'discounted_price',
        'will_be_credited_bank_account',
        'logistic_from_wb_wh_to_opp',
        'commission_wb',
        'simplified_tax_system',
        'will_receive_wb',
        'wb_expenses',
        'profitability_percent',
        'marginality_percent',
        'net_profit',
        'net_profit_by_personal_terms',
        'marginality_percent_on_personal_terms',
        mode='before')
    def round_float_values(cls, v: Optional[Union[float, str]]) -> Optional[float]:
        if v is None or v == '':
            return None
        try:
            return round(float(v), 2)
        except (ValueError, TypeError):
            return None


class PeriodRequestModel(BaseModel):
    date_from: date
    date_to: date = Field(default_factory=date.today)


class ProfitData(BaseModel):
    date: date
    net_profit: int


class NetProfitResponseModel(ArticleBase):
    data: List[ProfitData]


class PercentByTaxResponseModel(ArticleBase):
    percent_by_tax: int


class DefaultPercentByTaxResponseModel(BaseModel):
    default_percent_by_tax: int


class StocksQuantity(ArticleBase):
    data: Dict[str, Union[None, int]]


class SkuAmountResponseModel(BaseModel):
    sku: str
    amount: int


class UpdateStocksQuantityResponseModel(BaseModel):
    stocks: List[SkuAmountResponseModel]


# Модель для данных внутри каждого федерального округа
class FederalDistrictData(BaseModel):
    daily_average: Union[float, None]
    balance_for_number_of_days: Union[float, None]

    @field_validator('daily_average', 'balance_for_number_of_days', mode='before')
    def round_float_values(cls, v: Optional[Union[float, str]]) -> Optional[float]:
        if v is None or v == '':
            return 0
        try:
            return round(float(v), 2)
        except (ValueError, TypeError):
            return None


# Модель для данных по каждому федеральному округу (словарь с ключами - названиями округов)
class TurnoverByFederalDistrict(RootModel):
    root: Dict[str, FederalDistrictData]

    def __getitem__(self, item):
        return self.root[item]

    def __iter__(self):
        return iter(self.root)

    def __len__(self):
        return len(self.root)


# Модель для всего набора данных (внешний словарь с ключами - числами)
class TurnoverByFederalDistrictData(RootModel):
    root: Dict[int, TurnoverByFederalDistrict]

    def __getitem__(self, item):
        return self.root[item]

    def __iter__(self):
        return iter(self.root)

    def __len__(self):
        return len(self.root)

    class Config:
        json_schema_extra = {
            "example": {
                123455677: {
                    "Центральный":
                        {"daily_average": 500,
                         "balance_for_number_of_days": 50},
                    "Северо-Кавказский":
                        {"daily_average": 500,
                         "balance_for_number_of_days": 50},
                },
                765432112: {
                    "Центральный":
                        {"daily_average": 500,
                         "balance_for_number_of_days": 50},
                    "Приволжский":
                        {"daily_average": 500,
                         "balance_for_number_of_days": 50},
                },
            }
        }


def transform_asyncpg_data(asyncpg_data: List[dict]) -> Dict[int, Dict[str, FederalDistrictData]]:
    transformed_data = {}
    for row in asyncpg_data:
        id_ = row["article_id"]
        district = row["federal_district"]
        data = FederalDistrictData(
            daily_average=row["daily_average"],
            balance_for_number_of_days=row["balance_for_number_of_days"]
        )
        if id_ not in transformed_data:
            transformed_data[id_] = {}
        transformed_data[id_][district] = data
    return transformed_data


class WeeklyOrdersResponse(RootModel[Dict[int, Dict[str, int]]]):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                # "description": "Ключи словаря - целые числа (article_id)",
                "value": {
                    12345678: {
                        "03.24-03.30": 15000,
                        "03.17-03.23": 7800
                    },
                    87654321: {
                        "03.24-03.30": 4200
                    }
                },
                "summary": "Пример успешного ответа"
            }]
        }
    )
