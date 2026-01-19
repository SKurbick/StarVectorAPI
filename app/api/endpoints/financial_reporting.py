from fastapi import APIRouter, Depends, status, Query

from app.dependencies.financial_reporting import get_financial_reporting_service
from app.domain.models import ItemizationOfExpenses
from app.domain.enums import FinancialReportingEnum
from app.service.financial_reporting import FinancialReportingService

router = APIRouter(tags=["Financial Reporting"])

@router.get("/items_of_expenses", response_model=list[ItemizationOfExpenses], status_code=status.HTTP_200_OK)
async def get_items_of_expenses(
        service: FinancialReportingService = Depends(get_financial_reporting_service),
        period: FinancialReportingEnum = Query(..., description="Период агрегации отчётности")
) -> list[ItemizationOfExpenses]:
    return await service.get_items_of_expenses(period)