from datetime import date
from typing import Optional

from fastapi import Query, HTTPException

from app.domain.models import PeriodRequestModel


date_from_description = "Начало периода."
date_to_description = "Окончание периода."


def get_dates_period_filter(
    date_from: date = Query("2000-01-01", example="2025-06-18", description=date_from_description),
    date_to: date = Query(..., default_factory=date.today, example="2025-07-18", description=date_to_description),
):
    return PeriodRequestModel(
        date_from=date_from,
        date_to=date_to,
    )


def get_months_filter(
    month: Optional[str] = Query(
        None,
        regex=r'^\d{4}-\d{2}$',
        description="Конкретный месяц в формате ГГГГ-ММ (например, 2025-01)"
    ),
    start_month: Optional[str] = Query(
        None, 
        regex=r'^\d{4}-\d{2}$',
        description="Начало периода в формате ГГГГ-ММ"
    ),
    end_month: Optional[str] = Query(
        None,
        regex=r'^\d{4}-\d{2}$', 
        description="Конец периода в формате ГГГГ-ММ"
    ),
):
    if month and (start_month or end_month):
        raise HTTPException(
            status_code=400,
            detail="Используйте либо параметр 'month', либо 'start_month/end_month', но не вместе"
        )
    
    if month:
        start_month = end_month = month

    return start_month, end_month
