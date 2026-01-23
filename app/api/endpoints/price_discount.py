import asyncio
from pprint import pprint
from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.domain.models import PriceDiscountResponseModel, PriceDiscountContainer, ResponseMessage, UserPermissions
from app.dependencies import get_price_discount_service, get_info_from_token
from app.service.price_discount import PriceDiscountService

router = APIRouter(tags=["Price and Discount"])


@router.post("/price_discount", response_model=ResponseMessage)
async def update_price_discount(
        data: PriceDiscountResponseModel,
        user: UserPermissions = Depends(get_info_from_token),
        service: PriceDiscountService = Depends(get_price_discount_service)
):
    if not user.crm_change_price_and_discounts:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    print(data.model_dump())
    return {
        "status": 200,
        "message": "успешно ебать 👍 поздравляю"
    }

# try:
#     test_article = [255950221, 156164094]
#     # await service.update(data=data)
#     articles = []
#     for account, inner_data in data.model_dump()['update_data'].items():
#         for article_data in inner_data['data']:
#             nm_id = article_data['nmID']
#             articles.append(nm_id)
#             if nm_id not in test_article:
#                 raise HTTPException(status_code=401, detail=f"Вы используете Артикулы не из списка для тестирования. Исключите их из запроса")
#     # await asyncio.sleep(3)
#     print(data.model_dump()['update_data'])
#     return {
#         "status": 200,
#         "message": "успешно ебать 👍 поздравляю"
#     }
# except Exception as e:
#     raise HTTPException(status_code=400, detail=f"Ошибка обновления данных. Error: {e}")
