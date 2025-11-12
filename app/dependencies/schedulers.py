from fastapi import Header, HTTPException, status

from app.config.settings import settings


async def verify_scheduler_api_key(x_api_key: str = Header(None)):
    if x_api_key != settings.SCHEDULER_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
