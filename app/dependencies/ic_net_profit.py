from asyncpg import Pool
from fastapi import Depends, Request

from app.repository.ic_net_profit import ICNetProfitRepository
from app.service.ic_net_profit_service import ICNetProfitService


def get_pool(request: Request) -> Pool:
    return request.app.state.pool

def get_ic_net_profit_repository(pool: Pool = Depends(get_pool)) -> ICNetProfitRepository:
    return ICNetProfitRepository(pool)

def get_ic_net_profit_service(repository: ICNetProfitRepository = Depends(get_ic_net_profit_repository)) -> ICNetProfitService:
    return ICNetProfitService(repository)