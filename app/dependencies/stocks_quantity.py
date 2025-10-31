from fastapi import Request, Depends
from asyncpg import Pool

from fastapi import Body

from app.dependencies.card_status import get_card_status_service
from app.domain.models import EditQuantityValidationResult, UpdateStocksQuantityResponseModel
from app.repository.stocks_quantity import StocksQuantityRepository
from app.service.card_status import CardStatusService
from app.service.stocks_quantity import StocksQuantityService


example_edit_quantity = {
    "ХАЧАТРЯН": {"stocks": [{"amount": 748, "sku": "2040464284361"}, {"amount": 42, "sku": "2040464284385"}]},
    "ПИЛОСЯН": {"stocks": [{"amount": 8534, "sku": "2037786392119"}]}
}


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_stocks_quantity_repository(pool: Pool = Depends(get_pool)) -> StocksQuantityRepository:
    return StocksQuantityRepository(pool)


def get_stocks_quantity_service(repository: StocksQuantityRepository = Depends(get_stocks_quantity_repository)) -> StocksQuantityService:
    return StocksQuantityService(repository)


async def validate_edit_quantity_data(
    edit_data: dict[str, UpdateStocksQuantityResponseModel] = Body(example=example_edit_quantity),
    card_status_service: CardStatusService = Depends(get_card_status_service),
) -> EditQuantityValidationResult:
    """
    Возвращает:
    {
        "allowed": Dict[str, UpdateStocksQuantityResponseModel],
        "forbidden": Dict[str, List[str]]  # account → [barcode, ...]
    }
    """
    allowed: dict[str, list] = {}
    forbidden: dict[str, list] = {}

    all_barcodes = [item.sku for account_data in edit_data.values() for item in account_data.stocks]

    if not all_barcodes:
        return {"allowed": {}, "forbidden": {}}

    allowed_barcodes, forbidden_barcodes = await card_status_service.get_stocks_editable_barcodes(all_barcodes)
    allowed_set = set(allowed_barcodes)
    forbidden_set = set(forbidden_barcodes)

    for account, account_data in edit_data.items():
        allowed_items = []
        forbidden_list = []

        for item in account_data.stocks:
            if item.sku in allowed_set:
                allowed_items.append(item)
            elif item.sku in forbidden_set:
                forbidden_list.append(item.sku)
            else:
                forbidden_list.append(item.sku)

        if allowed_items:
            allowed[account] = allowed_items

        if forbidden_list:
            forbidden[account] = forbidden_list


    allowed_validated = {
        acc: UpdateStocksQuantityResponseModel(stocks=items)
        for acc, items in allowed.items()
    }

    return EditQuantityValidationResult(
        allowed=allowed_validated,
        forbidden=forbidden
    )
