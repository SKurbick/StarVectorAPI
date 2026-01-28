from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from starlette import status

router = APIRouter(prefix="/analytics", tags=["Аналитика"])

@router.get("/warehouse/time-execution-delivery")
async def warehouse_time_execution_delivery(

):
    pass