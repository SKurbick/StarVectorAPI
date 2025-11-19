from openpyxl import load_workbook
from enum import Enum
from fastapi import UploadFile
from datetime import datetime


def normalize_value(key_name: str, value):

    if value is None:
        return None
    
    if key_name == "penalty_date":
        if isinstance(value, str):
            return datetime.strptime(value.strip(), "%d.%m.%Y").date()
        elif isinstance(value, datetime):
            return value.date()
        
    elif key_name == "nm_id":
        value_str = str(value).replace("\xa0", "").replace(" ", '').split(".")[0]
        return int(value_str)
    
    elif key_name in ("bonus_type_name", "srid", "loss_owner", "comment"):
        return str(value).replace("\xa0", ' ').strip()
    
    else:
        return value


def get_columns_values_from_excel_file(
        upload_file: UploadFile,
        column_indices: list[int],
        enum_mapping: Enum,
        start_row: int = 2
) -> list[dict[str]]:
    """Функция для парсинга данных из определенных столбцов Excel таблицы по их номерам

    Args:
        upload_file (UploadFile): файл Excel
        column_indices (list[int]): Спсиок номеров столбцов, которые считывать (начиная с 1)
        enum_mapping (Enum): Соответствие названия ключа с позицией столбца в Excel файле
        start_row (int, optional): _description_. Defaults to 2.

    Returns:
        list[dict[str]]: данные из указанных столбцов
    """
    upload_file.file.seek(0)

    wb = load_workbook(
        filename=upload_file.file,
        read_only=True,
        data_only=True
    )

    try:
        ws = wb.active
        result_data = []
        key_mapping = {}

        for idx in column_indices:
            enum_item = next((item for item in enum_mapping if item.value == idx), None)
            key_mapping[idx] = enum_item.name

        for row in ws.iter_rows(
            min_row=start_row,
            max_row=ws.max_row,
            values_only=True
        ):
        
            row_data = {}

            for col_idx in column_indices:
                key_name = key_mapping[col_idx]

                if col_idx - 1 < len(row):
                    cell_value = row[col_idx - 1]
                    if isinstance(col_idx, str):
                        cell_value = normalize_value(key_name=key_name, value=cell_value)
                    else:
                        cell_value = None
                    
                row_data[key_name] = cell_value
            
            result_data.append(row_data)
        
        return result_data
    
    finally:
        wb.close()