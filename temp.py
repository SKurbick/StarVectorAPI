# from datetime import datetime
# import logging
# import uuid

# from aiohttp import ClientSession
# from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
# from starlette import status

# from app.dependencies import (
#     get_info_from_token,
#     get_wb_http_session,
# )
# from app.domain.models import (
#     DuplicateWBProductCardRequest,
#     DuplicateCardToAccountsRequest,
#     DuplicateWBProductCardResponse,
#     DuplicateCardToAccountsResponse,
#     UserPermissions,
#     WBCardSpecificationUpdateRequest,
#     WBCardUploadRequest,
#     CardOperationResponse,
#     CardWBMediaLinksUpdate,
# )
# from app.service.wb_card_duplicate import WildberriesCardsDuplicateService
# from app.service.wb_card_create import WBCardCreateService
# from app.service.wb_card_update import WBCardUpdateService
# from app.service.wb_media import WBMediaService
# from app.service.wb_media import WBMediaService
# from app.infrastructure.API.wildberries.content.wb_cards import CardsWBAPI




# @router.post("/wb/duplicate", description="Создание дубликата карточки товара на WB.")
# async def duplicate_wb_card(
#     data: DuplicateWBProductCardRequest,
#     # user: UserPermissions = Depends(get_info_from_token),
#     service: WildberriesCardsDuplicateService = Depends(get_wb_cards_duplicate_service),
#     session: ClientSession = Depends(get_wb_http_session),
# ) -> DuplicateWBProductCardResponse:
#     """Создать дубликат карточки товара."""
#     # if not user.viewing:
#     #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
#     try:
#         source_wb_client = CardsWBAPI(session=session, account_name=data.source_account)
#         # result = await service.duplicate_card(
#         #     wb_client=source_wb_client,
#         #     source_nm_id=data.nm_id,
#         #     sync_stocks=data.sync_stocks,
#         #     close_old=data.close_old_card,
#         # )
#         # return result
#     except ValueError as e:
#         logger.warning(f"Ошибка клиента при дублировании: {e}")
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
#     except Exception as e:
#         logger.exception(f"Непредвиденная ошибка в /wb/duplicate: {e}")
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error.")


# @router.post("/wb/duplicate-to-accounts", description="Создание дубликата карточки товара на других аккаунтах WB.")
# async def duplicate_wb_card_to_accounts(
#     data: DuplicateCardToAccountsRequest,
#     # user: UserPermissions = Depends(get_info_from_token),
#     service: WildberriesCardsDuplicateService = Depends(get_wb_cards_duplicate_service),
#     session: ClientSession = Depends(get_wb_http_session),
# ) -> DuplicateCardToAccountsResponse:
#     """Создать дубликат карточки товара на других аккаунтах."""
#     # if not user.viewing:
#     #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
#     try:
#         source_wb_client = CardsWBAPI(session=session, account_name=data.source_account)
#         # target_wb_clients = [
#         #     CardsWBAPI(
#         #         session=session,
#         #         account_name=account,
#         #     )
#         #     for account in set(data.target_accounts)
#         #     if account.lower() != data.source_account.lower()
#         # ]

#         # if not target_wb_clients:
#         #     raise ValueError("Не указаны аккаунты для создания дубликатов.")

#         # result = await service.duplicate_card_to_accounts(
#         #     source_wb_client=source_wb_client,
#         #     target_wb_clients=target_wb_clients,
#         #     sync_stocks=data.sync_stocks,
#         #     source_nm_id=data.nm_id,
#         # )
#         # return result
#     except ValueError as e:
#         logger.warning(f"Ошибка клиента при дублировании: {e}")
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
#     except Exception as e:
#         logger.exception(f"Непредвиденная ошибка в /wb/duplicate-to-accounts: {e}")
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

# @router.post(
#         "/wb/update",
#         status_code=status.HTTP_202_ACCEPTED,
#         description="Обновить информацию карточки товара на WB."
# )
# async def update_wb_card(
#     data: WBCardSpecificationUpdateRequest,
#     # user: UserPermissions = Depends(get_info_from_token),
#     service: WBCardUpdateService = Depends(get_wb_card_update_service),
# ) -> CardOperationResponse:
#     # if not user.viewing:
#     #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

#     task_id = f"update_{uuid.uuid4().hex}"
#     # try:
#     #     await service.update_card(data)
#     # except ValueError as e:
#     #     logger.warning(f"Ошибка клиента во время обновления карточки товара: {e}")
#     #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
#     # except Exception as e:
#     #     logger.exception(f"Непредвиденная ошибка в /wb/update: {e}")
#     #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

#     return CardOperationResponse(
#         task_id=task_id,
#         status="completed",
#         message="Карточка товара успешно обновлена",
#         account=data.account,
#         product_id=data.product_id,
#         nm_id=data.nm_id,
#         created_at=datetime.now()
#     )

# @router.post(
#         "/wb/upload", 
#         status_code=status.HTTP_202_ACCEPTED,
#         description="Создать карточку товара на WB."
# )
# async def upload_wb_card(
#     data: WBCardUploadRequest,
#     # user: UserPermissions = Depends(get_info_from_token),
#     service: WBCardCreateService = Depends(get_wb_card_create_service),
# ) -> CardOperationResponse:
#     # if not user.viewing:
#     #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

#     task_id = f"create_{uuid.uuid4().hex}"
#     # try:
#     #     nm_id = await service.create_card(data)
#     # except ValueError as e:
#     #     logger.warning(f"Ошибка клиента во время создания карточки товара: {e}")
#     #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
#     # except Exception as e:
#     #     logger.exception(f"Непредвиденная ошибка в /wb/upload: {e}")
#     #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

#     return CardOperationResponse(
#         task_id=task_id,
#         status="completed",
#         message="Карточка товара успешно создана",
#         account=data.account,
#         product_id=data.product_id,
#         # nm_id=nm_id,
#         nm_id=18071995,
#         created_at=datetime.now()
#     )

    # display_order: Optional[int] = Header(None, ge=1, description=(
    #     "Номер фото в списке фотографий. **Заменяет текущее фото или видео**.<br>"
    #     "Если не указать, или указать большее значение, чем всего фотографий,<br>"
    #     "файл будет добавлен в конец списка.<br>"
    #     "При загрузке видео указывать не требуется."
    # )),




# from datetime import datetime
# from typing import Annotated, Optional
# import logging
# import uuid

# from fastapi import APIRouter, Depends, Query, HTTPException, Path, UploadFile, File, Form, Header
# from starlette import status

# from app.dependencies import get_info_from_token, get_product_media_file_service, get_product_media_links_service, get_product_specifications_update_service
# from app.dependencies import get_product_service
# from app.domain.models import (
#     SubjectDataWithProductsResponse,
#     UserPermissions,
#     ProductWBCards,
#     ProductWBSpecificationResponse,
#     ProsuctWBSpecificationUpdate,
#     ProductUpdateSpecificationsResponse,
#     CardOperationResponse,
#     ProductWBMediaLinksUpdate,
# )
# from app.service.product import ProductService
# from app.service.wb_media import WBMediaService
# from app.service.wb_media import WBMediaService
# from app.service.product_specifications_update import ProductWBSpecificationsUpdateService


# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/products", tags=["Товары"])


# @router.get("/grouped_by_subjects", status_code=status.HTTP_200_OK)
# async def get_products_grouped_by_subjects(
#         service: Annotated[ProductService, Depends(get_product_service)],
#         limit: Annotated[int, Query(ge=1)] = 1000,
#         offset: Annotated[int, Query(ge=0)] = 0,
#         user: UserPermissions = Depends(get_info_from_token),
# ) -> list[SubjectDataWithProductsResponse]:
#     if not user.viewing:
#         raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
#     return await service.get_products_grouped_by_subjects(
#         limit=limit,
#         offset=offset,
#     )


# @router.get("/{id}/cards", status_code=status.HTTP_200_OK, description="""
#     **Получить все карточки товара**\n   
#     id: локальный артикул товара (wild).
# """)
# async def get_product_cards(
#         id: str = Path(..., description="Локальный артикул товара."),
#         # user: UserPermissions = Depends(get_info_from_token),
#         service: ProductService = Depends(get_product_service),
# ) -> ProductWBCards:
#     # if not user.viewing:
#     #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
#     try:
#         return await service.get_poduct_cards(product_id=id)
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error."
#         )


# @router.get("/{id}/wb/specifications", status_code=status.HTTP_200_OK, description="""
#     **Получить спецификации товара.**
#     id: локальный артикул товара (wild).
# """)
# async def get_product_wb_specifications(
#     id: str = Path(..., description="Локальный артикул товара."),
#     # user: UserPermissions = Depends(get_info_from_token),
#     service: ProductService = Depends(get_product_service),
# ) -> ProductWBSpecificationResponse:
#     # if not user.viewing:
#     #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
#     try:
#         return await service.get_product_wb_specifications(id)
#     except ValueError as e:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
#             detail=str(e)
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error."
#         )


# @router.post(
#         "/wb/specifications/update", 
#         status_code=status.HTTP_202_ACCEPTED,
#         description="**Обновить спецификации товара.**"
# )
# async def update_product_wb_specifications(
#     data: ProsuctWBSpecificationUpdate,
#     user: UserPermissions = Depends(get_info_from_token),
#     service: ProductWBSpecificationsUpdateService = Depends(get_product_specifications_update_service),
# ) -> ProductUpdateSpecificationsResponse:
#     if not user.viewing:
#         raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

#     task_id = f"update_{uuid.uuid4().hex}"
#     try:
#         updated_cards = await service.update_product_specifications(data)
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
#     except RuntimeError as e:
#         raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
#     except Exception:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

#     cards = [
#         CardOperationResponse(
#             task_id=task_id,
#             status="completed",
#             message="Карточка товара успешно обновлена",
#             account=item["account"],
#             product_id=data.id,
#             nm_id=item["nm_id"],
#             created_at=datetime.now(),
#         )
#         for item in updated_cards
#     ]

#     return ProductUpdateSpecificationsResponse(
#         message="Спецификации товара успешно обновлены.",
#         product_id=data.id,
#         cards_for_update=cards,
#     )