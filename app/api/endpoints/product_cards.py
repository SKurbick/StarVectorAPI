from datetime import datetime
import logging
import uuid

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.dependencies import get_wb_cards_service, get_info_from_token
from app.domain.models import (
    DuplicateWBProductCardRequest,
    DuplicateCardToAccountsRequest,
    DuplicateWBProductCardResponse,
    DuplicateCardToAccountsResponse,
    UserPermissions,
    WBCardSpecificationUpdateRequest,
    WBCardUploadRequest,
    CardOperationResponse,
)
from app.service.product_cards import WildberriesCardsService
from app.infrastructure.WildberriesAPI.cards import WBCardsClient


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cards", tags=["Карточки товаров"])


@router.post("/wb/duplicate", description="Создание дубликата карточки товара на WB.")
async def duplicate_wb_card(
    data: DuplicateWBProductCardRequest,
    user: UserPermissions = Depends(get_info_from_token),
    service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> DuplicateWBProductCardResponse:
    """Создать дубликат карточки товара."""
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        async with ClientSession() as session:
            source_wb_client = WBCardsClient(account=data.source_account, session=session)
            result = await service.duplicate_card(
                wb_client=source_wb_client,
                source_nm_id=data.nm_id,
                sync_stocks=data.sync_stocks,
                close_old=data.close_old_card
            )
        return result
    except ValueError as e:
        logger.warning(f"Ошибка клиента при дублировании: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/duplicate: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error.")


@router.post("/wb/duplicate-to-accounts", description="Создание дубликата карточки товара на других аккаунтах WB.")
async def duplicate_wb_card_to_accounts(
    data: DuplicateCardToAccountsRequest,
    user: UserPermissions = Depends(get_info_from_token),
    service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> DuplicateCardToAccountsResponse:
    """Создать дубликат карточки товара на других аккаунтах."""
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        async with ClientSession() as session:
            source_wb_client = WBCardsClient(account=data.source_account, session=session)
            target_wb_clients = [
                WBCardsClient(
                    account=account,
                    session=session,
                )
                for account in set(data.target_accounts)
                if account.lower() != data.source_account.lower()
            ]

            if not target_wb_clients:
                raise ValueError("Не указаны аккаунты для создания дубликатов.")
    
            result = await service.duplicate_card_to_accounts(
                source_wb_client=source_wb_client,
                target_wb_clients=target_wb_clients,
                sync_stocks=data.sync_stocks,
                source_nm_id=data.nm_id,
            )
        return result
    except ValueError as e:
        logger.warning(f"Ошибка клиента при дублировании: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/duplicate-to-accounts: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error.")


@router.post("/wb/update", description="Обновить информацию карточки товара на WB.")
async def update_wb_card(
    data: WBCardSpecificationUpdateRequest,
    user: UserPermissions = Depends(get_info_from_token),
    # service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> CardOperationResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    
    task_id = f"update_{uuid.uuid4().hex}"
    return CardOperationResponse(
        task_id=task_id,
        status="queued",
        message="Запрос на обновление карточки принят в обработку",
        account=data.account,
        product_id=data.product_id,
        nm_id=data.nm_id,
        created_at=datetime.now()
    )


@router.post("/wb/upload", description="Создать карточку товара на WB.")
async def upload_wb_card(
    data: WBCardUploadRequest,
    user: UserPermissions = Depends(get_info_from_token),
    # service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> CardOperationResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    task_id = f"create_{uuid.uuid4().hex}"
    
    return CardOperationResponse(
        task_id=task_id,
        status="queued",
        message="Запрос на создание карточки принят в обработку",
        account=data.account,
        product_id=data.product_id,
        nm_id=None,
        created_at=datetime.now()
    )
