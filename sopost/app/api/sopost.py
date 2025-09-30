from fastapi import APIRouter

from domain.shemas.sopost import SopostItemResponse


router = APIRouter(prefix="/sopost", tags=["Sopost"])


TEMP_DATA = [
    {
        "id": "wild1661",
        "name": "Овощерезка ручная слайсер многофункциональная",
        "is_active": True,
        "is_kit": False,
        "share_of_kit": False,
        "kit_components": {"testwild": 2, "testwild2": 1},
        "photo_link": "https://basket-26.wbbasket.ru/vol4851/part485102/485102399/images/tm/1.webp",
        "is_inventoried": None,
        "created_at": "2025-08-28 09:46:35.274+03:00",
    },
    {
        "id": "wild1625",
        "name": "Швабра с отжимом и ведром для мытья пола (CW006)",
        "is_active": True,
        "is_kit": False,
        "share_of_kit": False,
        "kit_components": None,
        "photo_link": None,
        "is_inventoried": None,
        "created_at": "2025-09-05T13:15:05.003+03:00",
    },
]


@router.get("/")
async def get_sopost_items() -> list[SopostItemResponse]:
    return TEMP_DATA
