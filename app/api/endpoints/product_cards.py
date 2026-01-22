import asyncio
import logging

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_wb_cards_service
from app.domain.models import (
    DuplicateWBProductCardRequest,
    DuplicateCardToAccountsRequest,
    UpdateWBCardsRequest,
    UploadWBCardsRequest,
    MoveToTrashRequest,
    CardInfoRequest,
    WbCard,
    WbCardTrashed,
    DuplicateWBProductCardResponse,
    DuplicateCardToAccountsResponse,
    UploadWBCardsResponse,
    UpdateWBCardsResponse,
)
from app.service.product_cards import WildberriesCardsService
from app.infrastructure.WildberriesAPI.cards import WBCardsClient


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cards", tags=["Карточки товаров"])


@router.post("/wb/duplicate", description="Создание дубликата карточки товара на WB.")
async def duplicate_wb_card(
    data: DuplicateWBProductCardRequest,
    service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> DuplicateWBProductCardResponse:
    """Создать дубликат карточки товара."""
    try:
        async with ClientSession() as session:
            source_wb_client = WBCardsClient(account=data.account, session=session)
            result = await service.duplicate_card(
                source_wb_client=source_wb_client,
                source_nm_id=data.nm_id,
                close_old=data.close_old_card
            )
        return result
    except ValueError as e:
        logger.warning(f"Ошибка клиента при дублировании: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/duplicate: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {e}")


@router.post("/wb/duplicate-to-accounts", description="Создание дубликата карточки товара на других аккаунтах WB.")
async def duplicate_wb_card_to_accounts(
    data: DuplicateCardToAccountsRequest,
    service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> DuplicateCardToAccountsResponse:
    """Создать дубликат карточки товара на других аккаунтах."""
    try:
        async with ClientSession() as session:
            source_wb_client = WBCardsClient(account=data.account, session=session)
            target_wb_clients = [
                WBCardsClient(
                    account=account,
                    session=session,
                )
                for account in set(data.target_accounts)
                if account.lower() != data.account.lower()
            ]

            if not target_wb_clients:
                raise ValueError("Не указаны аккаунты для создания дубликатов.")
    
            result = await service.duplicate_card_to_accounts(
                source_wb_client=source_wb_client,
                target_wb_clients=target_wb_clients,
                source_nm_id=data.nm_id,
            )
        return result
    except ValueError as e:
        logger.warning(f"Ошибка клиента при дублировании: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/duplicate: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {e}")


@router.post("/wb/upload", description="Создать карточки товаров в личных кабинетах WB.")
async def upload_wb_cards(
    data: list[UploadWBCardsRequest],
    service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> list[UploadWBCardsResponse]:
    """Создать карточки товаров в личных кабинетах WB."""
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой запрос")

    final_result = []
    tasks = []

    try:
        async with ClientSession() as session:
            for req in data:
                account = req.account
                cards = req.data
                wb_client = WBCardsClient(account=account, session=session)

                tasks.append(asyncio.create_task(
                    service.create_cards_from_request(wb_client=wb_client, creation_requests=cards)
                ))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.exception(f"Ошибка при создании карточек: {result}")
                    raise result

                final_result.append(result)

        return final_result
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать карточки."
        )


@router.post("/wb/update", description="Обновить информацию карточек товаров в личных кабинетах WB.")
async def update_wb_cards(
    data: list[UpdateWBCardsRequest],
    service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> list[UpdateWBCardsResponse]:
    """Обновить информацию карточек товаров в личных кабинетах WB."""
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой запрос")

    final_result = []
    tasks = []

    try:
        async with ClientSession() as session:
            for req in data:
                account = req.account
                cards = req.data
                wb_client = WBCardsClient(account=account, session=session)

                tasks.append(asyncio.create_task(
                    service.update_cards_from_request(wb_client=wb_client, update_requests=cards)
                ))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(results, Exception):
                    logger.exception(f"Ошибка при обновлении карточек: {result}")

                final_result.append(result)

        return final_result
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить карточки."
        )


@router.post("/wb/delete/trash", description="Переместить карточку товара в корзину.")
async def move_card_to_trash(
    data: MoveToTrashRequest,
    service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> dict[str, bool]:
    """Переместить карточку товара в корзину."""
    try:
        async with ClientSession() as session:
            wb_client = WBCardsClient(account=data.account, session=session)
            success = await service.move_card_to_trash(wb_client, data.nm_id)
        return {"success": success}
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/delete/trash: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось переместить карточку в корзину"
        )


@router.post("/wb/info", description="Получить информацию о карточке с WB.")
async def get_card_info(
    data: CardInfoRequest,
    service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> WbCard:
    """Получить информацию о карточке с WB."""
    if not data.nm_id and not data.vendor_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Укажите nm_id или vendor_code")

    try:
        async with ClientSession() as session:
            wb_client = WBCardsClient(account=data.account, session=session)
            card = await service.get_card_info(
                wb_client,
                nm_id=data.nm_id,
                vendor_code=data.vendor_code
            )

        if card is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Карточка не найдена")

        return card
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении данных карточки"
        )

@router.post("/wb/info/trashed", description="Получить информацию о карточке с WB из корзины")
async def get_trashed_card_info(
    data: CardInfoRequest,
    service: WildberriesCardsService = Depends(get_wb_cards_service),
) -> WbCardTrashed:
    """Получить информацию о карточке с WB из корзины."""
    if not data.nm_id and not data.vendor_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Укажите nm_id или vendor_code")

    try:
        async with ClientSession() as session:
            wb_client = WBCardsClient(account=data.account, session=session)
            card = await service.get_trashed_card_info(
                wb_client,
                nm_id=data.nm_id,
                vendor_code=data.vendor_code
            )

        if card is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Карточка не найдена")

        return card
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/info/trashed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении данных карточки из корзины"
        )
