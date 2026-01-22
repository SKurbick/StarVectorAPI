from fastapi import APIRouter, Depends, Query

from app.dependencies import get_seller_account_service
from app.service.seller_account import SellerAccountService
from app.domain.models import SellerAccount


router = APIRouter(prefix="/accounts", tags=["Аккаунты продавца"])


@router.get("/", description="""
    **Получить список аккаунтов продавца.**\n
""")
async def get_all_wb_accounts(
    is_active: bool | None = Query(None, description=(
    "`true` - получить **активные** аккаунты<br>"
    "`false` - получить **неактивные** аккаунты<br>"
    "По умолчанию вернуться все аккаунты продавца."
    )),
    service: SellerAccountService = Depends(get_seller_account_service)
) -> list[SellerAccount]:
    return await service.get_list(is_active)
