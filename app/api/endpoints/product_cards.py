from datetime import datetime
import logging
import uuid

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from starlette import status

from app.dependencies import (
    get_wb_cards_service,
    get_info_from_token,
    get_wb_media_service,
    get_wb_http_session,
    get_wb_card_update_service,
    get_wb_card_create_service,
)
from app.domain.models import (
    DuplicateWBProductCardRequest,
    DuplicateCardToAccountsRequest,
    DuplicateWBProductCardResponse,
    DuplicateCardToAccountsResponse,
    UserPermissions,
    WBCardSpecificationUpdateRequest,
    WBCardUploadRequest,
    CardOperationResponse,
    CardWBMediaLinksUpdate,
)
from app.service.product_cards import WildberriesCardsService
from app.service.wb_media import WBMediaService
from app.service.wb_card_create import WBCardCreateService
from app.service.wb_card_update import WBCardUpdateService
from app.infrastructure.API.wildberries.content.wb_cards import CardsWBAPI


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cards", tags=["Карточки товаров"])


@router.post("/wb/duplicate", description="Создание дубликата карточки товара на WB.")
async def duplicate_wb_card(
    data: DuplicateWBProductCardRequest,
    user: UserPermissions = Depends(get_info_from_token),
    service: WildberriesCardsService = Depends(get_wb_cards_service),
    session: ClientSession = Depends(get_wb_http_session),
) -> DuplicateWBProductCardResponse:
    """Создать дубликат карточки товара."""
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        source_wb_client = CardsWBAPI(account_name=data.source_account, session=session)
        result = await service.duplicate_card(
            wb_client=source_wb_client,
            source_nm_id=data.nm_id,
            sync_stocks=data.sync_stocks,
            close_old=data.close_old_card,
            user_id=user.user_id,
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
    session: ClientSession = Depends(get_wb_http_session),
) -> DuplicateCardToAccountsResponse:
    """Создать дубликат карточки товара на других аккаунтах."""
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        source_wb_client = CardsWBAPI(account_name=data.source_account, session=session)
        target_wb_clients = [
            CardsWBAPI(
                account_name=account,
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
            user_id=user.user_id,
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
    service: WBCardUpdateService = Depends(get_wb_card_update_service),
) -> CardOperationResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    try:
        task_id = f"update_{uuid.uuid4().hex}"
        result = await service.update_card(data, user_id=user.user_id)
        return CardOperationResponse(
            task_id=task_id,
            status="queued",
            message="Запрос на обновление карточки принят в обработку",
            account=data.account,
            product_id=data.product_id,
            nm_id=result,
            created_at=datetime.now()
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/update: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error.")


@router.post("/wb/upload", description="Создать карточку товара на WB.")
async def upload_wb_card(
    data: WBCardUploadRequest,
    user: UserPermissions = Depends(get_info_from_token),
    service: WBCardCreateService = Depends(get_wb_card_create_service),
) -> CardOperationResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    try:
        task_id = f"create_{uuid.uuid4().hex}"
        result = await service.create_card(data, user_id=user.user_id)
        return CardOperationResponse(
            task_id=task_id,
            status="queued",
            message="Запрос на создание карточки принят в обработку",
            account=data.account,
            product_id=data.product_id,
            nm_id=result,
            created_at=datetime.now()
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка в /wb/upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error.")


@router.post(
    "/wb/media/links",
    status_code=status.HTTP_202_ACCEPTED,
    description="""
    **Обновление медиа карточки товара на WB по ссылкам.**

    Нужно передавать как старые, так и новые ссылки.
    Новые медиа полностью заменяют старые.
    Требования:
        - Максимум 5 уникальных изображений для карточки
        - Максимум 1 видео
        - Ссылки должны вести напрямую на файлы
    """,
    deprecated=True
)
async def update_media_by_links(
    data: CardWBMediaLinksUpdate,
    service: WBMediaService = Depends(get_wb_media_service),
    user: UserPermissions = Depends(get_info_from_token),
) -> CardOperationResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    task_id = f"media_links_{uuid.uuid4().hex}"
    try:
        pass
        # await service.update_card_media_links(data, user_id=user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except Exception as e:
        logger.exception(f"Ошибка во время обновления медиа: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

    return CardOperationResponse(
        task_id=task_id,
        status="completed",
        message="Медиа успешно обновлены",
        account=data.account,
        product_id="None",
        nm_id=int(data.nm_id),
        created_at=datetime.now()
    )


@router.post(
    "/wb/media/file/add",
    status_code=status.HTTP_202_ACCEPTED,
    description="""
    **Загрузка обложки или видео для карточки товара на WB.**

    Требования:
        - Форматы фото (JPG, PNG, BMP, GIF, WebP)
        - формат видео (MP4, MOV)
        - Размер фото: до 32 Мб
        - Размер видео: до 50 Мб
    """,
)
async def upload_media_files(
    nm_id: int = Header(..., description="Артикул WB"),
    file: UploadFile = File(..., description="Файл для загрузки"),
    service: WBMediaService = Depends(get_wb_media_service),
    user: UserPermissions = Depends(get_info_from_token),
) -> CardOperationResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    allowed_photo_ext = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp")
    allowed_video_ext = (".mp4", ".mov")

    filename = file.filename.lower()
    is_photo = any(filename.endswith(ext) for ext in allowed_photo_ext)
    is_video = any(filename.endswith(ext) for ext in allowed_video_ext)

    if not (is_photo or is_video):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Недопустимый формат файла: {file.filename}. "
                f"Фото: {', '.join(allowed_photo_ext)}. Видео: {', '.join(allowed_video_ext)}"
            )
        )

    task_id = f"media_files_{uuid.uuid4().hex}"

    try:
        account = await service.upload_card_media_file(
            nm_id=nm_id,
            account=None,
            is_video=is_video,
            file=file,
            user_id=user.user_id,
            display_order=1,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except Exception as e:
        logger.exception(f"Ошибка во время загрузки медиа из файла: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

    return CardOperationResponse(
        task_id=task_id,
        status="completed",
        message="Медиафайл успешно загружен.",
        account=account,
        product_id="None",
        nm_id=nm_id,
        created_at=datetime.now()
    )
