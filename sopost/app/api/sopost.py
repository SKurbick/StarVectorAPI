from fastapi import APIRouter


router = APIRouter(prefix="/sopost", tags=["Sopost"])


@router.get("/")
async def get_sopost_items() -> dict:
    return {
        "message": "some_data"
    }
