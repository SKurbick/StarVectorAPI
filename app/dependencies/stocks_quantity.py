from collections import defaultdict

from fastapi import Request, Depends, Body
from asyncpg import Pool


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


def get_stocks_quantity_service(
        repository: StocksQuantityRepository = Depends(get_stocks_quantity_repository),
        card_data_service: CardDataService = Depends(get_card_data_service),
    ) -> StocksQuantityService:
    return StocksQuantityService(repository, card_data_service)


async def validate_edit_quantity_data(
    edit_data: dict[str, UpdateStocksQuantityResponseModel] = Body(...),
    card_status_service: CardStatusService = Depends(get_card_status_service),
    card_data_service: CardDataService = Depends(get_card_data_service),
) -> EditQuantityValidationResult:
    all_barcodes: dict[set[str]] = {}

    for acc, skus_data in edit_data.items():
        skus = {item.sku for item in skus_data.stocks}

        if not skus:
            continue

        if not acc in all_barcodes:
            all_barcodes[acc] = set()

        all_barcodes[acc].update(skus)

    if not all_barcodes:
        return EditQuantityValidationResult(allowed={}, invalid={}, closed_with_nonzero={})

    barcodes_nm_ids = await card_data_service.get_article_ids_by_barcodes(all_barcodes)

    all_nm_ids = set()

    for _, barcodes in barcodes_nm_ids.items():
        all_nm_ids.update(barcodes.values())

    cards_statuses = await card_status_service.get_status_by_nm_ids(list(all_nm_ids)) if all_nm_ids else {}

    allowed_items_by_account = defaultdict(list)
    invalid_barcodes_by_account = defaultdict(list)
    closed_with_nonzero_by_account = defaultdict(list)

    for account, account_data in edit_data.items():
        acc_nm_ids = barcodes_nm_ids.get(acc, {})

        for item in account_data.stocks:
            barcode = item.sku
            nm_id = acc_nm_ids.get(barcode)

            if nm_id is None:
                invalid_barcodes_by_account[account].append(barcode)
                continue

            status = cards_statuses.get(nm_id, "active")
            is_closed = status != CardStatusEnum.active

            if not is_closed or item.amount == 0:
                allowed_items_by_account[account].append(item)
            else:
                closed_with_nonzero_by_account[account].append(barcode)

    allowed = {
        acc: UpdateStocksQuantityResponseModel(stocks=items)
        for acc, items in allowed_items_by_account.items()
    }

    return EditQuantityValidationResult(
        allowed=allowed,
        invalid=invalid_barcodes_by_account,
        closed_with_nonzero=closed_with_nonzero_by_account,
    )
