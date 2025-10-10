from datetime import date

from fastapi import Query

from app.domain.models import PeriodRequestModel


date_from_description = "Начало периода."
date_to_description = "Окончание периода."


def get_period_filter(
    date_from: date = Query("2000-01-01", example="2025-06-18", description=date_from_description),
    date_to: date = Query(..., default_factory=date.today, example="2025-07-18", description=date_to_description),
):
    return PeriodRequestModel(
        date_from=date_from,
        date_to=date_to,
    )
