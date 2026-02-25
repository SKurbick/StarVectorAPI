from collections import defaultdict
from typing import Optional, Union

from aiohttp import ClientSession

from app.domain.models import (
    WBSubjectWithCharcs,
    WBColor,
    WBCountry,
    WBBrand,
    ProductCharcInfo,
    WBCharc,
    ProductWBCharc,
)

from app.repository.wb_parent_categories import WBParentCategoryRepository, WBParentCategory
from app.repository.products_data import ProducsDataRepository
from app.repository.wb_charcs import WBCharcRepository
from app.repository.wb_subjects import WBSubjectRepository, WBParentCategoryWithSubjects
from app.infrastructure.API.wildberries.content.wb_charcs import CharcsWBAPI

from app.service.marketplace_cards import MarketplaceCardsService


DEFAULT_ACCOUNT_NAME = "Вектор"


class WBParentCategoryService:
    """Сервис для родительских категорий Wildberies."""

    def __init__(
            self,
            repo: WBParentCategoryRepository,
            marketplace_cards_service: MarketplaceCardsService,
    ):
        self.repo = repo
        self.marketplace_cards_service = marketplace_cards_service

    async def get_all_categories(self) -> list[WBParentCategory]:
        """Метод возвращает все родительские категории."""
        return await self.marketplace_cards_service.get_all_categories()


class WBSubjectService:
    """Сервис для предметов Wildberies."""

    def __init__(
            self,
            repo: WBSubjectRepository,
            marketplace_cards_service: MarketplaceCardsService,
    ):
        self.repo = repo
        self.marketplace_cards_service = marketplace_cards_service

    async def get_subjects_by_filters(
            self,
            parent_id: Optional[int] = None,
    ) -> list[WBParentCategoryWithSubjects]:
        """
        Метод возвращает все предметы.
        
        Args:
            parent_id: id родительской категории.
        """
        return await self.marketplace_cards_service.get_subjects_by_filters(parent_id)


class WBCharcService:
    """Сервис для характеристик предметов Wildberies."""

    def __init__(
            self,
            charc_repo: WBCharcRepository,
            subject_repo: WBSubjectRepository,
            products_data_repo: ProducsDataRepository,
            marketplace_cards_service: MarketplaceCardsService,
            session: ClientSession
    ):
        self._charc_repo = charc_repo
        self._subject_repo = subject_repo
        self._products_data_repo = products_data_repo
        self._marketplace_cards_service = marketplace_cards_service
        self._wb_client = CharcsWBAPI(
            session=session,
            account_name=DEFAULT_ACCOUNT_NAME
        )

    async def get_charcs_by_subject_id(self, subject_id: int) -> WBSubjectWithCharcs:
        """
        Метод возвращает параметры характеристик предмета.

        Args:
            subject_id: id предмета.
        """
        return await self._marketplace_cards_service.get_charcs_by_subject_id(subject_id)

    async def get_colors(self) -> list[WBColor]:
        """Метод возвращает возможные значения характеристики предмета Цвет."""
        return await self._marketplace_cards_service.get_colors()

    async def get_kinds(self) -> list[str]:
        """Метод возвращает возможные значения характеристики предмета Пол."""
        return await self._marketplace_cards_service.get_kinds()

    async def get_countries(self) -> list[WBCountry]:
        """Метод возвращает возможные значения характеристики предмета Страна производства."""
        return await self._marketplace_cards_service.get_countries()

    async def get_seasons(self) -> list[str]:
        """Метод возвращает возможные значения характеристики предмета Сезон."""
        return await self._marketplace_cards_service.get_seasons()

    async def get_vat(self) -> list[str]:
        """Метод возвращает возможные значения характеристики предмета Ставка НДС."""
        return await self._marketplace_cards_service.get_vat()

    async def get_brands(self, subject_id: int, limit: int = 1, offset: int = 0) -> list[WBBrand]:
        """
        Метод возвращает список брендов по ID предмета.

        Args:
            subject_id: id предмета.
        """
        return await self._marketplace_cards_service.get_brands(subject_id, limit, offset)

    async def get_product_charcs(self, product_id) -> list[ProductCharcInfo]:
        """
        Получить текущие характеристики товара.
        
        Метод возвращает заполненные и незаполненные характеристики.
        """
        products_data = await self._products_data_repo.get(product_id)

        if not products_data:
            raise ValueError(f"Товар с {product_id=} не найден.")

        subject_id = products_data.wb_subject_id
        all_subject_charcs = []

        if subject_id:
            subject_charcs_response = await self.get_charcs_by_subject_id(subject_id)
            all_subject_charcs = subject_charcs_response.charcs if subject_charcs_response else []

        current_charcs = await self._charc_repo.get_charcs_by_product_id(product_id)

        current_charcs_dict = {c.id: c for c in current_charcs}
        available_charc_ids = {c.id for c in all_subject_charcs}
        results_charcs_info: list[ProductCharcInfo] = []

        for subject_charc in all_subject_charcs:
            current = current_charcs_dict.get(subject_charc.id)
            is_valid, messages, suggestions = self._validate_characteristic(
                subject_charc, current
            )

            if current and current.value is not None:
                is_filled = True

                if is_valid:
                    status = "valid"
                else:
                    status = "invalid"
            else:
                is_filled = False

                if subject_charc.required:
                    status = "invalid"
                else:
                    status = "empty"

            charc_info = ProductCharcInfo(
                id=subject_charc.id,
                name=subject_charc.name,
                unit_name=subject_charc.unit_name,
                max_count=subject_charc.max_count,
                required=subject_charc.required,
                popular=subject_charc.popular,
                charc_type=subject_charc.charc_type,
                value=current.value if current else None,
                status=status,
                is_filled=is_filled,
                messages=messages,
                suggestions=suggestions,
            )
            results_charcs_info.append(charc_info)

        for charc_id, current in current_charcs_dict.items():
            if charc_id not in available_charc_ids:
                charc_info = ProductCharcInfo(
                    id=current.id,
                    name=current.name,
                    unit_name=current.unit_name,
                    max_count=current.max_count,
                    required=current.required,
                    popular=current.popular,
                    charc_type=current.charc_type,
                    value=current.value,
                    status="invalid",
                    is_filled=True,
                    is_required=False,
                    messages=["Характеристика больше не доступна для этого предмета"],
                    suggestions=["Удалите эту характеристику из карточки товара"]
                )
                results_charcs_info.append(charc_info)

        # Сортировка: 
        # сначала невалидные, потом обязательные пустые, 
        # популярные пустые, пустые,
        # потом валидные
        results_charcs_info.sort(key=lambda x: (
            0 if x.status == "invalid" else 1,
            0 if not x.is_filled and x.required else 1,
            0 if x.status == "empty" and x.popular else 1,
            0 if x.status == "empty" else 1,
            0 if x.required else 1,
            0 if x.popular else 1,
            x.name
        ))

        return results_charcs_info

    @classmethod
    def _validate_characteristic(
        cls,
        subject_charc: WBCharc,
        product_charc: Optional[ProductWBCharc]
    ) -> tuple[bool, list[str], list[str]]:
        """
        Валидация характеристики.

        Возвращает:
            (is_valid, messages, suggestions)
        """
        if not product_charc or product_charc.value is None:
            # Пустое значение - валидно только если характеристика необязательная
            if subject_charc.required:
                return False, ["Обязательная характеристика не заполнена"], [
                    f"Заполните характеристику '{subject_charc.name}'"
                ]
            return True, [], []
        
        messages = []
        suggestions = []
        is_valid = True

        # Валидация типа данных
        type_valid, type_msg, type_sugg = cls._validate_type(
            subject_charc.charc_type,
            product_charc.value
        )

        if not type_valid:
            is_valid = False
            messages.append(type_msg)
            suggestions.extend(type_sugg)

        # Валидация количества значений для списков
        if isinstance(product_charc.value, list):
            count_valid, count_msg, count_sugg = cls._validate_count(
                len(product_charc.value),
                subject_charc.max_count
            )
            if not count_valid:
                is_valid = False
                messages.append(count_msg)
                suggestions.extend(count_sugg)

        return is_valid, messages, suggestions

    @staticmethod
    def _validate_type(
        expected_type: str,
        value: Union[list[str], int, float]
    ) -> tuple[bool, str, list[str]]:
        """Валидация соответствия типа значения ожидаемому типу характеристики."""
        type_mapping = {
            "array_of_str": list,
            "number": (int, float),
        }

        expected_python_type = type_mapping.get(expected_type)

        if expected_python_type is None:
            return True, "", []

        if not isinstance(value, expected_python_type):
            actual_type = type(value).__name__
            return False, (
                f"Неверный тип значения: ожидается {expected_type}, "
                f"получено {actual_type}"
            ), [
                f"Измените тип значения на {expected_type}"
            ]

        if expected_type == "array_of_str" and isinstance(value, list):
            invalid_items = [v for v in value if not isinstance(v, str)]
    
            if invalid_items:
                return False, (
                    f"В списке есть элементы не строкового типа: {invalid_items}"
                ), [
                    "Все элементы списка должны быть строками"
                ]

        return True, "", []

    @staticmethod
    def _validate_count(
        actual_count: int,
        max_count: int
    ) -> tuple[bool, str, list[str]]:
        """Валидация количества значений в списке."""
        if actual_count > max_count:
            return False, (
                f"Превышено максимальное количество значений: "
                f"{actual_count} из {max_count}"
            ), [
                f"Оставьте не более {max_count} значений"
            ]

        return True, "", []
