from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException
from app.domain.models import PriceDiscountResponseModel, PriceDiscountContainer
from app.service import CardDataService
from app.dependencies import get_card_data_service
from app.use_cases.price_discount_use_case import PriceDiscountUseCase
router = APIRouter(tags=["Price and Discount"])


@router.post("/price_discount", response_model=PriceDiscountResponseModel)
async def update_price_discount(
        data: PriceDiscountResponseModel,
        # data: List[Dict[str, PriceDiscountContainer]]
        # use_case: PriceDiscountUseCase
):
    # result = await use_case.update_data(data)# нельзя раскоментировать

    print(data)

    if not data:
        raise HTTPException(status_code=400, detail="Ошибка обновления данных")
    return data


    # print("попал")
    # print(data.dict())
    # return await service.get_card_data_by_article_id(article_id)
