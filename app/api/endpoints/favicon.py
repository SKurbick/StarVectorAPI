from fastapi import APIRouter
from starlette.responses import RedirectResponse, FileResponse

from fastapi.staticfiles import StaticFiles

router = APIRouter(tags=["favicon file"])

router.mount("/static", StaticFiles(directory="static"), name="static")


@router.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")
