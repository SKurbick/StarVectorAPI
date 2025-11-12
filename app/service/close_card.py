import logging
from collections import defaultdict
from datetime import datetime
import json
from uuid import uuid4

from asyncpg import Pool
from fastapi import HTTPException, status

from app.domain.enums import CardStatusEnum
from app.domain.models import (
    CloseCardPreviewRequest,
    PreviewCardSummary,
    ClosePreviewResponse,
    WarehouseFBWStock,
    CloseCardsRequest,
)
from app.repository.article import ArticleRepository
from app.repository.card_status import CardStatusRepository
from app.repository.current_stocks import CurrentStocksRepository
from app.service.stock_movement import StockMovementService
from app.use_cases.card_use_cases import CloseCardUseCase
from redis.asyncio import Redis


logger = logging.getLogger(__name__)


class CloseCardService:
    """
    Сервис закрывает карточки и обнуляет остатки.
    """

    def __init__(self, pool: Pool, stock_movement_service: StockMovementService, redis_client: Redis):
        self.pool = pool
        self.stock_movement_service = stock_movement_service
        self.redis_client = redis_client

    async def close_cards(self, data: CloseCardsRequest):
        """
        Закрыть артикулы и обнулить остатки на маркетплейсе.
        """
        cache_key = f"close_cards_preview:{data.preview_operation_id}"
        cached = await self.redis_client.get(cache_key)

        if not cached:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Preview устарел (более 5 минут) или operation_id неверен"
            )

        try:
            preview_data = json.loads(cached)
            accounts_data: dict[str, list[int]] = preview_data["accounts"]
        except (KeyError, json.JSONDecodeError) as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Повреждённые данные preview: {e}"
            )

        card_closer = CloseCardUseCase(self.pool)
        result = await card_closer.execute(accounts_data, preview_operation_id=data.preview_operation_id)

        await self.redis_client.delete(cache_key)

        return result

    async def close_cards_preview(self, data: CloseCardPreviewRequest) -> ClosePreviewResponse:
        """
        Возвращает данные по артикулам, переданным к закрытию.
        """
        article_repo = ArticleRepository(self.pool)
        status_repo = CardStatusRepository(self.pool)
        stocks_repo = CurrentStocksRepository(self.pool)

        # Получаем article-данные
        articles, invalid_nm_ids, invalid_lvc = await article_repo.get_articles_by_criteria(
            nm_ids_by_account=(
                {acc: card_data.nm_ids for acc, card_data in data.accounts.items()}
                if data.accounts else {}
            ),
            local_vendor_codes=data.local_vendor_codes
        )

        # Группируем валидные по аккаунтам
        valid_by_account: dict[str, list[dict]] = defaultdict(list)
        nm_to_lvc: dict[int, str] = {}

        for art in articles:
            acc = art["account"]
            valid_by_account[acc].append(art)

            if art.get("local_vendor_code"):
                nm_to_lvc[art["nm_id"]] = art["local_vendor_code"]

        # Подготавливаем пары (nm_id, account)
        nm_acc_pairs = [(art["nm_id"], art["account"]) for art in articles]

        # Получаем статусы и остатки
        statuses = await status_repo.get_status_by_nm_and_account(nm_acc_pairs)
        stocks = await stocks_repo.get_fbs_stocks_by_nm_and_account(nm_acc_pairs)

        # Получаем данные из WB API (только валидные nm_id по аккаунтам)
        wb_request = {acc: [art["nm_id"] for art in arts] for acc, arts in valid_by_account.items()}
        wb_result = {}

        if wb_request:
            try:
                raw = await self.stock_movement_service.get_stock_movement(wb_request)
                wb_result = raw.get("result", {})
            except Exception as e:
                logger.warning(f"WB API error in preview: {e}")

        # Собираем ответ
        summary = defaultdict(list)
        stats = {"total": len(articles), "to_close": 0, "already_closed": 0, "invalid": len(invalid_nm_ids), "no_stock": 0}

        for art in articles:
            nm, acc = art["nm_id"], art["account"]
            key = (nm, acc)

            current_status = statuses.get(key, "active")
            current_stock = stocks.get(key, 0)
            lvc = nm_to_lvc.get(nm)

            wb_data = None

            if acc in wb_result and "data" in wb_result[acc]:
                wb_data = next((x for x in wb_result[acc]["data"] if x.get("nm_id") == nm), None)

            warehouses = []

            if wb_data and "warehouses" in wb_data:
                for wh in wb_data["warehouses"]:
                    warehouses.append(WarehouseFBWStock(
                        warehouse_name=wh.get("warehouseName", ""),
                        quantity=wh.get("quantity", 0)
                    ))

            will_be_closed = current_status != CardStatusEnum.closed
            reason_to_skip = None

            if current_status == CardStatusEnum.closed:
                stats["already_closed"] += 1
                reason_to_skip = "already_closed"
            elif will_be_closed:
                stats["to_close"] += 1
            else:
                reason_to_skip = "not_eligible"

            if current_stock == 0:
                stats["no_stock"] += 1

            summary[acc].append(PreviewCardSummary(
                nm_id=nm,
                local_vendor_code=lvc,
                account=acc,
                current_status=current_status,
                current_virtual_stock=current_stock,
                warehouses=warehouses,
                will_be_closed=will_be_closed,
                reason_to_skip=reason_to_skip,
            ))

        # кешируем данные для закрытия
        to_close_by_account = defaultdict(list)

        for items in summary.values():
            for item in items:
                to_close_by_account[item.account].append(item.nm_id)

        operation_id = str(uuid4())
        timestamp = datetime.now()

        try:
            cache_key = f"close_cards_preview:{operation_id}"
            ttl = 300

            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps({
                    "operation_id": operation_id,
                    "timestamp": timestamp.isoformat(),
                    "accounts": {acc: list(set(nms)) for acc, nms in to_close_by_account.items()}
                },  ensure_ascii=False)
            )
            logger.info(f"Записан кеш для '{self.close_cards_preview.__qualname__}', key: {cache_key}, ttl: {ttl}")
        except Exception as e:
            logger.warning(f"Ошибка установки кэша для ключа '{cache_key}': {e}")

        return ClosePreviewResponse(
            operation_id=operation_id,
            timestamp=timestamp,
            summary=summary,
            stats=stats,
            details={"invalid_nm_ids": invalid_nm_ids, "invalid_local_codes": invalid_lvc},
        )
