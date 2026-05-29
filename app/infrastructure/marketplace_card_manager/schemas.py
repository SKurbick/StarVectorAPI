from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator, ConfigDict


class AccountCardData(BaseModel):
    nm_ids: Annotated[list[int], Field(example=[111222333, 444555666], description="Артикулы карточек")]


class CardDataByAccountRequest(BaseModel):
    accounts: Annotated[dict[str, AccountCardData] | None, Field(
        description="Словарь где ключ - имя аккаунта, значение - данные карточек",
        example={
            "account_1": {
                "nm_ids": [111222333, 444555666]
            },
            "account_2": {
                "nm_ids": [111222333, 444555666]
            }
        }
    )] = None
    local_vendor_codes: Annotated[list[str] | None, Field(example=["wild123", "wild456"], description="id товаров")] = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if not self.accounts and not self.local_vendor_codes:
            raise ValueError("Необходимо указать 'accounts' или 'wild_ids'.")

        return self


class CloseCardPreviewRequest(CardDataByAccountRequest):
    pass


class OpenCardsRequest(CardDataByAccountRequest):
    pass


class CloseCardsRequest(BaseModel):
    preview_operation_id: str = Field(..., description="operation_id из /preview")


class WarehouseFBWStock(BaseModel):
    warehouse_name: str
    quantity: int


class PreviewCardSummary(BaseModel):
    nm_id: int
    local_vendor_code: str | None = None
    account: str
    current_status: str
    current_virtual_stock: int
    warehouses: list[WarehouseFBWStock]
    will_be_closed: bool
    reason_to_skip: str | None = None


class ClosePreviewResponse(BaseModel):
    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    summary: dict[str, list[PreviewCardSummary]]
    stats: dict[
        Literal["total", "to_close", "already_closed", "invalid", "no_stock"],
        int
    ]
    details: dict[
        Literal["invalid_nm_ids", "invalid_local_codes"],
        list[Union[int, str]]
    ]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "operation_id": "cb7041cf-0b5c-45a5-9c9e-b4ca02f9cfd3",
                    "timestamp": "2025-11-12T10:04:42.105207",
                    "summary": {
                        "ЛОПАТИНА": [
                            {
                                "nm_id": 191919180,
                                "local_vendor_code": "wild123",
                                "account": "ЛОПАТИНА",
                                "current_status": "active",
                                "current_virtual_stock": 3,
                                "warehouses": [],
                                "will_be_closed": True,
                                "reason_to_skip": None
                            }
                        ],
                        "СТАРТ": [
                            {
                                "nm_id": 181818693,
                                "local_vendor_code": "wild123",
                                "account": "СТАРТ",
                                "current_status": "active",
                                "current_virtual_stock": 2,
                                "warehouses": [
                                {
                                    "warehouse_name": "Всего находится на складах",
                                    "quantity": 1
                                },
                                {
                                    "warehouse_name": "Самара (Новосемейкино)",
                                    "quantity": 1
                                }
                                ],
                                "will_be_closed": True,
                                "reason_to_skip": None
                            }
                        ],
                        "ТОНОЯН": [
                            {
                                "nm_id": 202020031,
                                "local_vendor_code": "wild123",
                                "account": "ТОНОЯН",
                                "current_status": "active",
                                "current_virtual_stock": 4,
                                "warehouses": [
                                {
                                    "warehouse_name": "В пути до получателей",
                                    "quantity": 2
                                }
                                ],
                                "will_be_closed": True,
                                "reason_to_skip": None
                            }
                        ],
                        "ХАЧАТРЯН": [
                            {
                                "nm_id": 110711529,
                                "local_vendor_code": "wild123",
                                "account": "ХАЧАТРЯН",
                                "current_status": "active",
                                "current_virtual_stock": 1,
                                "warehouses": [],
                                "will_be_closed": True,
                                "reason_to_skip": None
                            }
                        ]
                    },
                    "stats": {
                        "total": 4,
                        "to_close": 4,
                        "already_closed": 0,
                        "invalid": 0,
                        "no_stock": 0
                    },
                    "details": {
                        "invalid_nm_ids": [111111222, 5566778987],
                        "invalid_local_codes": [
                            "wild456"
                        ]
                    }
                }
            ]
        }
    )


class ClosedCardResult(BaseModel):
    nm_id: int
    account: str
    old_status: str
    new_status: str
    success: bool
    error: str | None = None


class CloseOperationResponse(BaseModel):
    operation_id: str
    timestamp: datetime
    status: Literal["accepted", "partial", "failed"]
    summary: dict[str, list[ClosedCardResult]]
    stats: dict[
        Literal["total_requested", "successfully_queued", "already_closed", "failed_db"],
        int
    ]
    celery_task_ids: list[str] = Field(validation_alias="task_ids")
    details: dict[
        Literal["failed_accounts"],
        list[Union[int, str, dict]]
    ]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "operation_id": "be0524ad-45d5-4323-9335-c5aa35d9d484",
                    "timestamp": "2025-11-12T10:14:59.250849",
                    "status": "accepted",
                    "summary": {
                        "ЛОПАТИНА": [
                            {
                                "nm_id": 191919180,
                                "account": "ЛОПАТИНА",
                                "old_status": "active",
                                "new_status": "closing_pending",
                                "success": True,
                                "error": None
                            }
                        ],
                        "СТАРТ": [
                            {
                                "nm_id": 181818693,
                                "account": "СТАРТ",
                                "old_status": "active",
                                "new_status": "closing_pending",
                                "success": True,
                                "error": None
                            }
                        ],
                        "ТОНОЯН": [
                            {
                                "nm_id": 202020031,
                                "account": "ТОНОЯН",
                                "old_status": "active",
                                "new_status": "closing_pending",
                                "success": True,
                                "error": None
                            }
                        ],
                        "ХАЧАТРЯН": [
                            {
                                "nm_id": 110711529,
                                "account": "ХАЧАТРЯН",
                                "old_status": "active",
                                "new_status": "closing_pending",
                                "success": True,
                                "error": None
                            }
                        ]
                    },
                    "stats": {
                        "total_requested": 4,
                        "successfully_queued": 4,
                        "already_closed": 0,
                        "failed_db": 0
                    },
                    "celery_task_ids": [],
                    "details": {
                        "failed_accounts": []
                    }
                }
            ]
        }
    )
