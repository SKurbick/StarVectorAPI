from typing import Optional

from fastapi import APIRouter, Query, Path, status, Depends, HTTPException

from app.domain.models import (
    WBSubjectWithCharcs,
    WBColor,
    WBCountry,
    WBBrand,
    WBParentCategory,
    WBParentCategoryWithSubjects,
    UserPermissions,
)
from app.domain.enums import PredefinedWBCharcEnum
from app.service.wb_specifications import WBCharcService, WBParentCategoryService, WBSubjectService
from app.dependencies import (
    get_wb_charc_service,
    get_wb_subject_service,
    get_wb_parent_category_service,
    get_info_from_token,
)
from app.dependencies.marketplace_cards import MarketplaceCardsService, get_marketplace_cards_service

router = APIRouter(prefix="/wb/specifications", tags=["Категории, предметы и характеристики Wildberies"])
categories_router = APIRouter(prefix="/categories")
subjects_router = APIRouter(prefix="/subjects")
charcs_router = APIRouter(prefix="/charcs")


@charcs_router.get("/list/{subject_id}", status_code=status.HTTP_200_OK, description="""
    **Получить доступные характеристики по ID предмета.**
""")
async def get_charcs_by_subject_id(
        subject_id: int = Path(..., gt=0, description="id предмета"),
        # user: UserPermissions = Depends(get_info_from_token),
        service: WBCharcService = Depends(get_wb_charc_service)
) -> WBSubjectWithCharcs:
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_charcs_by_subject_id(subject_id=subject_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@charcs_router.get("/colors", status_code=status.HTTP_200_OK, description="""
    **Получить возможные значения характеристики предмета `Цвет`.**
""")
async def get_colors(
        # user: UserPermissions = Depends(get_info_from_token),
        service: WBCharcService = Depends(get_wb_charc_service),
) -> list[WBColor]:
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_colors()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
            )


@charcs_router.get("/kinds", status_code=status.HTTP_200_OK, description="""
    **Получить возможные значения характеристики предмета `Пол`.**
""")
async def get_kinds(
        # user: UserPermissions = Depends(get_info_from_token),
        service: WBCharcService = Depends(get_wb_charc_service),
) -> list[str]:
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_kinds()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@charcs_router.get("/countries", status_code=status.HTTP_200_OK, description="""
    **Получить возможные значения характеристики предмета `Страна производства`.**
""")
async def get_countries(
        # user: UserPermissions = Depends(get_info_from_token),
        service: WBCharcService = Depends(get_wb_charc_service),
) -> list[WBCountry]:
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_countries()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@charcs_router.get("/seasons", status_code=status.HTTP_200_OK, description="""
    **Получить возможные значения характеристики предмета `Сезон`.**
""")
async def get_seasons(
        # user: UserPermissions = Depends(get_info_from_token),
        service: WBCharcService = Depends(get_wb_charc_service),
) -> list[str]:
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_seasons()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@charcs_router.get("/vat", status_code=status.HTTP_200_OK, description="""
    **Получить возможные значения характеристики предмета `Ставка НДС`.**
""")
async def get_vat(
        # user: UserPermissions = Depends(get_info_from_token),
        service: WBCharcService = Depends(get_wb_charc_service),
) -> list[str]:
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_vat()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@charcs_router.get("/brands/{subject_id}", status_code=status.HTTP_200_OK, description="""
    **Получить список брендов по ID предмета.**
""")
async def get_brands(
        subject_id: int = Path(..., gt=0, description="id предмета"),
        limit: int = Query(1, ge=1, description="Лимит значений"),
        offset: int = Query(0, ge=0, description="Пропустить значения"),
        # user: UserPermissions = Depends(get_info_from_token),
        service: WBCharcService = Depends(get_wb_charc_service),
) -> list[WBBrand]:
    # if not user.viewing:
        # raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_brands(subject_id=subject_id, limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@charcs_router.get("/predifined", status_code=status.HTTP_200_OK, description="""
    **Получить id характеристик, по которым можно получить доступные значения.**
""")
async def get_predifined_charc_ids(
        # user: UserPermissions = Depends(get_info_from_token),
        service: MarketplaceCardsService = Depends(get_marketplace_cards_service),
) -> dict[str, PredefinedWBCharcEnum]:
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_predifined_charc_ids()


@categories_router.get("/", status_code=status.HTTP_200_OK, description="""
    **Получить все родительские категории.**
""")
async def get_all_categories(
        # user: UserPermissions = Depends(get_info_from_token),
        service: WBParentCategoryService = Depends(get_wb_parent_category_service),
) -> list[WBParentCategory]:
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_all_categories()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )

@subjects_router.get("/", status_code=status.HTTP_200_OK, description="""
    **Получить все предметы.**
""")
async def get_subjects_by_filters(
        parent_id: Optional[int] = Query(None, gt=0, description="id родительской категории предметов"),
        # user: UserPermissions = Depends(get_info_from_token),
        service: WBSubjectService = Depends(get_wb_subject_service),
) -> list[WBParentCategoryWithSubjects]:
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_subjects_by_filters(parent_id=parent_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )

router.include_router(categories_router)
router.include_router(subjects_router)
router.include_router(charcs_router)
