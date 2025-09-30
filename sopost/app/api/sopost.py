from fastapi import APIRouter


router = APIRouter(prefix="/sopost", tags=["Sopost"])


@router.get("/")
async def get_products_data() -> dict:
    return {
        "message": "some_data"
    }
