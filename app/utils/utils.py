from openpyxl import load_workbook
from enum import Enum
from fastapi import UploadFile


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
        filename=upload_file,
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
                        cell_value = cell_value.replace("\xa0", " ")
                    else:
                        cell_value = None
                    
                row_data[key_name] = cell_value
            
            result_data.append(row_data)
        
        return result_data
    
    finally:
        wb.close()