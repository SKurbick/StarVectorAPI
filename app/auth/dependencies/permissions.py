from typing import Annotated, ClassVar

from fastapi import Depends

from app.exceptions import AccessForbiddenError

from ..enums import StarVectorApiPermissions
from ..models import AuthenticatedUserModel

from .context import get_user_context, UserRequestContext


class AuthenticatedUser(AuthenticatedUserModel):
    """
    Аутентифицированный пользователь.
    """

    def __init__(self, user_context: Annotated[UserRequestContext, Depends(get_user_context)]):
        super().__init__(user_context)


class _BasePermissionChecker(AuthenticatedUserModel):
    """
    Проверить, что авторизованный пользователь обладает одним из необходимых разрешений.
    """

    REQUIRED_PERMISSIONS: ClassVar[frozenset[StarVectorApiPermissions]] = frozenset()

    def __init__(self, user_context: Annotated[UserRequestContext, Depends(get_user_context)]):
        super().__init__(user_context)
        self._require_permission()

    def _require_permission(self) -> None:
        if self.is_superuser:
            return
        if any(self._has_permission(permission) for permission in self.REQUIRED_PERMISSIONS):
            return
        raise AccessForbiddenError()

    def _has_permission(self, permission: str) -> bool:
        domain, separator, _ = permission.partition(".")
        return permission in self.permissions or (bool(separator) and f"{domain}.admin" in self.permissions)


class Admin(_BasePermissionChecker):
    """
    Администратор приложения.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.ADMIN})


class WBAnalyticsWHDTViewer(Admin):
    """
    Просмотр времени исполнения поставок WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_ANALYTICS_WAREHOUSE_DELIVERY_TIME_VIEW})


class WBCardsViewer(Admin):
    """
    Просмотр карточек товаров WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_CARDS_VIEW})


class WBCompetitorsPricesViewer(Admin):
    """
    Просмотр цен конкурентов WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_COMPETITORS_PRICES_VIEW})


class WBFinanceReportsWeeklyViewer(Admin):
    """
    Просмотр агрегированных недельных финансовых отчетов WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_FINANCE_REPORTS_WEEKLY_VIEW})


class WBFinanceICNetProfitViewer(Admin):
    """
    Просмотр чистой прибыли по индивидуальным условиям WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_FINANCE_INDIVIDUAL_CONDITIONS_NET_PROFIT_VIEW})


class WBFinanceNetProfitViewer(WBFinanceICNetProfitViewer):
    """
    Просмотр чистой прибыли WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_FINANCE_NET_PROFIT_VIEW})


class WBOrderHistoryViewer(Admin):
    """
    Просмотр истории заказов WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_ORDERS_HISTORY_VIEW})


class WBOrderRevenuesViewer(Admin):
    """
    Просмотр выручки заказов WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_ORDERS_REVENUES_VIEW})


class WBPenaltiesAnnotationsEditor(Admin):
    """
    Изменение аннотаций к штрафам WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_PENALTIES_ANNOTATIONS_EDIT})


class WBPenaltiesViewer(WBPenaltiesAnnotationsEditor):
    """
    Просмотр штрафов WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_PENALTIES_VIEW})


class WBTaxesPercentEditor(Admin):
    """
    Изменение налоговой ставки товаров WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_TAXES_PERCENT_EDIT})


class ProductsNotesEditor(Admin):
    """
    Изменение внутренних заметок к товарам.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.PRODUCTS_NOTES_EDIT})


class WBAnaliticsSalesRevenueViewer(Admin):
    """
    Просмотр выручки WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_ANALYTICS_SALES_REVENUE_VIEW})


class WBAnaliticsSalesICViewer(Admin):
    """
    Просмотр показателей индивидуальных условий WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_ANALYTICS_SALES_INDIVIDUAL_CONDITIONS_VIEW})


class WBAnaliticsSalesManagersViewer(Admin):
    """
    Просмотр выручки и прибыли Wildberries по менеджерам.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_ANALYTICS_SALES_MANAGERS_VIEW})


class WBAnaliticsSalesCategoryViewer(Admin):
    """
    Просмотр статистики продаж категорий WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_ANALYTICS_SALES_CATEGORY_VIEW})


class WBAnaliticsPromotionsViewer(Admin):
    """
    Просмотр статистики акций WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_ANALYTICS_PROMOTIONS_VIEW})


class WBStocksQuantityEditor(Admin):
    """
    Изменение виртуальных остатков WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_STOCKS_QUANTITY_EDIT})


class WBStocksQuantityViewer(WBStocksQuantityEditor):
    """
    Просмотр виртуальных остатков WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_STOCKS_QUANTITY_VIEW})


class WBTurnoverFederalDistrictViewer(Admin):
    """
    Просмотр оборачиваемости WB по федеральным округам.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_TURNOVER_FEDERAL_DISTRICT_VIEW})


class WBUnitEconomicsViewer(Admin):
    """
    Просмотр показателей юнит-экономики WB.
    """

    REQUIRED_PERMISSIONS = frozenset({StarVectorApiPermissions.WB_UNIT_ECONOMICS_VIEW})
