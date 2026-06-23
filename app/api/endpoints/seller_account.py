from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.dependencies import get_seller_account_service, get_info_from_token
from app.service.seller_account import SellerAccountService
from app.domain.models import SellerAccount, UserPermissions


router = APIRouter(prefix="/accounts", tags=["Аккаунты продавца"])


@router.get("/", description="""
    **Получить список аккаунтов продавца.**\n
""", deprecated=True)
async def get_all_wb_accounts(
    is_active: bool | None = Query(None, description=(
    "`true` - получить **активные** аккаунты<br>"
    "`false` - получить **неактивные** аккаунты<br>"
    "По умолчанию вернуться все аккаунты продавца."
    )),
    service: SellerAccountService = Depends(get_seller_account_service),
    user: UserPermissions = Depends(get_info_from_token),
) -> list[SellerAccount]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_list(is_active)
