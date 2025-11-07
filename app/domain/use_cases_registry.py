from app.domain.models import CardUseCaseMetadata

# список сценариев по управлению карточками товаров
MANAGE_CARD_UC_REGISTRY = [
        CardUseCaseMetadata(
            title="Закрытие карточки",
            name="close_card",
            description="Закрывает карточку: запрещает редактирование остатков и обнуляет виртуальные остатки на маркетплейсе.",
            settings_schema=None,
            example={"title": "close_card"}
        ),
        CardUseCaseMetadata(
            title="Открытие карточки",
            name="open_card",
            description="Открывает ранее закрытую карточку, разрешая редактирование остатков.",
            settings_schema=None,
            example={"title": "open_card"}
        ),
    ]
