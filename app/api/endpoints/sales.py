from typing import Optional

from fastapi import APIRouter, Depends, status, Query

from app.dependencies import get_sale_service, get_months_filter
from app.domain.models import MonthlyCategorySales
from app.service.sales import SaleService


router = APIRouter(prefix="/sales", tags=["Продажи"])


@router.get("/categories_sales_per_month", status_code=status.HTTP_200_OK,
            description="Результаты продаж по месяцам и категориям")
async def get_categories_sales_per_month(
    period: tuple[str] = Depends(get_months_filter),
    category: Optional[str] = Query(None, description="Категория для фильтрации"),
    service: SaleService = Depends(get_sale_service),
    ) -> list[MonthlyCategorySales]:
    return await service.get_categories_sales_per_month(*period, category)
