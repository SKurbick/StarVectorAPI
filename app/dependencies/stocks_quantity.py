from fastapi import Request, Depends
from asyncpg import Pool

from fastapi import Body

from app.dependencies.card_status import get_card_status_service
from app.dependencies.card_data import get_card_data_service
from app.domain.models import EditQuantityValidationResult, UpdateStocksQuantityResponseModel
from app.domain.enums import CardStatusEnum
from app.repository.stocks_quantity import StocksQuantityRepository
from app.service.card_status import CardStatusService
from app.service.card_data import CardDataService
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
    card_data_service: CardDataService = Depends(get_card_data_service),
) -> EditQuantityValidationResult:
    """
    Возвращает разрешённые и запрещённые к редактированию баркоды.
    Запрещены: карточки со статусами 'closed' и 'closing_pending'.
    """

    all_barcodes = []

    for account_data in edit_data.values():
        for item in account_data.stocks:
            all_barcodes.append(item.sku)

    all_barcodes = list(set(all_barcodes))

    if not all_barcodes:
        return EditQuantityValidationResult(allowed={}, forbidden={})

    barcode_to_nm = await card_data_service.get_article_ids_by_barcodes(all_barcodes)

    nm_ids = list(set(barcode_to_nm.values())) if barcode_to_nm else []
    nm_to_status = await card_status_service.get_status_by_nm_ids(nm_ids)

    allowed_barcodes = set()
    forbidden_barcodes = set()
    forbidden_statuses = {CardStatusEnum.closed, CardStatusEnum.closing_pending}

    for barcode in all_barcodes:
        nm_id = barcode_to_nm.get(barcode)

        if nm_id is None:
            forbidden_barcodes.add(barcode)
            continue

        status = nm_to_status.get(nm_id)

        if status in forbidden_statuses:
            forbidden_barcodes.add(barcode)
        else:
            allowed_barcodes.add(barcode)

    allowed = {}
    forbidden = {}

    for account, account_data in edit_data.items():
        allowed_items = []
        forbidden_list = []

        for item in account_data.stocks:
            if item.sku in allowed_barcodes:
                allowed_items.append(item)
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
