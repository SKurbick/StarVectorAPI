import datetime
from datetime import date
from typing import Optional

from app.domain.models import SalesManagementBaseSumm, SalesManagementManagerRow, SalesManagementBaseSummWithDate, \
    SalesManagementBaseSummWithSKU
from app.repository.sales_management import SalesManagementRepository


class SalesManagementService:
    def __init__(self, repository: SalesManagementRepository):
        self.repository = repository

    async def get_sum_sales_category_by_period_with_managers(
            self,
            start_date: date,
            end_date: date,
    ):
        """Получить общие цифры продаж по категориям за определенный период, с менеджерами"""
        period = start_date - end_date
        sums_rows = await self.repository.get_sums_sales_by_category_and_period(
            date_start=start_date, date_end=end_date
        )
        manager_rows = await self.repository.get_managers_name_by_category_and_period(
            date_start=start_date, date_end=end_date
        )
        old_period_avg_sums_rows = await self.repository.get_old_sums_by_category_and_period(
            start_date=start_date - datetime.timedelta(days=period.days + 1),
            end_date=end_date - datetime.timedelta(days=period.days + 1),
        )
        valid_sums_rows = [SalesManagementBaseSummWithSKU(**r) for r in sums_rows]
        valid_manager_rows = [SalesManagementManagerRow(**r) for r in manager_rows]
        valid_old_week_avg_sums_rows = [SalesManagementBaseSumm(**r) for r in old_period_avg_sums_rows]
        valid_result = {}

        # Добавление в результирующий словарь и разбивка по секциям дат с продажами и процентным соотношением релевантных SKU
        for i in valid_sums_rows:
            if valid_result.get(i.subject_name) is None:
                valid_result[i.subject_name] = {
                    "manager": "",
                    "old_period_avg": ""
                }
            if valid_result[i.subject_name].get("dates") is None:
                valid_result[i.subject_name]["dates"] = [
                    {"date": i.date, "summ": i.summ, "sku_percentage": i.sku_percentage}]
            else:
                valid_result[i.subject_name]["dates"].append(
                    {"date": i.date, "summ": i.summ, "sku_percentage": i.sku_percentage})

        # Добавление в результирующий словарь менеджера торгующего данной категорией
        for i in valid_manager_rows:
            try:
                valid_result[i.subject_name]["manager"] = i.manager
            except KeyError:
                continue

        # Добавление в результирующий словарь среднего количества продаж за период по категории
        for i in valid_old_week_avg_sums_rows:
            try:
                valid_result[i.subject_name]["old_period_avg"] = i.summ
            except KeyError:
                continue

        # Математические расчеты тут появляются значения "Продажи сегодня ко вчера", "Рост средней к прошлой"
        for k, _ in valid_result.items():
            today_sales_sum = 0
            yesterday_sales_sum = 0
            sums_now_period = 0
            for i in valid_result[k]["dates"]:
                if i['date'] == start_date:
                    today_sales_sum = i['summ']
                    i['summ'] = f"{i['summ']}₽"
                    i['sku_percentage'] = f"{i['sku_percentage']}%"
                    continue
                if i['date'] == start_date - datetime.timedelta(days=1):
                    yesterday_sales_sum = i['summ']
                sums_now_period += i['summ']
                i['summ'] = f"{i['summ']}₽"
                i['sku_percentage'] = f"{i['sku_percentage']}%"
            valid_result[k]["sales_today_to_tomorrow"] = f"{0 if today_sales_sum == 0 or yesterday_sales_sum == 0 
            else round(today_sales_sum / yesterday_sales_sum * 100)}%"
            valid_result[k]["hight_middle_to_old_period"] = f"{0 if sums_now_period == 0 or valid_result[k].get(
                "old_period_avg") == 0 else round((sums_now_period / period.days) / valid_result[k].get(
                "old_period_avg") * 100 - 100)}%"
            valid_result[k]["old_period_avg"] = f"{valid_result[k]["old_period_avg"]}₽"

        return valid_result


    async def get_sum_sales_category_by_date(
            self,
            date: date,
            good_category: Optional[str] = None,
    ):
        """Сумма продаж по категории за конкретный день"""
        rows = await self.repository.get_sum_sales_by_date(date, good_category)
        return [SalesManagementBaseSummWithDate(**r) for r in rows]
