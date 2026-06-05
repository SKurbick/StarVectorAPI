from pydantic import Field, ConfigDict, model_validator

from .mixins import (
    ReportMetaMixin,
    ProductCatalogMixin,
    TransactionIdentifiersMixin,
    PricingAndDiscountsMixin,
    FinancialSettlementsMixin,
    LogisticsAndOperationsMixin,
    PartnerAndLegalMixin,
)


class SalesReportRow(
    ReportMetaMixin,
    ProductCatalogMixin,
    TransactionIdentifiersMixin,
    PricingAndDiscountsMixin,
    FinancialSettlementsMixin,
    LogisticsAndOperationsMixin,
    PartnerAndLegalMixin,
):
    """
    Модель данных строки финансового отчёта о продажах по реализации товара.
    """

    rrd_id: int = Field(validation_alias="rrdId", description="ID строки")
    account: str = Field(..., description="ЛК отчета")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def validate_str(cls, data: dict):
        if isinstance(data, dict):
            return {
                key: (None if value == "" else value)
                for key, value in data.items()
            }

        return data
