from typing import Annotated

from fastapi import APIRouter, Depends, Query

from dependencies.sopost import get_sopost_service
from domain.shemas.sopost import SubjectsResponse
from service.sopost import SopostService


router = APIRouter(prefix="/sopost", tags=["Sopost"])


@router.get("/")
async def get_sopost_items(
    service: Annotated[SopostService, Depends(get_sopost_service)],
    limit: Annotated[int, Query(ge=1)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SubjectsResponse]:
    return await service.get_sopost_items(
        limit=limit,
        offset=offset,
    )
