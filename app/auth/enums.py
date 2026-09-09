"""
Перечисления разрешений StarVectorAPI.
"""

from enum import StrEnum

DOMAIN_NAME = "star_vector_api"


class StarVectorApiPermissions(StrEnum):
    """
    Разрешения домена star_vector_api.
    """

    ADMIN = f"{DOMAIN_NAME}.admin"

    WB_UNIT_ECONOMICS_VIEW = f"{DOMAIN_NAME}.wb.unit_economics.view"
    WB_TURNOVER_FEDERAL_DISTRICT_VIEW = (
        f"{DOMAIN_NAME}.wb.turnover.federal_district.view"
    )
    WB_ORDERS_REVENUES_VIEW = f"{DOMAIN_NAME}.wb.orders_revenues.view"
    WB_STOCKS_QUANTITY_VIEW = f"{DOMAIN_NAME}.wb.stocks.quantity.view"
    WB_STOCKS_QUANTITY_EDIT = f"{DOMAIN_NAME}.wb.stocks.quantity.edit"
    WB_CARDS_VIEW = f"{DOMAIN_NAME}.wb.cards.view"
    WB_FINANCE_INDIVIDUAL_CONDITIONS_NET_PROFIT_VIEW = (
        f"{DOMAIN_NAME}.wb.finance.individual_conditions.net_profit.view"
    )
    WB_FINANCE_NET_PROFIT_VIEW = f"{DOMAIN_NAME}.wb.finance.net_profit.view"
    WB_FINANCE_REPORTS_WEEKLY_VIEW = f"{DOMAIN_NAME}.wb.finance.reports.weekly.view"
    WB_TAXES_PERCENT_EDIT = f"{DOMAIN_NAME}.wb.taxes.percent.edit"
    WB_COMPETITORS_PRICES_VIEW = f"{DOMAIN_NAME}.wb.competitors.prices.view"
    WB_ORDERS_HISTORY_VIEW = f"{DOMAIN_NAME}.wb.orders.history.view"
    WB_ANALYTICS_WAREHOUSE_DELIVERY_TIME_VIEW = (
        f"{DOMAIN_NAME}.wb.analytics.warehouse_delivery_time.view"
    )
    WB_ANALYTICS_SALES_REVENUE_VIEW = (
        f"{DOMAIN_NAME}.wb.analytics.sales.revenue.view"
    )
    WB_ANALYTICS_SALES_INDIVIDUAL_CONDITIONS_VIEW = (
        f"{DOMAIN_NAME}.wb.analytics.sales.individual_conditions.view"
    )
    WB_ANALYTICS_SALES_CATEGORY_VIEW = (
        f"{DOMAIN_NAME}.wb.analytics.sales.category.view"
    )
    WB_ANALYTICS_SALES_MANAGERS_VIEW = f"{DOMAIN_NAME}.wb.analytics.sales.managers.view"
    WB_ANALYTICS_PROMOTIONS_VIEW = (
        f"{DOMAIN_NAME}.wb.analytics.promotions.view"
    )
    WB_PENALTIES_VIEW = f"{DOMAIN_NAME}.wb.penalties.view"
    WB_PENALTIES_ANNOTATIONS_EDIT = f"{DOMAIN_NAME}.wb.penalties.annotations.edit"
    PRODUCTS_NOTES_EDIT = f"{DOMAIN_NAME}.products.notes.edit"


class LegacyPermissions(StrEnum):
    """
    Boolean claims прежней схемы токена.
    """

    VIEWING = "viewing"
    CRM_VIEWING_UNIT_ECONOMICS = "crm_viewing_unit_economics"
    CRM_VIEWING_CRM_ANALYTIC = "crm_viewing_crm_analytic"
    CRM_POSSIBILITY_TO_STORE_LEFTOVERS = "crm_possibility_to_store_leftovers"
    CRM_ABILITY_TO_ADD_AND_REMOVE_PRODUCTS_FROM_PROMOTIONS = (
        "crm_ability_to_add_and_remove_products_from_promotions"
    )
    ABILITY_TO_UPLOAD_EXCEL_FILE_TO_FINES = "ability_to_upload_excel_file_to_fines"
