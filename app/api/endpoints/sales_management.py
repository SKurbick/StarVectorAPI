import datetime
from typing import Optional
from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from app.auth import (
    WBAnaliticsSalesRevenueViewer,
    WBAnaliticsSalesICViewer,
    WBAnaliticsSalesManagersViewer,
    WBAnaliticsSalesCategoryViewer,
    WBAnaliticsPromotionsViewer,
)
from fastapi.params import Depends

from app.dependencies import get_sales_management_service
from app.service.sales_management import SalesManagementService
from app.domain.models import (
    SalesManagementBaseSummWithDate,
    SalesManagementShares,
    SalesManagementSharesGood,
    SalesManagementSharesGoodWithMargin
)

router = APIRouter(prefix="/sales-management", tags=["Управление продажами"])


@router.get("/sales/revenue/{date}", response_model=list[SalesManagementBaseSummWithDate], description="""
    **Получить выручку по категориям за конкретный день**\n
    date: format date, example: 2025-12-18,
    good_category: Optinal row, example 'Казаны' 
""")
async def get_revenue_by_date(
        date: datetime.date,
        good_category: Optional[str] = None,
        _: WBAnaliticsSalesRevenueViewer = Depends(),
        service: SalesManagementService = Depends(get_sales_management_service)
):
    return await service.get_sum_sales_category_by_date(date, good_category)


@router.get("/sales/revenue", description="""
    **Получить выручку по категориям за период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18
    good_category: Optinal row, example 'Казаны' 
""")
async def get_revenue_by_period(
        date_start: datetime.date,
        date_end: datetime.date,
        good_category: Optional[str] = None,
        _: WBAnaliticsSalesRevenueViewer = Depends(),
        service: SalesManagementService = Depends(get_sales_management_service)
):
    if date_start < date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="reverse date")
    result = await service.get_sum_revenue_category_by_period_with_managers(
        start_date=date_start,
        end_date=date_end,
        good_category=good_category
    )
    return result


@router.get("/sales/ic", description="""
    **Получить данные по ИУ за период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18
    good_category: Optinal row, example 'Казаны' 
""")
async def get_individual_condition_by_period(
        date_start: datetime.date,
        date_end: datetime.date,
        good_category: Optional[str] = None,
        _: WBAnaliticsSalesICViewer = Depends(),
        service: SalesManagementService = Depends(get_sales_management_service)
):
    if date_start < date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="reverse date")
    result = await service.get_sums_individual_conditions_by_period_with_category(
        start_date=date_start,
        end_date=date_end,
        good_category=good_category
    )
    return result


@router.get("/sales/browsing", description="""    
    **Получить данные по статистики просмторов\кликов категорий за период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18
    good_category: Optinal row, example 'Казаны' 
""")
async def get_browsing_by_period(
        date_start: datetime.date,
        date_end: datetime.date,
        good_category: Optional[str] = None,
        _: WBAnaliticsSalesCategoryViewer = Depends(),
        service: SalesManagementService = Depends(get_sales_management_service)
):
    if date_start < date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="reverse date")
    result = await service.get_browsing_info_by_category_and_period(
        start_date=date_start,
        end_date=date_end,
        good_category=good_category
    )
    return result


@router.get("/sales/outlay", description="""
    **Получить данные по раходам категорий за период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18
    good_category: Optinal row, example 'Казаны' 
""")
async def get_outlay_by_period(
        date_start: datetime.date,
        date_end: datetime.date,
        good_category: Optional[str] = None,
        _: WBAnaliticsSalesCategoryViewer = Depends(),
        service: SalesManagementService = Depends(get_sales_management_service)
):
    if date_start < date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="reverse date")
    result = await service.get_outlay_info_by_category_and_period(
        start_date=date_start,
        end_date=date_end,
        good_category=good_category
    )
    return result


@router.get("/sales/penalty", description="""
    **Получить данные по штрафам категорий за период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18
    good_category: Optinal row, example 'Казаны'
""")
async def get_penalty_by_period(
        date_start: datetime.date,
        date_end: datetime.date,
        good_category: Optional[str] = None,
        _: WBAnaliticsSalesCategoryViewer = Depends(),
        service: SalesManagementService = Depends(get_sales_management_service)
):
    if date_start < date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="reverse date")
    result = await service.get_penalty_info_by_category_and_period(
        start_date=date_start,
        end_date=date_end,
        good_category=good_category
    )
    return result


@router.get("/sales/managers", description="""
    **Получить выручку и прибыль по каждому менеджеру за период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18
""")
async def get_managers_statistic_by_period(
        date_start: datetime.date,
        date_end: datetime.date,
        _: WBAnaliticsSalesManagersViewer = Depends(),
        service: SalesManagementService = Depends(get_sales_management_service)
):
    if date_start < date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="reverse date")
    result = await service.get_revenue_and_ic_by_manager_and_period(
        start_date=date_start,
        end_date=date_end,
    )
    return result


@router.get("/sales/promotions/static", response_model=list[SalesManagementShares], description="""
**Получить информацию по акциям у аккаунтов с процентным соотношением total/shares**\n
""")
async def get_promotions_statistic(
        _: WBAnaliticsPromotionsViewer = Depends(),
        service: SalesManagementService = Depends(get_sales_management_service)
):
    result = await service.get_shares_total_items_by_accounts()
    return result


@router.get("/sales/promotions/goods", response_model=list[SalesManagementSharesGood], description="""
**Получить товары участвующие\неучавствующие в акциях**\n""")
async def get_promotions_goods(
        is_promotion: bool,
        _: WBAnaliticsPromotionsViewer = Depends(),
        service: SalesManagementService = Depends(get_sales_management_service)
):
    result = await service.get_shares_goods_with_bool(is_promotion)
    return result


@router.get("/sales/promotions/best-marginality", response_model=list[SalesManagementSharesGoodWithMargin],
            description="""
**Получить товар с информацией по маржинальности текущей 
и плановой (при участии в акции), если имеется подходящая акция для участия.**\n
""")
async def get_best_marginality(
        _: WBAnaliticsPromotionsViewer = Depends(),
        service: SalesManagementService = Depends(get_sales_management_service)
):
    result = await service.get_best_marginality_by_good_id()
    return result
