import datetime
import logging
from typing import Optional

from app.repository.sales_management import SalesManagementRepository

from app.domain.models import (
    SalesManagementBaseSumm,
    SalesManagementManagerRow,
    SalesManagementBaseSummWithDate,
    SalesManagementBaseSummWithSKU,
    SalesManagementICWithDate,
    SalesManagementICBase,
    SalesManagementBrowsingInfoWithDate,
    SalesManagementBrowsingInfo,
    SalesManagementOutlayBase,
    SalesManagementOutlayWithDate
)


class SalesManagementService:
    def __init__(self, repository: SalesManagementRepository):
        self.repository = repository

    async def get_outlay_info_by_category_and_period(
            self,
            start_date: datetime.date,
            end_date: datetime.date,
            good_category: Optional[str] = None,
    ):
        period = start_date - end_date
        actual_outlay = await self.repository.get_outlay_by_category_and_period(
            start_date=start_date,
            end_date=end_date,
            good_category=good_category
        )
        old_outlay = await self.repository.get_old_outlay_by_category_and_period(
            start_date=start_date - datetime.timedelta(days=period.days + 1),
            end_date=end_date - datetime.timedelta(days=period.days + 1),
            period=period.days + 1,
            good_category=good_category
        )
        old_revenue = await self.repository.get_old_sums_revenue_by_category_and_period(
            start_date=start_date - datetime.timedelta(days=period.days + 1),
            end_date=end_date - datetime.timedelta(days=period.days + 1),
            period=period.days + 1,
            good_category=good_category
        )
        actual_ic_rows = await self.repository.get_sums_ic_and_revenue_by_category_and_period(
            start_date=start_date,
            end_date=end_date,
            good_category=good_category
        )
        old_avg_ic_rows = await self.repository.get_old_sums_ic_by_category_and_period(
            start_date=start_date - datetime.timedelta(days=period.days + 1),
            end_date=end_date - datetime.timedelta(days=period.days + 1),
            period=period.days + 1,
            good_category=good_category
        )
        valid_actual_ic_rows = [SalesManagementICWithDate(**r) for r in actual_ic_rows]
        valid_old_avg_ic_rows = [SalesManagementICBase(**r) for r in old_avg_ic_rows]
        valid_old_revenue_avg_rows = [SalesManagementBaseSumm(**r) for r in old_revenue]
        valid_actual_outlay = [SalesManagementOutlayWithDate(**r) for r in actual_outlay]
        valid_old_avg_outlay = [SalesManagementOutlayBase(**r) for r in old_outlay]
        valid_result = {}


        for i in valid_actual_outlay:
            if valid_result.get(i.subject_name) is None:
                valid_result[i.subject_name] = {
                    "old_period_avg_outlay": 0,
                    "old_period_avg_revenue": 0,
                    "old_period_avg_ic": 0,
                    "old_period_CHP-RC": 0,
                    "growth_today_to_tomorrow": 0
                }
            if valid_result[i.subject_name].get("dates") is None:
                valid_result[i.subject_name]["dates"] = [
                    {"date": i.date, "adv_spend": i.adv_spend}]
            else:
                valid_result[i.subject_name]["dates"].append(
                    {"date": i.date, "adv_spend": i.adv_spend})


        # for i in valid_actual_ic_rows:
        #     try:
        #         for k in valid_result[i.subject_name]["dates"]:
        #             if k["date"] == i.date:
        #                 k["ic"] = i.ic
        #                 k["revenue"] = i.revenue
        #     except KeyError:
        #         continue

        # Добавление в результирующий словарь среднего количества продаж за период по категории
        for i in valid_old_revenue_avg_rows:
            try:
                valid_result[i.subject_name]["old_period_avg_revenue"] = i.summ
            except KeyError:
                continue
        logging.info(f"revenue_avg_rows {len(valid_old_revenue_avg_rows)}")
        # Добавление в результирующий словарь среднего количества затрат за период по категории
        for i in valid_old_avg_outlay:
            try:
                valid_result[i.subject_name]["old_period_avg_outlay"] = i.adv_spend
            except KeyError:
                continue
        logging.info(f"valid_old_avg_outlay {len(valid_old_avg_outlay)}")
        # Добавление в результирующий словарь среднего количества ИУ за период по категории
        for i in valid_old_avg_ic_rows:
            try:
                valid_result[i.subject_name]["old_period_avg_ic"] = i.ic
            except KeyError:
                continue
        logging.info(f"valid_old_avg_ic_rows {len(valid_old_avg_ic_rows)}")
        return valid_result

    async def get_browsing_info_by_category_and_period(
            self,
            start_date: datetime.date,
            end_date: datetime.date,
            good_category: Optional[str] = None,
    ):
        period = start_date - end_date
        actual_browsing = await self.repository.get_browsing_info_by_category_and_period(
            start_date=start_date,
            end_date=end_date,
            good_category=good_category
        )
        old_browsing = await self.repository.get_old_browsing_info_by_category_and_period(
            start_date=start_date - datetime.timedelta(days=period.days + 1),
            end_date=end_date - datetime.timedelta(days=period.days + 1),
            period=period.days + 1,
            good_category=good_category
        )
        valid_actual_browsing = [SalesManagementBrowsingInfoWithDate(**r) for r in actual_browsing]
        valid_old_browsing = [SalesManagementBrowsingInfo(**r) for r in old_browsing]
        valid_result = {}

        # Добавление в результирующий словарь статистики по датам
        for i in valid_actual_browsing:
            if valid_result.get(i.subject_name) is None:
                valid_result[i.subject_name] = {
                    "old_views_avg": 0,
                    "old_clicks_avg": 0,
                    "old_clicks_avg_percentage": 0,
                }
            if valid_result[i.subject_name].get("dates") is None:
                valid_result[i.subject_name]["dates"] = [
                    {"date": i.date, "views": i.views, "clicks_percentage": i.clicks, "clicks_avg": i.clicks_avg}]
            else:
                valid_result[i.subject_name]["dates"].append(
                    {"date": i.date, "views": i.views, "clicks_percentage": i.clicks, "clicks_avg": i.clicks_avg})

        # Добавление в результирующий словарь статистики за прошлый период
        for i in valid_old_browsing:
            try:
                valid_result[i.subject_name]["old_views_avg"] = i.views
                valid_result[i.subject_name]["old_clicks_avg"] = i.clicks_avg
                valid_result[i.subject_name]["old_clicks_avg_percentage"] = i.clicks
            except KeyError:
                continue

        return valid_result

    async def get_sums_individual_conditions_by_period_with_category(
            self,
            start_date: datetime.date,
            end_date: datetime.date,
            good_category: Optional[str] = None,
    ):
        """Получить данные по индивидуальным условиям с категориями за определенный период"""
        period = start_date - end_date
        sums_ic_rows = await self.repository.get_sums_ic_and_revenue_by_category_and_period(
            start_date=start_date,
            end_date=end_date,
            good_category=good_category
        )
        old_period_avg_sums_ic_rows = await self.repository.get_old_sums_ic_by_category_and_period(
            start_date=start_date - datetime.timedelta(days=period.days + 1),
            end_date=end_date - datetime.timedelta(days=period.days + 1),
            period=period.days + 1,
            good_category=good_category
        )
        old_period_avg_revenue_rows = await self.repository.get_old_sums_revenue_by_category_and_period(
            start_date=start_date - datetime.timedelta(days=period.days + 1),
            end_date=end_date - datetime.timedelta(days=period.days + 1),
            period=period.days + 1,
            good_category=good_category
        )
        valid_sums_ic_rows = [SalesManagementICWithDate(**r) for r in sums_ic_rows]
        valid_old_period_avg_ic_rows = [SalesManagementICBase(**r) for r in old_period_avg_sums_ic_rows]
        valid_old_period_avg_revenue_rows = [SalesManagementBaseSumm(**r) for r in old_period_avg_revenue_rows]
        valid_result = {}

        # Добавление в результирующий словарь и разбивка по секциям дат с выручками и
        # ИУ и процентами по маржинальности за каждую дату
        for i in valid_sums_ic_rows:
            if valid_result.get(i.subject_name) is None:
                valid_result[i.subject_name] = {
                    "old_period_ic_avg": 0,
                    "old_period_revenue_avg": 0,
                    "margin_per_period": 0,
                    "sales_today_to_tomorrow": 0,
                    "max_profit_per_period": 0
                }
            if valid_result[i.subject_name].get("dates") is None:
                valid_result[i.subject_name]["dates"] = [
                    {"date": i.date, "ic": i.ic, "revenue": i.revenue, "margin_per_date": ""}]
            else:
                valid_result[i.subject_name]["dates"].append(
                    {"date": i.date, "ic": i.ic, "revenue": i.revenue, "margin_per_date": ""})

        # Добавление в результирующий словарь маржинальность по ИУ за предидущий период
        for i in valid_old_period_avg_ic_rows:
            try:
                valid_result[i.subject_name]["old_period_ic_avg"] = i.ic
            except KeyError:
                continue

        # Добавление в результирующий словарь выручки за предидущий период
        for i in valid_old_period_avg_revenue_rows:
            try:
                valid_result[i.subject_name]["old_period_revenue_avg"] = i.summ
            except KeyError:
                continue

        # Математические расчеты тут появляются значения
        # "ИУ сегодня ко вчера",
        # "маржинальность ИУ по датам",
        # "Процентное соотношение маржинальности к выручке за предидущий период"
        for k, _ in valid_result.items():
            today_sales_sum = 0
            yesterday_sales_sum = 0
            sums_now_period = 0
            max_profit = 0
            for i in valid_result[k]["dates"]:
                margin = self._math_percent_create(
                    low_num=i["ic"],
                    up_num=i["revenue"]
                )
                i["margin_per_date"] = margin
                if margin > max_profit:
                    max_profit = margin
                if i['date'] == start_date:
                    today_sales_sum = i['ic']
                    continue
                if i['date'] == start_date - datetime.timedelta(days=1):
                    yesterday_sales_sum = i['ic']
                sums_now_period += i['ic']
            valid_result[k]["sales_today_to_tomorrow"] = self._math_percent_create(
                low_num=today_sales_sum,
                up_num=yesterday_sales_sum
            )
            valid_result[k]["margin_per_period"] = self._math_percent_create(
                low_num=valid_result[k].get("old_period_ic_avg"),
                up_num=valid_result[k].get("old_period_revenue_avg")
            )
            valid_result[k]["max_profit_per_period"] = max_profit
        if valid_result.get(None):
            del valid_result[None]

        return valid_result

    async def get_sum_revenue_category_by_period_with_managers(
            self,
            start_date: datetime.date,
            end_date: datetime.date,
            good_category: Optional[str] = None,
    ):
        """Получить общие цифры продаж по категориям за определенный период, с менеджерами"""
        period = start_date - end_date
        sums_rows = await self.repository.get_sums_revenue_by_category_and_period(
            date_start=start_date,
            date_end=end_date,
            good_category=good_category
        )
        manager_rows = await self.repository.get_managers_name_by_category_and_period(
            date_start=start_date,
            date_end=end_date,
            good_category=good_category
        )
        old_period_avg_sums_rows = await self.repository.get_old_sums_revenue_by_category_and_period(
            start_date=start_date - datetime.timedelta(days=period.days + 1),
            end_date=end_date - datetime.timedelta(days=period.days + 1),
            period=period.days + 1,
            good_category=good_category
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
                    "old_period_avg": 0,
                    "sku_period_avg": 0
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
            avg_sku_period = 0
            for i in valid_result[k]["dates"]:
                if i['date'] == start_date:
                    today_sales_sum = i['summ']
                    avg_sku_period += i['sku_percentage']
                    continue
                if i['date'] == start_date - datetime.timedelta(days=1):
                    yesterday_sales_sum = i['summ']
                sums_now_period += i['summ']
                avg_sku_period += i['sku_percentage']
            valid_result[k]["sales_today_to_tomorrow"] = self._math_percent_create(
                low_num=today_sales_sum,
                up_num=yesterday_sales_sum
            )
            valid_result[k]["height_middle_to_old_period"] = self._math_average_to_average_growth(
                sums_now_period=sums_now_period,
                period=period.days,
                old_period_avg=valid_result[k].get("old_period_avg"),
            )
            valid_result[k]["old_period_avg"] = valid_result[k]["old_period_avg"]
            valid_result[k]["sku_period_avg"] = round(avg_sku_period / (period.days + 1))
        if valid_result.get(None):
            del valid_result[None]

        return valid_result

    async def get_sum_sales_category_by_date(
            self,
            date: datetime.date,
            good_category: Optional[str] = None,
    ):
        """Сумма продаж по категории за конкретный день"""
        rows = await self.repository.get_sum_revenue_by_date(date, good_category)
        return [SalesManagementBaseSummWithDate(**r) for r in rows]

    def _math_percent_create(
            self,
            low_num: int,
            up_num: int,
    ) -> int:
        if low_num == 0:
            return 0
        if up_num == 0:
            return 0
        return round(low_num / up_num * 100)

    def _math_average_to_average_growth(
            self,
            sums_now_period: int,
            period: int,
            old_period_avg: int,
    ):
        if sums_now_period == 0:
            return 0
        if old_period_avg == 0:
            return 0
        if period == 0:
            period = 1
        return round((sums_now_period / period) / old_period_avg * 100 - 100)
