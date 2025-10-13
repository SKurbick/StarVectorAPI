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
    start_month: Optional[int] = Query(
        None,
        example=8,
        ge=1,
        le=12,
        description="Первый месяц периода",
    ),
    start_year: Optional[int] = Query(
        default_factory=lambda: date.today().year,
        example=2025,
        ge=2000,
        le=2100,
        description="Год на начало периода",
    ),
    end_month: Optional[int] = Query(
        None,
        example=9,
        ge=1,
        le=12,
        description="Год на конец периода",
    ),
    end_year: Optional[int] = Query(
        default_factory=lambda: date.today().year,
        example=2025,
        ge=2000,
        le=2100,
        description="Год в формате ГГГГ",
    )
) -> tuple[date, date]:
    try:
        if start_month:
            start_date = date(start_year, start_month, 1)
        else:
            start_date = date(start_year, 1, 1)

        if end_month:
            end_date = date(end_year, end_month, 1)
        elif end_year:
            end_date = date(end_year, 12, 1)

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        return start_date, end_date
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Неверный формат даты."
        )
