from datetime import date, datetime
from typing import Optional, List, Union, Dict

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, RootModel

from app.domain.enums import LossOwnerEnum


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
    "rating": Field(default=None, description="Рейтинг"),
    "manager": Field(..., description="Мэнеджер"),
    "product_name": Field(..., description="Наименование товара"),
    "products_list": Field(..., description="Список товаров"),
    "articles_list": Field(..., description="Список карточек товара"),
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


class ArticleResponse(ArticleBase):
    """Модель ответа с данными карточки товара."""

    photo_link: str | None = field_configs["photo_link"]
    price: int | None = field_configs["price"]
    discount: int | None = field_configs["discount"]
    barcode: str | None = field_configs["barcode"]
    rating: float | None = field_configs["rating"]
    length: int | None = field_configs["length"]
    width: int | None = field_configs["width"]
    height: int | None = field_configs["height"]
    manager: str | None = field_configs["manager"]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "article_id": 176869522,
                    "photo_link": "https://example.com/images/tm/1.webp",
                    "price": 2130,
                    "discount": 52,
                    "barcode": "2043334453898",
                    "rating": 4.7,
                    "length": 42,
                    "width": 22,
                    "height": 19,
                    "manager": "Петров Пётр"
                },
            ]
        }
    )


class ProductResponse(BaseModel):
    """Модель ответа с данными товара."""

    id: str = field_configs["local_vendor_code"]
    name: str = field_configs["product_name"]
    photo_link: str | None = field_configs["photo_link"]
    length: int | None = field_configs["length"]
    width: int | None = field_configs["width"]
    height: int | None = field_configs["height"]
    manager: str | None = field_configs["manager"]

    articles: list[ArticleResponse] = field_configs["articles_list"]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "wild123",
                    "name": "Монитор Redmi",
                    "photo_link": "https://example.com/images/tm/1.webp",
                    "length": 100,
                    "width": 50,
                    "height": 20,
                    "manager": "Иванов Иван",
                    "articles": [
                        ArticleResponse.model_config['json_schema_extra']['examples'][0],
                        {
                            "article_id": 176869523,
                            "photo_link": "https://example.com/images/tm/2.webp",
                            "price": 2120,
                            "discount": 25,
                            "barcode": "2043334453393",
                            "rating": 4.1,
                            "length": 42,
                            "width": 22,
                            "height": 19,
                            "manager": "Иванов Иван"
                        }
                    ]
                }
            ]
        }
    )


class SubjectDataWithProductsResponse(BaseModel):
    """Модель ответа с данными предмета и списком товаров."""

    subject_name: str | None = field_configs["subject_name"]

    products: list[ProductResponse] = field_configs["products_list"]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "subject_name": "Мониторы",
                    "products": [
                        ProductResponse.model_config['json_schema_extra']['examples'][0],
                        {
                            "id": "wild456",
                            "name": "Монитор ACER",
                            "photo_link": "https://example.com/images/tm/2.webp",
                            "length": 300,
                            "width": 200,
                            "height": 15,
                            "manager": "Сидорова Мария",
                            "articles": [
                                ArticleResponse.model_config['json_schema_extra']['examples'][0],
                                {
                                    "article_id": 176869523,
                                    "photo_link": "https://example.com/images/tm/2.webp",
                                    "price": 3590,
                                    "discount": 41,
                                    "barcode": "2043334453444",
                                    "rating": 4.7,
                                    "length": 43,
                                    "width": 21,
                                    "height": 21,
                                    "manager": "Сидорова Мария"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    )


class FinReportDeduction(BaseModel):
    """Модель для вычетов из финансового отчета."""

    grouped_bonus_type_name: Optional[str] = Field(..., description="Виды логистики, штрафов и корректировок ВВ")
    total_deduction: Optional[float] = Field(..., description="Удержания")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "grouped_bonus_type_name": "Оказание услуг «ВБ.Продвижение»",
                    "total_deduction": 1111391
                },
            ]
        }
    )


class WeeklyFinReportsAggregated(BaseModel):
    """Модель для агрегированных недельных финансовых отчетов WB."""

    date_to: date = Field(..., description="Дата")
    wb_commission: float = Field(..., description="Комиссия ВБ")
    wb_commission_percentage: float = Field(..., description="Комиссия ВБ, %")
    to_be_transferred: float = Field(..., description="К перечислению")
    logistics: float = Field(..., description="Логистика")
    total_to_be_paid: float = Field(..., description="Итого к оплате")
    revenue: float = Field(..., description="Выручка")
    discounted_retail_price: float = Field(..., description="Розничная цена со скидкой")
    penalty: float = Field(..., description="Штрафы")
    storage_fee: float = Field(..., description="Хранение")
    paid_acceptance: float = Field(..., description="Платная приемка")
    credit_transfers: float = Field(..., description="Перечисления по кредиту")
    to_client_upon_cancellation: float = Field(..., description="К клиенту при отмене")
    from_client_upon_cancellation: float = Field(..., description="От клиента при отмене")
    from_client_upon_return: float = Field(..., description="От клиента при при возврате")
    to_client_upon_sale: float = Field(..., description="К клиенту при продаже")
    purchase_price_of_sales: int = Field(..., description="Закупочная стоимость продаж")
    purchase_price_of_returns: int = Field(..., description="Закупочная стоимость возвратов")
    purchase_cost: int = Field(..., description="Закупочная стоимость")
    our_share_before_cost: float = Field(..., description="Наша доля до вычета себестоимости")
    vp_after_wb: float = Field(..., description="ВП после ВБ")
    vp_after_wb_percentage: float = Field(..., description="ВП после ВБ, %")
    total_deductions: float = Field(..., description="Сумма удержаний")
    deductions: list[FinReportDeduction] = Field(..., description="Все удержания")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "date_to": "2025-07-18",
                    "wb_commission": 16554462.84,
                    "wb_commission_percentage": 29.48,
                    "to_be_transferred": 61360434.8,
                    "logistics": 2606288.52,
                    "total_to_be_paid": 48500574.79,
                    "revenue": 77914897.64,
                    "discounted_retail_price": 78434795.7,
                    "penalty": 62695.05,
                    "storage_fee": 66754.73,
                    "paid_acceptance": 30015,
                    "credit_transfers": 3013441.44,
                    "to_client_upon_cancellation": 344240.59,
                    "from_client_upon_cancellation": 86100,
                    "from_client_upon_return": 1200,
                    "to_client_upon_sale": 2040633.92,
                    "purchase_price_of_sales": 37563404,
                    "purchase_price_of_returns": 128066,
                    "purchase_cost": 37435338,
                    "our_share_before_cost": 67.99,
                    "vp_after_wb": 10548583.47,
                    "vp_after_wb_percentage": 18.07,
                    "total_deductions": 10160861.44,
                    "deductions": [
                        {
                            "grouped_bonus_type_name": "Оказание услуг «ВБ.Продвижение»",
                            "total_deduction": 1111391
                        },
                        {
                            "grouped_bonus_type_name": "Перевод на баланс заёмщика",
                            "total_deduction": 3312184.55
                        },
                    ]
                },
            ]
        }
    )


class PenaltyDetailsResponse(BaseModel):
    """Модель штрафа из таблицы penalties_mv."""

    sale_dt: Optional[date] = Field(..., description="Дата продажи")
    order_date: Optional[date] = Field(..., description="Дата заказа покупателем")

    nm_id: Optional[int] = Field(..., description="Код номенклатуры")
    penalty: Optional[float] = Field(..., description="Сумма штрафа")
    count_items: Optional[int] = Field(..., description="Количество")
    bonus_type_name: Optional[str] = Field(..., description="Виды логистики, штрафов и корректировок ВВ")
    subject_name: Optional[str] = Field(..., description="Предмет")
    account: Optional[str] = field_configs["account"]
    srid: Optional[str] = Field(..., description="Srid")
    warehouse_type: Optional[str] = Field(..., description="Тип склада")
    local_vendor_code: Optional[str] = field_configs["local_vendor_code"]
    shk_id: Optional[int] = Field(..., description="ШК")

    supplier_status: Optional[str] = Field(..., description="Статус поставщика")
    supply_id: Optional[str] = Field(..., description="Номер поставки")
    internal_status: Optional[str] = Field(None, description="Внутренний статус заказа")
    internal_status_setting_date: Optional[datetime] = Field(None, description="Дата установки внутреннего статуса")
    wb_status: Optional[str] = Field(..., description="Статус WB")
    wb_status_setting_date: Optional[datetime] = Field(None, description="Дата установки статуса WB")
    converted_price: Optional[float] = Field(None, description="Цена товара на момент сборки")
    penalty_rate: Optional[float] = Field(None, description="Процент штрафа от цены товара")
    assembly_id: Optional[int] = Field(..., description="Номер сборочного задания")
    assembly_start_date: Optional[datetime] = Field(None, description="Начало сборки заказа")
    assembly_end_date: Optional[datetime] = Field(None, description="Окончание сборки заказа")
    transferred_to_delivery_at: Optional[datetime] = Field(None, description="Дата передачи товара в доставку")

    loss_owner: Optional[int] = Field(1, description="Владелец потерь")
    comment: Optional[str] = Field(None, description="Комментарий к штрафу")

    # TODO: если накапливаются эти данные, добавить получение значений
    operator_name: Optional[str] = Field(None, description="ФИО оператора")
    assembler_name: Optional[str] = Field(None, description="ФИО сборщика")


class DaylyPenaltiesReport(BaseModel):
    """Модель отчета по штрафам за день."""

    penalties_date: date = Field(..., description="Дата штрафов")
    penalties: list[PenaltyDetailsResponse] = Field([], description="Все штрафы за день")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                  {
                    "penalties_date": "2025-08-01",
                    "penalties": [
                        {
                            "sale_dt": "2025-08-01",
                            "order_date": "2025-07-18",
                            "nm_id": 123456789,
                            "penalty": 138.41,
                            "count_items": 1,
                            "bonus_type_name": "Выявленные расхождения в карточке товара после приемки на складе WB",
                            "subject_name": "Помпы для воды",
                            "account": "Вектор",
                            "srid": "8054745045712921857.0.0",
                            "warehouse_type": "Склад WB",
                            "local_vendor_code": "wild1234",
                            "shk_id": 37450221111,
                            "supplier_status": "complete",
                            "supply_id": "WB-GI-180719950",
                            "internal_status": "DELIVERED",
                            "internal_status_setting_date": "2025-08-01T12:26:38.804285",
                            "wb_status": "waiting",
                            "wb_status_setting_date": "2025-10-15T12:26:38.804285",
                            "converted_price": 1277,
                            "penalty_rate": 29.18,
                            "assembly_id": 0,
                            "assembly_start_date": "2025-08-01T12:26:38.804285",
                            "assembly_end_date": "2025-08-01T12:26:38.804285",
                            "transferred_to_delivery_at": "2025-08-01T12:26:38.804285",
                            "loss_owner": 6,
                            "comment": "согласованный пересорт в виду отсутствия товара",
                            "operator_name": "Александров",
                            "assembler_name": "Сергеев"
                        },
                    ]
                },
            ]
        }
    )


class MonthlyCategorySales(BaseModel):
    """Модель ответа для результатов продаж по категориям за каждый месяц."""

    month_num: int = Field(..., description="Месяц")
    subject_name: Optional[str] = Field(..., description="Категория")
    total_revenue: Optional[float] = Field(..., description="Сумма заказов")
    total_orders_count: Optional[int] = Field(..., description="Количество заказов")
    total_sales_sum: Optional[float] = Field(..., description="Сумма продаж")
    average_receipt: Optional[float] = Field(..., description="Средний чек")
    net_profit_from_orders: Optional[float] = Field(..., description="Чистая прибыль от заказов")
    margin: Optional[float] = Field(..., description="Маржа")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "month_num": 1,
                    "subject_name": "Влажные салфетки",
                    "total_revenue": 361888,
                    "total_orders_count": 1186,
                    "total_sales_sum": 445879,
                    "average_receipt": 304.85,
                    "net_profit_from_orders": 50000,
                    "margin": 0.131
                },
            ]
        }
    )


class PenaltyIdentifier(BaseModel):
    """Идентификатор штрафа."""

    penalty_date: date = Field(..., description="Дата штрафа")
    nm_id: int = Field(..., description="Код номенклатуры")
    bonus_type_name: str = Field(..., description="Виды логистики, штрафов и корректировок ВВ")
    srid: str = Field(..., description="Srid", max_length=255)


class PenaltyAnnotationUpdate(BaseModel):
    """Модель для обновления аннотаций к штрафу."""

    penalty: PenaltyIdentifier
    loss_owner: LossOwnerEnum = Field(
        1,
        description="Владелец потерь: Склад (по умолчанию), Офис, Поставщик, ВБ или Прочее"
    )
    comment: Optional[str] = Field(None, description="Комментарий к штрафу")

    @field_validator("loss_owner", mode="before")
    @classmethod
    def validate_loss_owner(cls, v):
        if isinstance(v, int):
            return LossOwnerEnum.from_id(v)

        if isinstance(v, str):
            try:
                return LossOwnerEnum.from_id(int(v))
            except ValueError:
                pass

        if isinstance(v, LossOwnerEnum):
            return v

        raise ValueError(
            "loss_owner должен быть целочисленным (1–7). "
            "Например: 1 для 'Склад', 2 для 'Офис', и т.д."
        )

    @field_validator("comment", mode="before")
    @classmethod
    def validate_comment(cls, v):
        if isinstance(v, str):
            return v.strip() or None

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "penalty": {
                        "penalty_date": "2025-08-01",
                        "nm_id": 111222333,
                        "bonus_type_name": "Штраф МП. Невыполненный заказ ",
                        "srid": "22021130613098888.0.0"
                    },
                    "loss_owner": 1,
                    "comment": "Недостача при приёмке"
                },
            ]
        },
    )
