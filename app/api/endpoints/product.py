from datetime import datetime
import logging
from typing import Annotated, Optional, Literal
import uuid

from fastapi import APIRouter, Depends, Query, HTTPException, Path, UploadFile, File, Header, Body
from starlette import status

from app.dependencies import (
    get_info_from_token,
    get_wb_media_service,
    get_product_service,
    get_product_specifications_update_service,
)
from app.domain.models import (
    SubjectDataWithProductsResponse,
    UserPermissions,
    ProductWBCards,
    ProductWBSpecificationResponse,
    ProductWBSpecificationUpdate,
    ProductUpdateSpecificationsResponse,
    CardOperationResponse,
    ProductWBMediaLinksUpdate,
    ResponseMessage,
    WBPhoto,
    ProductWBHealthResponse,
    ProductWBHealthQueryParams,
    IssueTypeFilter,
    SortByParam,
    ProductBase,
    JoinProductsToWBGroupRequest,
    SplitProductsFromWBGroupRequest,
)
from app.service.product import ProductService
from app.service.wb_media import WBMediaService
from app.service.product_specifications import ProductWBSpecificationsUpdateService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Товары"])


@router.get("/grouped_by_subjects", status_code=status.HTTP_200_OK)
async def get_products_grouped_by_subjects(
        service: Annotated[ProductService, Depends(get_product_service)],
        limit: Annotated[int, Query(ge=1)] = 1000,
        offset: Annotated[int, Query(ge=0)] = 0,
        user: UserPermissions = Depends(get_info_from_token),
) -> list[SubjectDataWithProductsResponse]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_products_grouped_by_subjects(
        limit=limit,
        offset=offset,
    )


@router.get("/wb/subjects/{subject_id}", status_code=status.HTTP_200_OK, description="""
    **Получить список товаров по предмету WB.**
    subject_id: id предмета.
""")
async def get_products_by_wb_subject(
    subject_id: int = Path(..., description="ID предмета"),
    service: ProductService = Depends(get_product_service),
    user: UserPermissions = Depends(get_info_from_token),
) -> list[ProductBase]:
    """
    Получить список товаров по предмету WB.
    """
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    return await service.get_products_by_wb_subject(subject_id)


@router.post("/subject", status_code=status.HTTP_200_OK, description="""
    **Присвоить предмет WB для товара.**
""")
async def set_subject_id(
    product_id: str = Body(..., description="Артикул товара"),
    subject_id: int = Body(..., description="id предмета WB"),
    user: UserPermissions = Depends(get_info_from_token),
    service: ProductService = Depends(get_product_service),
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        await service.set_subject_id(product_id, subject_id, user.user_id)
        return ResponseMessage(
            status=status.HTTP_200_OK,
            message=f"Товару id={product_id} присвоен предмет id={subject_id}"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except Exception as e:
        logger.exception(f"Ошибка во время присвоения предмета товару товара: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.get("/{id}/wb/group", status_code=status.HTTP_200_OK, description="""
    **Получить объединенные товары.**
    id: локальный артикул товара (wild).
""")
async def get_product_wb_group(
    id: str = Path(..., description="Артикул товара."),
    user: UserPermissions = Depends(get_info_from_token),
    service: ProductService = Depends(get_product_service),
) -> list[ProductBase]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_product_wb_group(product_id=id)
    except ValueError as e:
        logger.exception(f"Ошибка во время получения группы объединенных товаров: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Ошибка во время получения группы объединенных товаров: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.post("/wb/groups/join", status_code=status.HTTP_200_OK, description="""
    **Объединить товары в группу для склеивания карточек на WB.**
""")
async def join_products_to_wb_group(
    data: JoinProductsToWBGroupRequest,
    user: UserPermissions = Depends(get_info_from_token),
    service: ProductService = Depends(get_product_service),
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.join_to_wb_group(
            target=data.target_product_id,
            product_ids=data.products
        )
    except ValueError as e:
        logger.exception(f"Ошибка во время объединения товаров в группу: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Ошибка во время объединения товаров в группу: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.post("/wb/groups/split", status_code=status.HTTP_200_OK, description="""
    **Отделить товары из группы для склеивания карточек на WB.**
""")
async def split_products_from_wb_group(
    data: SplitProductsFromWBGroupRequest,
    user: UserPermissions = Depends(get_info_from_token),
    service: ProductService = Depends(get_product_service),
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.split_from_wb_group(data.products)
    except ValueError as e:
        logger.exception(f"Ошибка во время отделения товаров из группы: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Ошибка во время отделения товаров из группы: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.get("/{id}/cards", status_code=status.HTTP_200_OK, description="""
    **Получить все карточки товара**\n   
    id: локальный артикул товара (wild).
""")
async def get_product_cards(
        id: str = Path(..., description="Локальный артикул товара."),
        user: UserPermissions = Depends(get_info_from_token),
        service: ProductService = Depends(get_product_service),
) -> ProductWBCards:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_poduct_cards(product_id=id)
    except Exception as e:
        logger.exception(f"Ошибка во время получения карточек товара: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.get("/{id}/wb/specifications", status_code=status.HTTP_200_OK, description="""
    **Получить спецификации товара.**
    id: локальный артикул товара (wild).
""")
async def get_product_wb_specifications(
    id: str = Path(..., description="Локальный артикул товара."),
    user: UserPermissions = Depends(get_info_from_token),
    service: ProductService = Depends(get_product_service),
) -> ProductWBSpecificationResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_product_wb_specifications(id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Ошибка во время получения спецификаций товара: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.post(
        "/wb/specifications/update", 
        status_code=status.HTTP_202_ACCEPTED,
        description="**Обновить спецификации товара.**"
)
async def update_product_wb_specifications(
    data: ProductWBSpecificationUpdate,
    user: UserPermissions = Depends(get_info_from_token),
    service: ProductWBSpecificationsUpdateService = Depends(get_product_specifications_update_service),
) -> ProductUpdateSpecificationsResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    task_id = f"update_{uuid.uuid4().hex}"
    try:
        updated_cards, errors = await service.update_product_specifications(data, user.user_id)
    except ValueError as e:
        logger.exception(f"Ошибка при обновлении спецификаций: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

    cards = [
        CardOperationResponse(
            task_id=task_id,
            status="completed",
            message="Карточка товара успешно обновлена",
            account=item["account"].capitalize(),
            product_id=data.id,
            nm_id=item["nm_id"],
            created_at=datetime.now(),
        )
        for item in updated_cards
    ]

    return ProductUpdateSpecificationsResponse(
        message=f"Спецификации товара обновлены. Обновлено {len(cards)} карточек. Ошибки во время обновления: [{"; ".join(errors) if errors else "Нет."}]",
        product_id=data.id,
        cards_for_update=cards,
    )


@router.get("/{id}/wb/media/additionals", status_code=status.HTTP_200_OK, description="""
    **Получение дополнительных фотографий товара, которые являются общим набором для всех карточек на WB.**
    id: локальный артикул товара (wild).
""")
async def get_additionals_photo_for_product(
    id: str = Path(..., description="Локальный артикул товара."),
    user: UserPermissions = Depends(get_info_from_token),
    service: ProductService = Depends(get_product_service),
) -> list[WBPhoto]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_product_additionals(id)


@router.post(
    "/wb/media/links",
    status_code=status.HTTP_202_ACCEPTED,
    description="""
    **Обновление медиа товара на WB по ссылкам.**

    Нужно передавать как старые, так и новые ссылки.
    Новые медиа полностью заменяют старые. Кроме уникальных медиа для карточки товара.

    Требования:
        - Максимум 25 изображений
        - Ссылки должны вести напрямую на файлы
    """,
)
async def update_media_by_links(
    data: ProductWBMediaLinksUpdate,
    service: WBMediaService = Depends(get_wb_media_service),
    user: UserPermissions = Depends(get_info_from_token),
) -> ProductUpdateSpecificationsResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    task_id = f"media_links_{uuid.uuid4().hex}"
    try:
        updated_nm_ids = await service.update_product_additionals_by_links(data=ProductWBMediaLinksUpdate(
            product_id=data.product_id,
            photos=data.photos
        ), user_id=user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Ошибка во время обновления медиа: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

    cards = [
        CardOperationResponse(
            task_id=task_id,
            status="completed",
            message="Медиа успешно обновлены",
            account="",
            product_id=data.product_id,
            nm_id=nm_id,
            created_at=datetime.now(),
        )
        for nm_id in updated_nm_ids
    ]

    return ProductUpdateSpecificationsResponse(
        message=f"Обновлены медиа в {len(updated_nm_ids)} карточек товара",
        product_id=data.product_id,
        cards_for_update=cards,
    )


@router.post(
    "/wb/media/files/add",
    status_code=status.HTTP_202_ACCEPTED,
    description="""
    **Загрузка дополнительных фото для карточек товара на WB.**

    Требования:
        - Форматы фото (JPG, PNG, BMP, GIF, WebP)
        - Размер фото: до 32 Мб
    """,
)
async def upload_media_files(
    product_id: str = Header(..., description="Локальный артикул товара"),
    replace: bool = Header(False, description="Заменить новыми файлами старые"),
    start: int = Header(-1, description="Позиция первого файла из списка. -1 - добавляем в конец (по умолчанию)"),
    files: list[UploadFile] = File(..., description="Файл для загрузки"),
    user: UserPermissions = Depends(get_info_from_token),
    service: WBMediaService = Depends(get_wb_media_service),
) -> ProductUpdateSpecificationsResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    allowed_photo_ext = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp")
    invalid_files = [file.filename for file in files if not file.filename.lower().endswith(allowed_photo_ext)]

    if invalid_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Недопустимый формат файла: {', '.join(invalid_files)}. Фото: {', '.join(allowed_photo_ext)}"),
        )

    task_id = f"media_files_{uuid.uuid4().hex}"

    try:
        nm_ids = await service.upload_product_adds(
            product_id=product_id,
            files=files,
            user_id=user.user_id,
            replace=replace,
            start=start,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except Exception as e:
        logger.exception(f"Ошибка во время загрузки медиа из файлов: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

    return ProductUpdateSpecificationsResponse(
        message=f"Запрос на обновление медиа файлов принят в обработку",
        product_id=product_id,
        cards_for_update=[
            CardOperationResponse(
                task_id=task_id,
                status="queued",
                message="Запрос на обновление медиа по ссылкам принят в обработку",
                account="account",
                product_id=product_id,
                nm_id=nm,
                created_at=datetime.now(),
            )
            for nm in nm_ids
        ],
    )


@router.get("/wb/health", status_code=status.HTTP_200_OK)
async def get_product_wb_health(
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    size: int = Query(default=50, ge=1, le=10000, description="Размер страницы"),
    search: Optional[str] = Query(None, description="Поиск по артикулу или названию"),
    status: Optional[Literal["all", "has_error", "has_warning", "ok"]] = Query(
        "all", description="Фильтр по общему статусу товара"
    ),
    issue_type: IssueTypeFilter = Query(
        None, description="Фильтр по типам проблем (vat_mismatch, low_rating...)"
    ),
    account_id: Optional[list[int]] = Query(
        None, description="Фильтр по ID аккаунтов"
    ),
    sort_by: SortByParam = Query(default="product_id", description="Поле для сортировки"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Порядок сортировки"),

    service: ProductService = Depends(get_product_service),
    user: UserPermissions = Depends(get_info_from_token),
) -> ProductWBHealthResponse:
    """
    Возвращает список товаров с информацией о состоянии карточек на WB по аккаунтам.
    Позволяет фильтровать проблемы и пагинировать результат.
    """
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    params = ProductWBHealthQueryParams(
        page=page,
        size=size,
        search=search,
        status=status,
        issue_type=issue_type,
        account_ids=account_id,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return await service.get_products_wb_health_analitics(params)
