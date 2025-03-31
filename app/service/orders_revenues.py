import datetime
from typing import List, Dict

from app.repository import OrdersRevenuesRepository
from app.domain.models import OrdersRevenues, PeriodRequestModel, OrdersRevenuesResponseModel, WeeklyOrdersResponse


class OrdersRevenuesService:
    def __init__(self, orders_revenues_repository: OrdersRevenuesRepository):
        self.orders_revenues_repository = orders_revenues_repository

    async def get_data_by_period(self, period: PeriodRequestModel) -> List[OrdersRevenuesResponseModel]:
        return await self.orders_revenues_repository.get_data_by_period(period)

    async def get_last_week_data(self, number_of_last_weeks) -> WeeklyOrdersResponse:
        result_data = {}
        week_result_dates = self.get_last_weeks_dates(number_of_last_weeks)
        print(week_result_dates)
        for week, dates in week_result_dates.items():
            period_start = dates['Start']
            period_end = dates['End']
            one_week_data = await self.orders_revenues_repository.get_last_week_data(period_start, period_end)
            for row in one_week_data:
                article_id = int(row['article_id'])
                result_data.setdefault(article_id, {})[week] = row['total_orders_sum_rub']

        return WeeklyOrdersResponse(result_data)

    @staticmethod
    # def get_last_weeks_dates(num_weeks: int) -> Dict[str, dict]:
    #     weeks = {}
    #     today = datetime.datetime.today()
    #
    #     for i in range(num_weeks):
    #         # Вычисляем конец недели (воскресенье)
    #         end_date = today - datetime.timedelta(days=(today.weekday() + 1) % 7 + 7 * i)
    #         start_date = end_date - datetime.timedelta(days=6)
    #
    #         # Форматируем ключ вида "03.24-03.30"
    #         week_key = (
    #             f"{start_date.strftime('%m.%d')}-"
    #             f"{end_date.strftime('%m.%d')}"
    #         )
    #
    #         weeks[week_key] = {
    #             'Start': start_date.date(),
    #             'End': end_date.date()
    #         }
    #
    #     return weeks
    def get_last_weeks_dates(last_week_count=1):
        last_week_count -= 1
        """Функция для получения срезов дат начало и конца недели не включая текущую.
         last_week_count: количество недель (указывая 1 - получишь последнюю)"""
        now = datetime.datetime.now()
        current_week_start = now - datetime.timedelta(days=now.weekday())

        result_dates = {}
        for i in range(0, last_week_count + 1):
            week_start = current_week_start - datetime.timedelta(weeks=i)
            week_end = week_start + datetime.timedelta(days=6)

            week_start = week_start.date()
            week_end = week_end.date()

            date_key = f"{week_start.strftime('%m.%d')}-{week_end.strftime('%m.%d')}"
            result_dates[date_key] = {"Start": week_start,
                                      "End": week_end}

        return result_dates
