from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ReportMetaMixin(BaseModel):
    """
    Период формирования отчёта, валюта, тип отчёта и страна.
    """

    realizationreport_id: int = Field(validation_alias="reportId", description="ID отчёта")
    date_from: date = Field(validation_alias="dateFrom", description="Дата начала отчётного периода")
    date_to: date = Field(validation_alias="dateTo", description="Дата конца отчётного периода")
    create_dt: date = Field(validation_alias="createDate", description="Дата формирования отчёта")
    currency_name: str = Field(validation_alias="currency", description="Валюта отчёта")
    report_type: int = Field(validation_alias="reportType", description="Тип отчёта: 1 — основной, 2 — по выкупам, 3 — по выкупам для Грузии")
    site_country: str | None = Field(default=None, validation_alias="country", description="Страна продажи")


class ProductCatalogMixin(BaseModel):
    """
    Характеристики товара, артикулы, размеры, маркировка и подмены.
    """

    subject_name: str | None = Field(default=None, validation_alias="subjectName", description="Предмет")
    nm_id: int = Field(validation_alias="nmId", description="Артикул WB")
    title: str | None = Field(default=None, description="Название товара")
    brand_name: str | None = Field(default=None, validation_alias="brandName", description="Бренд")
    sa_name: str | None = Field(default=None, validation_alias="vendorCode", description="Артикул продавца")
    ts_name: str | None = Field(default=None, validation_alias="techSize", description="Размер")
    barcode: str | None = Field(validation_alias="sku", description="Баркод")
    kiz: str | None = Field(default=None, description="Код маркировки Честного знака")
    gi_box_type_name: str | None = Field(default=None, validation_alias="giBoxTypeName", description="Тип коробов")
    article_substitution: str | None = Field(default=None, validation_alias="articleSubstitution", description="ID подменного артикула")
    delivery_method: str | None = Field(default=None, validation_alias="deliveryMethod", description="Способ продажи и тип товара")


class TransactionIdentifiersMixin(BaseModel):
    """
    Уникальные ключи заказов, поставок и временные метки операций.
    """

    gi_id: int = Field(validation_alias="giId", description="ID поставки")
    order_dt: datetime = Field(validation_alias="orderDt", description="Дата и время заказа")
    sale_dt: datetime = Field(validation_alias="saleDt", description="Дата и время продажи")
    rr_dt: date = Field(validation_alias="rrDate", description="Дата операции")
    shk_id: int = Field(validation_alias="shkId", description="Штрихкод")
    assembly_id: int = Field(validation_alias="orderId", description="ID сборочного задания")
    srid: str | None = Field(default=None, description="ID заказа")
    order_uid: str | None = Field(default=None, validation_alias="orderUid", description="ID корзины заказа - транзакции")
    trbx_id: str | None = Field(default=None, validation_alias="trbxId", description="ID короба для обработки товара")
    doc_type_name: str | None = Field(default=None, validation_alias="docTypeName", description="Тип документа")
    supplier_oper_name: str = Field(validation_alias="sellerOperName", description="Обоснование для оплаты")


class PricingAndDiscountsMixin(BaseModel):
    """
    Розничные цены, продуктовые скидки, промокоды, лояльность и кэшбэк.
    """

    retail_price: Decimal = Field(validation_alias="retailPrice", description="Цена розничная")
    retail_amount: Decimal = Field(validation_alias="retailAmount", description="Вайлдберриз реализовал Товар (Пр)")
    sale_percent: Decimal = Field(validation_alias="salePercent", description="Согласованный продуктовый дисконт, %") # проверить
    product_discount_for_report: Decimal = Field(validation_alias="productDiscountForReport", description="Итоговая согласованная скидка, %")
    supplier_promo: Decimal = Field(validation_alias="sellerPromo", description="Промокод, %")
    ppvz_spp_prc: Decimal = Field(validation_alias="spp", description="Платформенные скидки, %")
    retail_price_withdisc_rub: Decimal = Field(validation_alias="retailPriceWithDisc", description="Цена розничная с учётом согласованной скидки")
    installment_cofinancing_amount: Decimal = Field(validation_alias="installmentCofinancingAmount", description="Скидка по программе софинансирования")
    wibes_wb_discount_percent: Decimal = Field(validation_alias="wibesDiscountPercent", description="Скидка Wibes, %")
    cashback_amount: Decimal = Field(validation_alias="cashbackAmount", description="Сумма, удержанная за начисленные баллы программы лояльности")
    cashback_discount: Decimal = Field(validation_alias="cashbackDiscount", description="Компенсация скидки по программе лояльности")
    cashback_commission_change: Decimal = Field(validation_alias="cashbackCommissionChange", description="Стоимость участия в программе лояльности")
    sale_price_promocode_discount_prc: Decimal = Field(validation_alias="salePricePromocodeDiscountPrc", description="Скидка за промокод, %")
    sale_price_affiliated_discount_prc: Decimal = Field(validation_alias="salePriceAffiliatedDiscountPrc", description="Скидка по подменному артикулу, %")
    sale_price_wholesale_discount_prc: Decimal = Field(validation_alias="salePriceWholesaleDiscountPrc", description="Оптовая скидка для бизнеса, %")
    uuid_promocode: str | None = Field(default=None, validation_alias="uuidPromocode", description="ID промокода")
    seller_promo_id: int = Field(validation_alias="sellerPromoId", description="ID собственной акции продавца с дополнительной скидкой")
    seller_promo_discount: Decimal = Field(validation_alias="sellerPromoDiscount", description="Размер дополнительной скидки по собственной акции продавца, %")
    loyalty_id: int = Field(validation_alias="loyaltyId", description="ID скидки лояльности от продавца")
    loyalty_discount: Decimal = Field(validation_alias="loyaltyDiscount", description="Размер скидки лояльности от продавца, %")


class FinancialSettlementsMixin(BaseModel):
    """
    Комиссии ВВ, эквайринг, вознаграждения, удержания, штрафы и тарифы.
    """

    dlv_prc: Decimal = Field(validation_alias="dlvPrc", description="Фиксированный коэффициент склада по поставке")
    fix_tariff_date_from: datetime | None = Field(default=None, validation_alias="fixTariffDateFrom", description="Дата начала действия фиксации")
    fix_tariff_date_to: datetime | None = Field(default=None, validation_alias="fixTariffDateTo", description="Дата конца действия фиксации")
    commission_percent: Decimal = Field(validation_alias="commissionPercent", description="Размер кВВ, %")
    ppvz_kvw_prc_base: Decimal = Field(validation_alias="kvwBase", description="Размер кВВ без НДС, % базовый")
    ppvz_kvw_prc: Decimal = Field(validation_alias="kvw", description="Итоговый кВВ без НДС, %")
    sup_rating_prc_up: Decimal = Field(validation_alias="supRatingUp", description="Размер снижения кВВ из-за рейтинга, %")
    is_kgvp_v2: Decimal = Field(validation_alias="isKgvpV2", description="Размер снижения кВВ из-за акции, %") # проверить тип
    ppvz_sales_commission: Decimal = Field(validation_alias="ppvzSalesCommission", description="Вознаграждение с продаж до вычета услуг поверенного, без НДС")
    ppvz_for_pay: Decimal = Field(validation_alias="forPay", description="К перечислению продавцу за реализованный товар")
    ppvz_reward: Decimal = Field(validation_alias="ppvzReward", description="Возмещение за выдачу и возврат товаров на ПВЗ")
    acquiring_fee: Decimal = Field(validation_alias="acquiringFee", description="Компенсация платёжных услуг/Комиссия за интеграцию платёжных сервисов")
    acquiring_percent: Decimal = Field(validation_alias="acquiringPercent", description="Размер компенсации платёжных услуг/Комиссии за интеграцию платёжных сервисов, %")
    payment_processing: str | None = Field(default=None, validation_alias="paymentProcessing", description="Тип платежа: компенсация платёжных услуг/Комиссия за интеграцию платёжных сервисов")
    acquiring_bank: str | None = Field(default=None, validation_alias="acquiringBank", description="Наименование банка-эквайера")
    ppvz_vw: Decimal = Field(validation_alias="vw", description="Вознаграждение Вайлдберриз (ВВ), без НДС")
    ppvz_vw_nds: Decimal = Field(validation_alias="vwNds", description="НДС с вознаграждения Вайлдберриз")
    additional_payment: Decimal = Field(validation_alias="additionalPayment", description="Корректировка Вознаграждения Вайлдберриз (ВВ)")
    rebill_logistic_cost: Decimal = Field(validation_alias="rebillLogisticCost", description="Возмещение издержек по перевозке/по складским операциям с товаром")
    rebill_logistic_org: str | None = Field(default=None, validation_alias="rebillLogisticOrg", description="Организатор перевозки")
    storage_fee: Decimal = Field(validation_alias="paidStorage", description="Хранение")
    deduction: Decimal = Field(..., description="Удержания")
    penalty: Decimal = Field(..., description="Общая сумма штрафов")
    payment_schedule: Decimal = Field(validation_alias="paymentSchedule", description="Разовое изменение срока перечисления денежных средств")

    @field_validator("fix_tariff_date_from", "fix_tariff_date_to", mode="before")
    @classmethod
    def validate_str_datetime(cls, value):
        if not value:
            return None
        
        return value


class LogisticsAndOperationsMixin(BaseModel):
    """
    Количественные показатели, склады, ПВЗ, доставка, приёмка и бонусы.
    """

    quantity: int = Field(..., description="Количество")
    delivery_amount: int = Field(validation_alias="deliveryAmount", description="Количество доставок")
    return_amount: int = Field(validation_alias="returnAmount", description="Количество возврата")
    delivery_rub: Decimal = Field(validation_alias="deliveryService", description="Услуги по доставке товара покупателю")
    srv_dbs: bool = Field(validation_alias="srvDbs", description="Признак услуги платной доставки")
    office_name: str | None = Field(default=None, validation_alias="officeName", description="Склад")
    ppvz_office_name: str | None = Field(default=None, validation_alias="ppvzOfficeName", description="Наименование офиса доставки")
    ppvz_office_id: int = Field(validation_alias="ppvzOfficeId", description="ID офиса доставки")
    acceptance: Decimal = Field(validation_alias="paidAcceptance", description="Операции на приёмке")
    bonus_type_name: str | None = Field(default=None, validation_alias="bonusTypeName", description="Виды логистики, штрафов и корректировок ВВ")
    sticker_id: str | None = Field(default=None, validation_alias="stickerId", description="Стикер МП")


class PartnerAndLegalMixin(BaseModel):
    """
    Данные партнёра, ИНН, B2B-признак и таможенные декларации.
    """

    is_legal_entity: bool = Field(validation_alias="isB2b", description="Признак B2B-продажи")
    declaration_number: str | None = Field(default=None, validation_alias="declarationNumber", description="Номер таможенной декларации")
    ppvz_supplier_name: str | None = Field(default=None, validation_alias="ppvzSupplierName", description="Партнёр")
    ppvz_inn: str | None = Field(validation_alias="ppvzSupplierInn", description="ИНН партнёра")
