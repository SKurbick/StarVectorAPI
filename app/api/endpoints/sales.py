from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from starlette import status

from app.dependencies import get_sale_service, get_months_filter, get_info_from_token
from app.domain.models import MonthlyCategorySales, UserPermissions
from app.service.sales import SaleService


router = APIRouter(prefix="/sales", tags=["Продажи"])


@router.get("/categories_sales_per_month", status_code=status.HTTP_200_OK,
            description="Результаты продаж по месяцам и категориям")
async def get_categories_sales_per_month(
    period: tuple[date, date] = Depends(get_months_filter),
    category: Optional[str] = Query(None, description="Категория для фильтрации"),
    user: UserPermissions = Depends(get_info_from_token),
    service: SaleService = Depends(get_sale_service),
    ) -> list[MonthlyCategorySales]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_categories_sales_per_month(*period, category)
