"""
Преобразование claims токена в разрешения сервиса.
"""

from collections.abc import Mapping

from .enums import LegacyPermissions, StarVectorApiPermissions
from .models import AccessTokenPayload

DOMAIN_PERMISSIONS = frozenset(str(permission) for permission in StarVectorApiPermissions)

LEGACY_PERMISSIONS_MAP: Mapping[LegacyPermissions, frozenset[StarVectorApiPermissions]] = {
    LegacyPermissions.VIEWING: frozenset(
        {
            StarVectorApiPermissions.WB_CARDS_VIEW,
            StarVectorApiPermissions.WB_ANALYTICS_SALES_CATEGORY_VIEW,
            StarVectorApiPermissions.WB_FINANCE_NET_PROFIT_VIEW,
            StarVectorApiPermissions.WB_TAXES_PERCENT_EDIT,
            StarVectorApiPermissions.PRODUCTS_NOTES_EDIT,
            StarVectorApiPermissions.WB_PENALTIES_VIEW,
            StarVectorApiPermissions.WB_PENALTIES_ANNOTATIONS_EDIT,
        }
    ),
    LegacyPermissions.CRM_VIEWING_UNIT_ECONOMICS: frozenset(
        {
            StarVectorApiPermissions.WB_UNIT_ECONOMICS_VIEW,
            StarVectorApiPermissions.WB_TURNOVER_FEDERAL_DISTRICT_VIEW,
            StarVectorApiPermissions.WB_ORDERS_REVENUES_VIEW,
            StarVectorApiPermissions.WB_STOCKS_QUANTITY_VIEW,
            StarVectorApiPermissions.WB_CARDS_VIEW,
            StarVectorApiPermissions.WB_FINANCE_INDIVIDUAL_CONDITIONS_NET_PROFIT_VIEW,
            StarVectorApiPermissions.WB_FINANCE_REPORTS_WEEKLY_VIEW,
            StarVectorApiPermissions.WB_COMPETITORS_PRICES_VIEW,
            StarVectorApiPermissions.WB_ORDERS_HISTORY_VIEW,
            StarVectorApiPermissions.WB_ANALYTICS_PROMOTIONS_VIEW,
        }
    ),
    LegacyPermissions.CRM_VIEWING_CRM_ANALYTIC: frozenset(
        {
            StarVectorApiPermissions.WB_ANALYTICS_WAREHOUSE_DELIVERY_TIME_VIEW,
            StarVectorApiPermissions.WB_ANALYTICS_SALES_REVENUE_VIEW,
            StarVectorApiPermissions.WB_ANALYTICS_SALES_INDIVIDUAL_CONDITIONS_VIEW,
            StarVectorApiPermissions.WB_ANALYTICS_SALES_CATEGORY_VIEW,
            StarVectorApiPermissions.WB_ANALYTICS_SALES_MANAGERS_VIEW,
            StarVectorApiPermissions.WB_ANALYTICS_PROMOTIONS_VIEW,
        }
    ),
    LegacyPermissions.CRM_POSSIBILITY_TO_STORE_LEFTOVERS: frozenset(
        {StarVectorApiPermissions.WB_STOCKS_QUANTITY_EDIT}
    ),
    LegacyPermissions.ABILITY_TO_UPLOAD_EXCEL_FILE_TO_FINES: frozenset(
        {StarVectorApiPermissions.WB_PENALTIES_ANNOTATIONS_EDIT}
    ),
}


def resolve_permissions(access_token: AccessTokenPayload) -> frozenset[str]:
    """
    Получить разрешения домена из нового и прежнего токенов.
    """
    permissions = DOMAIN_PERMISSIONS & access_token.permissions
    legacy_permissions = access_token.model_extra or {}

    for legacy_permission, mapped_permissions in LEGACY_PERMISSIONS_MAP.items():
        if legacy_permissions.get(legacy_permission.value) is True:
            permissions |= {str(permission) for permission in mapped_permissions}

    return frozenset(permissions)
