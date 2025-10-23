from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


FIELD_TYPES = {
    # Даты (без времени)
    "date_from": "date",
    "create_dt": "date",
    "fix_tariff_date_from": "date",
    "fix_tariff_date_to": "date",
    "rr_dt": "date",

    # Даты со временем
    "order_dt": "datetime",
    "sale_dt": "datetime",

    # Числа
    "realizationreport_id": "int",
    "rrd_id": "int",
    "gi_id": "int",
    "nm_id": "int",
    "quantity": "int",
    "sale_percent": "int",
    "shk_id": "int",
    "delivery_amount": "int",
    "return_amount": "int",
    "ppvz_office_id": "int",
    "ppvz_supplier_id": "int",
    "assembly_id": "int",
    "report_type": "int",
    "wibes_wb_discount_percent": "int",

    # Decimal
    "dlv_prc": "decimal",
    "retail_price": "decimal",
    "retail_amount": "decimal",
    "commission_percent": "decimal",
    "retail_price_withdisc_rub": "decimal",
    "delivery_rub": "decimal",
    "product_discount_for_report": "decimal",
    "supplier_promo": "decimal",
    "ppvz_spp_prc": "decimal",
    "ppvz_kvw_prc_base": "decimal",
    "ppvz_kvw_prc": "decimal",
    "sup_rating_prc_up": "decimal",
    "ppvz_sales_commission": "decimal",
    "ppvz_for_pay": "decimal",
    "ppvz_reward": "decimal",
    "acquiring_fee": "decimal",
    "acquiring_percent": "decimal",
    "ppvz_vw": "decimal",
    "ppvz_vw_nds": "decimal",
    "penalty": "decimal",
    "additional_payment": "decimal",
    "rebill_logistic_cost": "decimal",
    "storage_fee": "decimal",
    "deduction": "decimal",
    "acceptance": "decimal",
    "installment_cofinancing_amount": "decimal",
    "cashback_amount": "decimal",
    "cashback_discount": "decimal",
    "cashback_commission_change": "decimal",

    # Булевы
    "is_kgvp_v2": "bool",
    "srv_dbs": "bool",
    "is_legal_entity": "bool",

    # Строки
    "currency_name": "str",
    "suppliercontract_code": "str",
    "subject_name": "str",
    "brand_name": "str",
    "sa_name": "str",
    "ts_name": "str",
    "barcode": "str",
    "doc_type_name": "str",
    "office_name": "str",
    "supplier_oper_name": "str",
    "gi_box_type_name": "str",
    "payment_processing": "str",
    "acquiring_bank": "str",
    "ppvz_office_name": "str",
    "ppvz_supplier_name": "str",
    "ppvz_inn": "str",
    "declaration_number": "str",
    "bonus_type_name": "str",
    "sticker_id": "str",
    "site_country": "str",
    "rebill_logistic_org": "str",
    "kiz": "str",
    "srid": "str",
    "trbx_id": "str",
    "order_uid": "str",
    "account": "str",
}


def normalize_wb_value(value: Any, target_type: str) -> Any:
    """
    Нормализует значение из WB API под ожидаемый тип.
    """

    if value == "" or value is None:
        return None

    try:
        if target_type == "date":
            if isinstance(value, str):
                return date.fromisoformat(value)
            elif isinstance(value, date):
                return value
            else:
                raise ValueError(f"Unexpected type for date: {type(value)}")

        elif target_type == "datetime":
            if isinstance(value, str):
                dt = value.rstrip("Z")

                return datetime.fromisoformat(dt)
            elif isinstance(value, datetime):
                return value.replace(tzinfo=None)
            else:
                raise ValueError(f"Unexpected type for datetime: {type(value)}")

        elif target_type == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")

            return bool(value)

        elif target_type == "int":
            if isinstance(value, bool):
                raise ValueError("Boolean is not a valid int")
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                if value.is_integer():
                    return int(value)
                raise ValueError("Float is not an integer")
            if isinstance(value, str):
                try:
                    return int(value)
                except ValueError:
                    pass

            raise ValueError("Not a valid int")

        elif target_type == "decimal":
            if value == "" or value is None:
                return None
            try:
                return Decimal(str(value))
            except (ValueError, InvalidOperation, TypeError):
                return None

        elif target_type == "str":
            return str(value) if value is not None else None

        else:
            return value

    except (ValueError, TypeError, OverflowError):
        return None
