from app.domain.models import UseCaseMetadata

# список сценариев по управлению карточками товаров
MANAGE_CARD_UC_REGISTRY = [
        UseCaseMetadata(
            title="Закрытие карточки",
            name="close_card",
            description="Закрывает карточку: запрещает редактирование остатков и обнуляет виртуальные остатки на маркетплейсе.",
            settings_schema=None,
            example={"title": "close_card"}
        ),
        UseCaseMetadata(
            title="Открытие карточки",
            name="open_card",
            description="Открывает ранее закрытую карточку, разрешая редактирование остатков.",
            settings_schema=None,
            example={"title": "open_card"}
        ),
    ]
