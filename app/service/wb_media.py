import logging
from typing import Optional

from aiohttp import ClientSession
import asyncio
from fastapi import UploadFile

from app.domain.models import (
    WBMedia,
    WBPhoto,
    ProductWBMediaLinksUpdate,
)
from app.domain.enums import CardStatusEnum
from app.infrastructure.API.wildberries.content.wb_cards import CardsWBAPI, Card
from app.infrastructure.API.wildberries.content.schemes.card_media import CardMediaUploadByLinks
from app.repository.article import ArticleRepository
from app.repository.wb_media import WBMediaRepository
from app.repository.card_data import CardDataRepository
from app.repository.product import ProductRepository
from app.repository.products_data import ProducsDataRepository
from app.service.card_status import CardStatusService


logger = logging.getLogger(__name__)


class WBMediaService:
    """Сервис для медиа карточек товаров на WB."""

    MAX_COUNT_PHOTOS_FOR_CARD = 30

    def __init__(
        self,
        products_repo: ProductRepository,
        products_data_repo: ProducsDataRepository,
        wb_media_repo: WBMediaRepository,
        article_repo: ArticleRepository,
        card_data_repo: CardDataRepository,
        card_status_service: CardStatusService,
        session: ClientSession,
    ):
        self._wb_media_repo = wb_media_repo
        self._article_repo = article_repo
        self._card_data_repo = card_data_repo
        self._products_repo = products_repo
        self._products_data_repo = products_data_repo
        self._card_status_service = card_status_service
        self._session = session

    async def upload_card_uniq_attrs(
            self,
            nm_id: int,
            is_video: bool,
            file: UploadFile,
            account: str | None = None,
            user_id: int | None = None,
    ):
        if is_video:
            return await self._upload_only_video(
                file=file,
                nm_id=nm_id,
                account=account,
                user_id=user_id,
            )

        return await self._upload_only_cover(
            file=file,
            nm_id=nm_id,
            account=account,
            user_id=user_id,
        )
    
    async def remove_card_video(
            self,
            nm_id: int,
            user_id: int | None = None,
    ) -> str:
        """
        Удалить видео из карточки товара на ВБ.
        """
        logger.info(f"Удаление видео из карточки {nm_id}...")
        account_data = await self._article_repo.get_accounts_by_nm_ids(nm_ids=[nm_id])

        if not account_data:
            message = f"Карточка {nm_id=} не найдена."
            logger.error(message)
            raise ValueError(message)
        
        target_account = next(iter(account_data.keys()))
        wb_client = CardsWBAPI(session=self._session, account_name=target_account)

        card: Card | None = None

        for _ in range(3):
            card = await wb_client.get_card(nm_id)

            if card:
                break

        if not card:
            message = f"Не удалось найти карточку {nm_id} в ЛК '{target_account.upper()}'."
            logger.error(message)
            raise ValueError(message)

        product_id = await self._get_product_id(nm_id=nm_id, account=target_account)
        cover = await self._wb_media_repo.get_cover_url_of_card(nm_id=nm_id)
        adds = await self._wb_media_repo.get_product_additionals(product_id=product_id)

        all_links = [cover] if cover else []
        all_links.extend([item.url for item in adds])

        logger.debug(f"Отправляем запрос на ВБ на удаление видео из карточки. [{target_account}|{nm_id}]")
        await wb_client.upload_media_by_links(
            CardMediaUploadByLinks(
                nm_id=nm_id,
                data=all_links,
            )
        )

        logger.debug(f"Удаляем ссылку на видео карточки в БД. [{target_account}|{nm_id}]")
        await self._wb_media_repo.update_video_of_card(
            article_id=nm_id,
            media_url=None,
            user_id=user_id,
        )

        logger.info(f"Удаление видео из карточки {nm_id} завершено.")
        return target_account

    async def _choose_adds_source_card(
            self, 
            product_id: str,
            user_id: int | None = None,
    ) -> tuple[str, Card]:
        """
        Выбрать карточку товара для хранения общих допников товара.
        """
        logger.info(f"Выбираем карточку для хранения допников товара {product_id}...")
        source_nm_id: int | None = None
        product_meta = await self._products_data_repo.get(product_id=product_id)

        if not product_meta:
            logger.debug(f"Нет метаданных товара {product_id}. Проверяем его наличие в БД.")
            product_is_exists = await self._products_repo.check_product_exists(product_id=product_id)

            if not product_is_exists:
                message = f"Товар с id={product_id} не найден."
                logger.error(message)
                raise ValueError(message)
            
            logger.debug(f"Сохраняем новые метаданные для товара {product_id}.")
            await self._products_data_repo.create(
                product_id=product_id,
                user_id=user_id,
            )

            product_meta = await self._products_data_repo.get(product_id=product_id)
        
        logger.debug(f"Получаем все карточки товара {product_id}...")
        articles, _, invalid_lvc = await self._article_repo.get_articles_by_criteria(local_vendor_codes=[product_id])
        if invalid_lvc or not articles:
            message = f"Для товара '{product_id}' не найдено карточек для хранения допников."
            logger.warning(message)
            raise ValueError(message)
        
        sorted_articles = sorted(articles, key=lambda x: (x["account"], x["nm_id"]))
        logger.debug(f"Получаем статусы всех карточек товара {product_id}...")
        article_statuses = await self._card_status_service.get_status_by_nm_ids(
            [a["nm_id"] for a in sorted_articles]
        )

        source_nm_id = product_meta.wb_adds_source_card
        target_card: tuple[str, Card] | None = None

        if source_nm_id:
            logger.debug(f"Текущая карточка для хранения допников товара {product_id}: {source_nm_id}")
            logger.debug(f"Статус карточки {source_nm_id}: {article_statuses.get(source_nm_id)}")
            if article_statuses.get(source_nm_id, "active") in {CardStatusEnum.active, CardStatusEnum.new}:
                current_article = next((a for a in sorted_articles if a["nm_id"] == source_nm_id), None)

                if current_article:
                    wb_client = CardsWBAPI(
                        session=self._session,
                        account_name=current_article["account"],
                    )

                    wb_card: Card | None = None
                    logger.debug(f"Получаем карточку товара {source_nm_id} с маркетплейса...")
                    for _ in range(3):
                        wb_card = await wb_client.get_card(current_article["nm_id"])

                        if wb_card:
                            break
                    
                    # если карточка на вб есть
                    if wb_card:
                        logger.debug(f"Карточка товара найдена: [{wb_client.account_name}|{wb_card.nm_id}]")
                        target_card = wb_client.account_name, wb_card

        if target_card:
            logger.info(f"Для товара {product_id} в качестве хранилища допников осталась текущая карточка.")
            return target_card
        
        logger.info(f"Не удалось получить текущее хранилище допников товара {product_id}. Выбираем новую.")
        current_adds_list = await self._wb_media_repo.get_product_additionals(product_id=product_id)
        first_valid_card: tuple[str, Card] | None = None

        for article in sorted_articles:
            if article["nm_id"] == source_nm_id:
                continue

            if not article_statuses.get(article["nm_id"], "active") in {CardStatusEnum.active, CardStatusEnum.new}:
                continue

            wb_client = CardsWBAPI(
                self._session,
                account_name=article["account"]
            )

            wb_card: Card | None = None

            for _ in range(3):
                wb_card = await wb_client.get_card(article["nm_id"])

                if wb_card:
                    break

            if not wb_card:
                continue

            if not first_valid_card:
                first_valid_card = wb_client.account_name, wb_card

            if current_adds_list:
                logger.debug(f"Проверяем карточку {wb_card.nm_id}, является ли текущим хранилищем допников товара {product_id}")
                target_link = current_adds_list[0].url
                photos = wb_card.photos or []
                all_card_urls = {ph["big"] for ph in photos}

                if target_link not in all_card_urls:
                    logger.debug(f"Карточка {wb_card.nm_id} не является текущим хранилищем допников товара {product_id}")
                    continue

                logger.info(f"Найдена карточка {wb_card.nm_id} в качестве текущего хранилища ссылок на допники товара {product_id}")
                target_card = wb_client.account_name, wb_card
                break

            # если нет ссылок на допники в БД
            logger.debug(f"Нет ссылок на допники для товара {product_id}.")
            if first_valid_card:
                logger.info(f"Выбираем первую валидную карточку {first_valid_card[1].nm_id} для хранения ссылок на допники товара {product_id}")
                target_card = first_valid_card
                break

        if not target_card and first_valid_card:
            target_card = first_valid_card

        if target_card:
            account, card = target_card
            logger.debug(f"Для товара {product_id} выбрана карточка для хранения ссылок: [{account}|{card.nm_id}]. Сохраняем в БД.")
            await self._products_data_repo.update_wb_specifications(
                product_id=product_id,
                adds_source_card=card.nm_id,
                user_id=user_id,
            )
            return target_card

        message = f"Для товара '{product_id}' не найдено валидных карточек для хранения допников."
        logger.warning(message)
        raise ValueError(message)


    async def _upload_video_to_card(
            self,
            wb_client: CardsWBAPI,
            nm_id: int,
            file_content: bytes,
            filename: str,
            content_type: str,
            user_id:  int | None = None,
    ):
        card: Card | None = None

        for _ in range(3):
            card = await wb_client.get_card(nm_id)

            if card:
                break

        if not card:
            logger.warning(f"Карточка не найдена: [{wb_client.account_name}:{nm_id}].")
            raise ValueError(f"Карточка не найдена: [{wb_client.account_name}:{nm_id}].")

        await self._send_video(
            wb_client=wb_client,
            nm_id=nm_id,
            file_content=file_content,
            filename=filename,
            content_type=content_type,
        )

        await self._ensure_card_video_state(
            wb_client=wb_client,
            nm_id=nm_id,
            has_video=True,
        )

        card: Card | None = None

        for _ in range(3):
            card = await wb_client.get_card(nm_id)

            if card:
                break

        if not card:
            logger.warning(f"Карточка не найдена: [{wb_client.account_name}:{nm_id}]. return None")
            return
        
        video = card.video

        await self._wb_media_repo.update_video_of_card(
            article_id=nm_id,
            media_url=video,
            user_id=user_id,
        )

        logger.info(f"Загрузка видео карточки завершена: [{wb_client.account_name}:{nm_id=}:{card.video=}]")

    async def upload_video_to_product_cards(
            self,
            product_id: str,
            file: UploadFile,
            force_upload: bool = False,
            user_id: int | None = None
    ) -> list[int]:
        """
        Загрузить видео на все карточки товара.
        """
        logger.info(f"Загружаем видео в карточки товара: {product_id=}|{force_upload=}")
        articles, _, invalid_lvc = await self._article_repo.get_articles_by_criteria(
            local_vendor_codes=[product_id]
        )

        if invalid_lvc or not articles:
            raise ValueError(f"Для товара '{product_id}' не найдено карточек.")
        
        update_tasks = []
        content = await file.read()
        card_statuses = await self._card_status_service.get_status_by_nm_ids(
            [a["nm_id"] for a in articles]
        )

        for item in articles:
            nm_id = item["nm_id"]
            account = item["account"]
            
            if card_statuses.get(nm_id) not in (CardStatusEnum.active, CardStatusEnum.new, None):
                continue

            current_video_url = await self._wb_media_repo.get_video_url_of_card(
                nm_id=nm_id,
            )

            wb_client = CardsWBAPI(session=self._session, account_name=account)

            if not current_video_url or force_upload:
                update_tasks.append(asyncio.create_task(
                    self._upload_video_to_card(
                        wb_client=wb_client,
                        nm_id=nm_id,
                        file_content=content,
                        filename=file.filename,
                        content_type=file.content_type,
                        user_id=user_id,
                    )
                ))

        results = await asyncio.gather(*update_tasks, return_exceptions=True)
        updated_nm_ids: list[int] = []

        for (res, article) in zip(results, articles):
            if isinstance(res, Exception):
                logger.exception(
                    f"Ошибка во время обновления медиа для карточки товара {product_id}-{article["nm_id"]}: {res}"
                )
                continue

            nm_id = article["nm_id"]
            updated_nm_ids.append(nm_id)

        if not updated_nm_ids:
            logger.warning(f"Нет обновленных карточек для сохранения допников товара {product_id=}")
            return []

        return updated_nm_ids

    async def upload_product_adds(
            self,
            product_id: str,
            files: list[UploadFile],
            user_id: int | None = None,
            replace: bool = False,
            start: int = -1,
    ) -> list[int]:
        """Загрузить дополнительные фотографии для всех карточек товаров в указанном порядке."""
        logger.info(f"Загрузка файлов (допники) для товара {product_id}...")

        if not files:
            logger.warning(f"Нет файлов для загрузки: {product_id=}")
            return []

        # список допников до обновления (текущее состояние)
        old_adds_list = await self._wb_media_repo.get_product_additionals(product_id=product_id)
        account, main_card = await self._choose_adds_source_card(product_id=product_id, user_id=user_id)
        main_wb_client = CardsWBAPI(
            session=self._session,
            account_name=account
        )

        main_cover = await self._wb_media_repo.get_cover_url_of_card(main_card.nm_id)
        has_cover = 1 if main_cover else 0
        finally_order_place = len(old_adds_list) + 1

        if start <= 0 or start > len(old_adds_list):
            logger.debug(f"Загружаем файлы в конец: [{product_id=}:{start=}:{replace=}]")
            load_file_target_place = finally_order_place + has_cover

        if start > 0 and start <= len(old_adds_list) and replace:
            logger.debug(f"Загружаем файлы c заменой: [{product_id=}:{start=}:{replace=}]")
            load_file_target_place = start + has_cover
            finally_order_place = start

        if start > 0 and start <= len(old_adds_list) and not replace:
            logger.debug(f"Загружаем файлы вставкой: [{product_id=}:{start=}:{replace=}]")
            load_file_target_place = finally_order_place + has_cover
            finally_order_place = start

        logger.debug(f"Загружаем файлы в карточку товара: [{product_id=}:{main_card.nm_id=}:{main_wb_client.account_name=}]")

        for i, file in enumerate(files, start=1):
            logger.debug(f"Загрузка файла {i} для товара [{product_id=}:{main_card.nm_id=}:{main_wb_client.account_name=}:{load_file_target_place=}]...")
            content = await file.read()

            if not content:
                logger.warning(f"Пустое содержимое файла {i} - {file.filename} для {product_id=}. Пропускаем.")
                continue

            await self._send_file(
                wb_client=main_wb_client,
                nm_id=main_card.nm_id,
                file_content=content,
                filename=file.filename,
                content_type=file.content_type,
                display_order=load_file_target_place
            )
            load_file_target_place += 1

        logger.debug(f"Все файлы отправлены: [{product_id=}:{main_card.nm_id=}:{main_wb_client.account_name=}]")
        logger.debug(f"{len(old_adds_list)=}")
        logger.debug(f"{has_cover=}")
        logger.debug(f"{load_file_target_place=}")
        # Проверка, что созданы все ячейки для хранения файлов
        await self._ensure_card_photo_count(
            wb_client=main_wb_client,
            nm_id=main_card.nm_id,
            strictly=False,
            expected_count=max(load_file_target_place - 1, len(old_adds_list) + has_cover)
        )

        card_after_update: Card | None = None
        for _ in range(3):
            card_after_update = await main_wb_client.get_card(main_card.nm_id)

            if card_after_update:
                break

        if not card_after_update:
            message = f"Не удалось получить карточку после обновления. [{main_wb_client.account_name}|{main_card.nm_id}]"
            logger.error(message)
            raise ValueError(message)

        card_photos = card_after_update.photos or []
        updated_adds = [ph["big"] for ph in card_photos[has_cover:]]
        result_adds = []

        if start <= 0 or start > len(old_adds_list):
            result_adds_count = len(old_adds_list) + len(files)
            result_adds = updated_adds[:result_adds_count]         

        if start > 0 and start <= len(old_adds_list) and replace:
            len_left_adds = len(updated_adds[:(finally_order_place - 1)])
            len_right_adds = max(len(files), len(old_adds_list[len_left_adds:]))
            len_result_adds = len_left_adds + len_right_adds
            result_adds = updated_adds[:len_result_adds]

        if start > 0 and start <= len(old_adds_list) and not replace:
            new_adds = updated_adds[-(len(files)):]
            left_adds = updated_adds[:(finally_order_place - 1)]
            right_adds = updated_adds[len(left_adds):len(old_adds_list)]
            result_adds = left_adds + new_adds + right_adds

        logger.debug(f"Сформирован итоговый список ссылок на доп.фото товара: [{product_id=}:{len(result_adds)=}]")
        logger.debug(f"Отправляем зафиксированный порядок ссылок в основную карточку: [{product_id=}:{main_card.nm_id=}:{main_wb_client.account_name=}]")
        main_links = []
        links_adds_for_save = updated_adds[:len(result_adds)]

        logger.debug(f"Сохраняем в БД допники товара {product_id=}...")
        await self._wb_media_repo.replace_product_media(
            product_id=product_id,
            user_id=user_id,
            media=WBMedia(
                photos=[WBPhoto(url=ph, display_order=i) for i, ph in enumerate(links_adds_for_save, start=1)]
            )
        )

        if has_cover:
            main_links.append(main_cover)

        main_links.extend(result_adds)

        if card_after_update.video:
            main_links.append(card_after_update.video)

        await main_wb_client.upload_media_by_links(card_media=CardMediaUploadByLinks(
            nm_id=main_card.nm_id, data=main_links
        ))

        await self._ensure_card_photo_count(
            wb_client=main_wb_client,
            nm_id=main_card.nm_id,
            expected_count=len(main_links) - (1 if card_after_update.video else 0)
        )

        return [main_card.nm_id]

    async def update_product_additionals_by_links(
            self,
            data: ProductWBMediaLinksUpdate,
            user_id: Optional[int] = None
    ) -> list[int]:
        logger.info(f"Обновление дополнительных фото на WB для товара {data.product_id}...")
        articles, _, invalid_lvc = await self._article_repo.get_articles_by_criteria(
            local_vendor_codes=[data.product_id]
        )

        if invalid_lvc or not articles:
            raise ValueError(f"Для товара '{data.product_id}' не найдено карточек.")

        product_additionals = [WBPhoto(
            url = ph.url,
            display_order=ph.display_order,
        ) for ph in data.photos]
        update_tasks = []

        for item in articles:
            nm_id = item["nm_id"]
            account = item["account"]
            update_tasks.append(asyncio.create_task(
                self._update_adds_card_by_links(
                    nm_id=nm_id,
                    account=account,
                    product_id=data.product_id,
                    product_additionals=product_additionals
                )
            ))

        results = await asyncio.gather(*update_tasks, return_exceptions=True)
        updated_nm_ids: list[int] = []

        for (res, article) in zip(results, articles):
            if isinstance(res, Exception):
                logger.exception(
                    f"Ошибка во время обновления медиа для карточки товара {data.product_id}-{article["nm_id"]}: {res}"
                )
                continue

            nm_id = article["nm_id"]
            updated_nm_ids.append(nm_id)

        if not updated_nm_ids:
            logger.warning(f"Нет обновленных карточек для сохранения допников товара {data.product_id=}")
            return []

        logger.info("Обноваляем список дополнительных фотографий в БД...")
        new_adds = None

        for item in articles:
            nm_id = item["nm_id"]

            if nm_id not in updated_nm_ids:
                logger.warning(f"Карточки {nm_id} нет среди обновленных. Пропускаем.")
                continue

            account = item["account"]
            wb_client = CardsWBAPI(session=self._session, account_name=account)
            card = await wb_client.get_card(nm_id)

            if not card:
                continue

            cover = await self._wb_media_repo.get_cover_url_of_card(nm_id)
            card_adds = [ph["big"] for ph in card.photos[(1 if cover else 0):]]

            if len(card_adds) != len(product_additionals):
                logger.warning(f"Количество допников в карточке [{account}:{nm_id}] не совпадает с заданным: "
                               f"ожидалось-{len(product_additionals)}, получено-{len(card_adds)}. Пропускаем.")
                continue

            new_adds = card_adds
            break

        if new_adds is None:
            logger.warning(f"Не найдено корректого списка ссылок на допники для товара: {data.product_id=}")
            return []

        logger.debug(f"Обновляем данные по допникам товара в БД: {data.product_id=}:{len(new_adds)=}")
        await self._wb_media_repo.replace_product_media(
            product_id=data.product_id,
            user_id=user_id,
            media=WBMedia(photos=[WBPhoto(url=ph, display_order=i) for i, ph in enumerate(new_adds, start=1)])
        )

        logger.info(f"Обновление допников товара заверешено: {data.product_id=}")
        return updated_nm_ids

    async def _update_adds_card_by_links(
            self,
            nm_id: int,
            account: str | None = None,
            product_id: str | None = None,
            product_additionals: list[WBPhoto] | None = None,
    ) -> None:
        logger.info(f"Обновление допников на WB для карточки товара [{account}:{nm_id}]...")
        if not account:
            account = await self._get_account_by_nm_id(nm_id)

        if not product_id:
            product_id = await self._get_product_id(nm_id=nm_id, account=account)

        wb_client = CardsWBAPI(session=self._session, account_name=account)

        card = None

        for _ in range(3):
            card = await wb_client.get_card(nm_id)

            if card:
                break

        if not card:
            logger.warning(f"Карточка не найдена: [{account}:{nm_id}].")
            return

        if not product_additionals:
            product_additionals = await self._wb_media_repo.get_product_additionals(product_id)

        cover = await self._wb_media_repo.get_cover_url_of_card(nm_id)

        if not cover:
            cover = "https://i.pinimg.com/736x/41/94/df/4194dfa48d2b9ceeb5b0ecc0174691f3.jpg"
            await self._wb_media_repo.update_cover_of_card(article_id=nm_id, media_url=cover)

        video = await self._wb_media_repo.get_video_url_of_card(nm_id)
        adds = [ph.url for ph in product_additionals]

        all_links = [cover, *adds]

        if video:
            all_links.append(video)

        await wb_client.upload_media_by_links(
            CardMediaUploadByLinks(nm_id=nm_id, data=all_links)
        )

        # Закомичено временно, как компромис для ускорения работы менеджера.
        # async with asyncio.TaskGroup() as group:
        #     if video:
        #         group.create_task(self._ensure_card_video_state(
        #             wb_client=wb_client,
        #             nm_id=nm_id,
        #             has_video=True,
        #         ))
        #     else:
        #         group.create_task(self._ensure_card_video_state(
        #             wb_client=wb_client,
        #             nm_id=nm_id,
        #             has_video=False,
        #         ))

        #     group.create_task(self._ensure_card_photo_count(
        #         wb_client=wb_client,
        #         nm_id=nm_id,
        #         strictly=True,
        #         expected_count=len(adds) + (1 if cover else 0)
        #     ))

    async def _upload_only_cover(
            self, 
            file: UploadFile,
            nm_id: int,
            account: str | None = None,
            user_id: int | None = None,
    ):
        logger.info(f"Загрузка обложки для карточки [{nm_id=}]...")
        resolved_account = account or await self._get_account_by_nm_id(nm_id)
        wb_client = CardsWBAPI(session=self._session, account_name=resolved_account)
        card = None

        for _ in range(3):
            card = await wb_client.get_card(nm_id=nm_id)

            if card:
                break

        if not card:
            logger.warning(f"Карточка не найдена: [{resolved_account}:{nm_id}]. return None")
            return

        cover_cell = await self._wb_media_repo.get_cover_url_of_card(nm_id)
        content = await file.read()

        if cover_cell or not card.photos:
            logger.debug(f"У карточки уже есть обложка или отсутствуют любые фото. Заменяем: [{resolved_account}:{nm_id}]")
            await self._send_cover(
                wb_client=wb_client,
                nm_id=nm_id,
                file_content=content,
                filename=file.filename,
                content_type=file.content_type,
            )
        else:
            logger.debug(f"Место обложки занято допником. Отправляем файл в конец: [{resolved_account}:{nm_id=}]")
            await self._append_photo(
                wb_client=wb_client,
                nm_id=nm_id,
                file_content=content,
                filename=file.filename,
                content_type=file.content_type,
            )
        
        if not cover_cell:
            card_photos = card.photos or []
            last_photo_count = len(card_photos)
            expected_count = last_photo_count + 1
            await self._ensure_card_photo_count(
                wb_client=wb_client,
                nm_id=nm_id,
                expected_count=expected_count,
            )

            is_updated = False

            for i in range(3):
                card = None
                
                for _ in range(3):
                    card = await wb_client.get_card(nm_id)
                    if card:
                        break
                
                if not card:
                    continue
                
                if not card.photos or len(card.photos) != expected_count:
                    logger.warning(f"У карточки [{wb_client.account_name}:{card.nm_id}] нет фото после обновления. Попытка: {i + 1}")
                    await asyncio.sleep(3)
                    continue

                is_updated = True
                break

            if not is_updated:
                message = f"После обновления не удалось получить фото обложки. [{wb_client.account_name}:{nm_id}]"
                logger.error(message)
                raise RuntimeError(message)

            video = card.video
            cover = card.photos[-1]["big"]
            adds = [ph["big"] for ph in card.photos[:-1]]
            all_links = [cover, *adds]

            if video:
                all_links.append(video)

            if len(all_links) != expected_count + (1 if video else 0):
                logger.warning(f"После загрузки обложки карточки не совпадает количество ссылок: [{wb_client.account_name}:{nm_id=}:{expected_count=}]")

            await wb_client.upload_media_by_links(
                card_media=CardMediaUploadByLinks(
                    nm_id=nm_id, data=all_links
                )
            )

        card = None

        for _ in range(3):
            card = await wb_client.get_card(nm_id=nm_id)

            if card:
                break

        if not card:
            logger.warning(f"Карточка не найдена: [{resolved_account}:{nm_id}]. return None")
            return

        card_photos = card.photos or []

        if card_photos:
            cover_url = card.photos[0]["big"]
            cover_tm = card.photos[0]["tm"]
            logger.info(f"Обновляем обложку карточки в БД: [{wb_client.account_name}:{nm_id=}:{cover_url=}]")
            await self._wb_media_repo.update_cover_of_card(article_id=nm_id, media_url=cover_url, user_id=user_id)
            await self._card_data_repo.update_card_photo(nm_id, cover_tm, user_id)

            product_id = await self._get_product_id(nm_id, wb_client.account_name)
            product_adds = await self._wb_media_repo.get_product_additionals(product_id)

            if product_adds:
                first_adds = min(product_adds, key=lambda x: x.display_order)
                if first_adds.url == cover_url:
                    logger.info(f"Ссылки на обложку карточки [{nm_id}] и допники карточки совпадают. Обновляем допники товара [{product_id=}]")
                    new_adds = [WBPhoto(url=ph["big"], display_order=i) for i, ph in enumerate(card_photos[1:], start=1)]
                    await self._wb_media_repo.replace_product_media(
                        product_id=product_id,
                        user_id=user_id,
                        media=WBMedia(photos=new_adds)
                    )
            logger.info(f"Загрузка обложки карточки завершена: [{wb_client.account_name}:{nm_id=}:{cover_url=}]")
        else:
            message = f"У карточки [{wb_client.account_name}:{card.nm_id}] нет фото после обновления."
            logger.warning(message)
            raise RuntimeError(message)

        return wb_client.account_name

    async def _upload_only_video(
            self, 
            file: UploadFile,
            nm_id: int,
            account: str | None = None,
            user_id: int | None = None,
    ):
        logger.info(f"Загрузка видео для карточки [{nm_id=}]...")
        resolved_account = account or await self._get_account_by_nm_id(nm_id)
        wb_client = CardsWBAPI(session=self._session, account_name=resolved_account)

        card: Card | None = None
        
        for _ in range(3):
            card = await wb_client.get_card(nm_id=nm_id)

            if card:
                break

        if not card:
            logger.warning(f"Карточка не найдена: [{resolved_account}:{nm_id}]. return None")
            return

        content = await file.read()

        await self._send_video(
            wb_client=wb_client,
            nm_id=nm_id,
            file_content=content,
            filename=file.filename,
            content_type=file.content_type,
        )

        await self._ensure_card_video_state(
            wb_client=wb_client,
            nm_id=nm_id,
            has_video=True,
        )

        card: Card | None = None

        for _ in range(3):
            card = await wb_client.get_card(nm_id)

            if card:
                break

        if not card:
            logger.warning(f"Карточка не найдена: [{resolved_account}:{nm_id}]. return None")
            return
        
        video = card.video

        await self._wb_media_repo.update_video_of_card(
            article_id=nm_id,
            media_url=video,
            user_id=user_id,
        )

        logger.info(f"Загрузка видео карточки завершена: [{wb_client.account_name}:{nm_id=}:{card.video=}]")
        return wb_client.account_name

    async def _get_product_id(self, nm_id: int, account: str) -> str:
        article = await self._article_repo.get_article_by_nm_id_and_account(nm_id, account)

        if not article:
            raise ValueError(f"Карточка nm_id={nm_id} не найдена в БД.")

        return article["local_vendor_code"]

    async def _get_account_by_nm_id(self, nm_id: int) -> str:
        account_map = await self._article_repo.get_accounts_by_nm_ids([nm_id])
        accounts = list(account_map.keys())

        if not accounts:
            raise ValueError(f"Карточка nm_id={nm_id} не найдена в БД.")

        return accounts[0]

    @staticmethod
    async def _send_file(
        wb_client: CardsWBAPI,
        nm_id: int,
        file_content: bytes,
        filename: str,
        content_type: str,
        display_order: int = 1,
    ):
        """Отправка файла."""
        logger.debug(f"Отправка файла: [{wb_client.account_name}:{nm_id=}:{display_order=}]")
        await wb_client.upload_media_file(
            nm_id=nm_id,
            photo_number=display_order,
            filename=filename,
            content_type=content_type or "application/octet-stream",
            content=file_content,
        )

    @classmethod
    async def _send_video(
        cls,
        wb_client: CardsWBAPI,
        nm_id: int,
        file_content: bytes,
        filename: str,
        content_type: str,
    ):
        """Отправка видео карточки."""
        logger.debug(f"Отправка видео: [{wb_client.account_name}:{nm_id=}]")
        await cls._send_file(
            wb_client=wb_client,
            nm_id=nm_id,
            file_content=file_content,
            content_type=content_type,
            filename=filename,
            display_order=1
        )

    @classmethod
    async def _send_cover(
        cls,
        wb_client: CardsWBAPI,
        nm_id: int,
        file_content: bytes,
        filename: str,
        content_type: str,
    ):
        """Отправка обложки карточки."""
        logger.debug(f"Отправка обложки: [{wb_client.account_name}:{nm_id=}]")
        await cls._send_file(
            wb_client=wb_client,
            nm_id=nm_id,
            file_content=file_content,
            content_type=content_type,
            filename=filename,
            display_order=1
        )

    @classmethod
    async def _append_photo(
        cls,
        wb_client: CardsWBAPI,
        nm_id: int,
        file_content: bytes,
        filename: str,
        content_type: str,
    ):
        """Добавление нового фото карточки в конец."""
        logger.debug(f"Отправка нового фото карточки в конец: [{wb_client.account_name}:{nm_id=}]")
        card: Card | None = None

        for _ in range(3):
            card = await wb_client.get_card(nm_id=nm_id)

            if card:
                break

        if not card:
            logger.warning(f"Карточка не найдена: [{wb_client.account_name}:{nm_id}]. return None")
            return
        
        card_photos = card.photos or []
        current_photos_count = len(card_photos)
        display_orders = current_photos_count + 1

        await cls._send_file(
            wb_client=wb_client,
            nm_id=nm_id,
            file_content=file_content,
            content_type=content_type,
            filename=filename,
            display_order=display_orders
        )

    @staticmethod
    async def _ensure_card_photo_count(
            wb_client: CardsWBAPI,
            nm_id: int,
            expected_count: int,
            attempts: int = 20,
            delay_seconds: float = 3.0,
            strictly: bool = True
    ) -> None:
        """Проверить, что в карточке ожидаемое количество фото."""
        logger.info(f"Проверяем соответствия ожидаемого количества фото в карточке [{wb_client.account_name}:{nm_id=}:{expected_count=}]...")
        for _ in range(attempts):
            card: Card | None = None

            for _ in range(3):
                card = await wb_client.get_card(nm_id=nm_id)

                if card:
                    break

            if not card:
                raise RuntimeError(f"Карточка {nm_id=} не найдена.")

            card_photos = card.photos or []
            actual_count = len(card_photos)

            if strictly:
                logger.debug(f"Проверка на строгое соответствие количества фото: {nm_id=}:{expected_count=}:{actual_count=}")
                if actual_count == expected_count:
                    return

                await asyncio.sleep(delay_seconds)
                continue
            
            logger.debug(f"Проверка на соответствие минимальному ожидаемому количеству фото: {nm_id=}:{expected_count=}:{actual_count=}")
            if actual_count >= expected_count:
                return

            await asyncio.sleep(delay_seconds)

        logger.error(f"Проверка на соответствие ожидаемому количеству фото провалена: {nm_id=}:{expected_count=}:{actual_count=}:{strictly=}")
        raise RuntimeError(
            f"Количество фото в карточке nm_id={nm_id} не совпадает. "
            f"Ожидалось {expected_count}, получено {actual_count}."
        )

    @staticmethod
    async def _ensure_card_video_state(
            wb_client: CardsWBAPI,
            nm_id: int,
            has_video: bool = True,
            attempts: int = 20,
            delay_seconds: float = 3.0,
    ) -> None:
        """Проверить, что в карточке есть ссылка на видео."""
        logger.info(f"Проверяем, что в карточке есть ссылка на видео: [{wb_client.account_name}:{nm_id=}]...")
        for _ in range(attempts):
            card: Card | None = None
            for _ in range(3):
                card = await wb_client.get_card(nm_id=nm_id)

                if card:
                    break

            if not card:
                raise RuntimeError(f"Карточка {nm_id=} не найдена.")

            if (has_video and not card.video) or (not has_video and card.video):
                logger.debug(f"Ожидаем, что видео карточки [{card.nm_id}]={has_video}, текущее соостояние видео: {bool(card.video)}")
                await asyncio.sleep(delay_seconds)
            else:
                return

        raise RuntimeError(
            f"Ожидаемое состояние видео в карточке nm_id={nm_id} не совпадает с текущим. "
            f"Ожидалось {has_video=}, получено {bool(card.video)}."
        )
