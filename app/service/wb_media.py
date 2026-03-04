import logging
from typing import Optional

from aiohttp import ClientSession
import asyncio
from fastapi import UploadFile

from app.domain.models import (
    WBMedia,
    WBPhoto,
    ProductWBMediaLinksUpdate,
    CardWBMediaLinksUpdate,
    WBMediaLinksUpdate,
    WBMediaLink,
)
from app.infrastructure.API.wildberries.content.wb_cards import CardsWBAPI
from app.infrastructure.API.wildberries.content.schemes.card_media import CardMediaUploadByLinks
from app.repository.article import ArticleRepository
from app.repository.wb_media import WBMediaRepository
from app.repository.card_data import CardDataRepository


logger = logging.getLogger(__name__)


class WBMediaService:
    """Сервис для медиа карточек товаров на WB."""

    MAX_COUNT_PHOTOS_FOR_CARD = 30

    def __init__(
        self,
        wb_media_repo: WBMediaRepository,
        article_repo: ArticleRepository,
        card_data_repo: CardDataRepository,
        session: ClientSession,
    ):
        self._wb_media_repo = wb_media_repo
        self._article_repo = article_repo
        self._card_data_repo = card_data_repo
        self._session = session

    async def update_product_media_links(self, data: ProductWBMediaLinksUpdate, user_id: Optional[int] = None) -> list[int]:
        """Обновить медиа товара на WB по ссылкам на файлы."""
        logger.info(f"Обновление медиа на WB для товара {data.product_id}...")
        articles, _, invalid_lvc = await self._article_repo.get_articles_by_criteria(
            local_vendor_codes=[data.product_id]
        )

        if invalid_lvc or not articles:
            raise ValueError(f"Для товара '{data.product_id}' не найдено карточек.")

        product_media = self._build_media_from_links(data)
        products_media_for_update_db: WBMedia | None = None
        update_tasks = []

        for item in articles:
            nm_id = item["nm_id"]
            account = item["account"]
            card_unique_media: WBMedia = await self._wb_media_repo.get_media_by_article(nm_id)

            card_data = CardWBMediaLinksUpdate(
                nm_id=nm_id,
                account=account,
                video=WBMediaLink(
                    url=card_unique_media.video
                ) if card_unique_media.video else None,
                photos=[WBMediaLink(
                    url=photo.url,
                    display_order=photo.display_order,
                ) for photo in card_unique_media.photos]
            )

            update_tasks.append(asyncio.create_task(
                self.update_card_media_links(
                    data=card_data,
                    product_media=product_media,
                    user_id=user_id,
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

        for item in articles:
            nm_id = item["nm_id"]
            account = item["account"]
            updated_uniq_card_media = await self._wb_media_repo.get_media_by_article(nm_id)
            wb_client = CardsWBAPI(session=self._session, account_name=account)
            card = await wb_client.get_card(nm_id=nm_id)

            if not card:
                logger.warning(f"Карточка не найдена: {account} | {nm_id}")
                continue

            places_uniq_card = {photo.display_order for photo in updated_uniq_card_media.photos}
            new_product_photos: list[WBPhoto] = []

            display_order_count = 1

            for i, photo in enumerate((card.photos or []), start=1):
                if i not in places_uniq_card:
                    new_product_photos.append(
                        WBPhoto(url=photo["big"], display_order=display_order_count)
                    )
                    display_order_count += 1

            if not products_media_for_update_db:
                products_media_for_update_db = WBMedia(photos=new_product_photos)

            if not updated_uniq_card_media.video:
                products_media_for_update_db.video = card.video

            if card.photos:
                tm = card.photos[0]["tm"]
                await self._card_data_repo.update_card_photo(card.nm_id, tm, user_id)

        await self._wb_media_repo.replace_product_media(data.product_id, products_media_for_update_db, user_id=user_id)
        return updated_nm_ids

    async def update_product_additionals(
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

        for item in articles:
            nm_id = item["nm_id"]
            account = item["account"]
            cover_and_video: WBMedia = await self._wb_media_repo.get_cover_and_video_of_card(nm_id=nm_id)
            update_tasks = []

            card_data = CardWBMediaLinksUpdate(
                nm_id=nm_id,
                account=account,
                video=WBMediaLink(
                    url=cover_and_video.video,
                ) if cover_and_video.video else None,
                photos=[WBMediaLink(
                    url=photo.url,
                    display_order=photo.display_order,
                ) for photo in cover_and_video.photos]
            )

            update_tasks.append(asyncio.create_task(
                self.update_cover_and_video_card(
                    data=card_data,
                    product_additionals=product_additionals,
                    user_id=user_id
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
        
        is_update_additionals = False
        logger.info("Обноваляем список дополнительных фотографий в БД...")
        for item in articles:
            nm_id = item["nm_id"]

            if nm_id not in updated_nm_ids:
                logger.warning(f"Карточки {nm_id} нет среди обновленных. Пропускаем.")
                continue

            account = item["account"]
            wb_client = CardsWBAPI(session=self._session, account_name=account)
            can_update = False
            for _ in range(3):
                card = await wb_client.get_card(nm_id=nm_id)

                if not card:
                    logger.warning(f"Карточка не найдена: {account} | {nm_id}")
                    break

                cover_and_video: WBMedia = await self._wb_media_repo.get_cover_and_video_of_card(nm_id=nm_id)
                new_additionals = card.photos or []

                if cover_and_video.photos:
                    new_additionals = new_additionals[1:]

                if len(product_additionals) != len(new_additionals):
                    logger.warning(f"Количество новых ссылок не совпадает.")
                    await asyncio.sleep(2)
                    continue

                can_update = True

            if can_update:
                await self._wb_media_repo.replace_product_media(
                    product_id=data.product_id,
                    user_id=user_id,
                    media=WBMedia(
                        photos=[WBPhoto(
                            url=ph["big"],
                            display_order=i
                        ) for i, ph in enumerate(new_additionals, start=1)]
                    )
                )
                is_update_additionals = True
                break

        if not is_update_additionals:
            logger.warning(f"Обновление дополнительных фото на WB для товара {data.product_id} не выполнено.")
        
        return updated_nm_ids

    async def update_cover_and_video_card(
            self,
            data: CardWBMediaLinksUpdate,
            product_additionals: list[WBPhoto] | None = None,
            user_id: Optional[int] = None
    ) -> None:
        logger.info(f"Обновление обложки и видео на WB для карточки товара [{data.account}:{data.nm_id}]...")
        article = await self._article_repo.get_article_by_nm_id_and_account(
            nm_id=data.nm_id,
            account=data.account,
        )

        if not article:
            raise ValueError(f"Карточка nm_id={data.nm_id} не найдена в БД.")

        if product_additionals is None:
            product_id = article["local_vendor_code"]
            product_additionals: list[WBPhoto] = await self._wb_media_repo.get_product_additional(product_id)

        video: str | None = data.video.url if data.video else None
        cover: WBPhoto | None = next((WBPhoto(
            url=photo.url,
            display_order=photo.display_order,
        ) for photo in data.photos if photo.display_order <= 1), None)

        all_links = self._build_links_of_card(
            cover=cover,
            video=video,
            additionals=product_additionals
        )

        wb_client = CardsWBAPI(session=self._session, account_name=data.account)
        await wb_client.upload_media_by_links(
            CardMediaUploadByLinks(nm_id=data.nm_id, data=all_links)
        )

        await self._ensure_card_media_count(
            wb_client=wb_client,
            nm_id=data.nm_id,
            expected_count=len(all_links),
        )

        card = await wb_client.get_card(nm_id=data.nm_id)
        new_video = card.video
        new_cover = None

        if cover and card.photos:
            cover_map = card.photos[0]
            new_cover = WBPhoto(
                url=cover_map["big"],
                display_order=1
            )
            cover_tm = cover_map["tm"]
            await self._card_data_repo.update_card_photo(nm_id=card.nm_id, photo_url=cover_tm, user_id=user_id)

        await self._wb_media_repo.replace_card_media(
            data.nm_id,
            WBMedia(
                video=new_video,
                photos=[new_cover] if new_cover else []
            ),
            user_id=user_id,
        )

    async def update_card_media_links(self, data: CardWBMediaLinksUpdate, product_media: Optional[WBMedia] = None, user_id: Optional[int] = None) -> None:
        """Обновить медиа карточки товара на WB по ссылкам на файлы."""
        logger.info(f"Обновление медиа на WB для карточки товара [{data.account}:{data.nm_id}]...")
        if not product_media:
            article = await self._article_repo.get_article_by_nm_id_and_account(
                nm_id=data.nm_id,
                account=data.account,
            )

            if not article:
                raise ValueError(f"Карточка nm_id={data.nm_id} не найдена в БД.")

            product_id = article["local_vendor_code"]
            product_media = await self._wb_media_repo.get_media_by_product(product_id)

        card_unique_media = self._build_media_from_links(
            data,
            is_uniq_card_links=True,
            product_photo_links_count=len(product_media.photos)
        )

        merged_links = self._merge_media_links(product_media, card_unique_media)

        wb_client = CardsWBAPI(session=self._session, account_name=data.account)

        await wb_client.upload_media_by_links(
            CardMediaUploadByLinks(nm_id=data.nm_id, data=merged_links)
        )

        await self._ensure_card_media_count(
            wb_client=wb_client,
            nm_id=data.nm_id,
            expected_count=len(merged_links),
        )

        card = await wb_client.get_card(nm_id=data.nm_id)
        places_uniq_card = {photo.display_order for photo in card_unique_media.photos}
        new_uniq_photos = [
            WBPhoto(url=photo["big"], display_order=i)
            for i, photo in enumerate((card.photos or []), start=1) if i in places_uniq_card
        ]
        new_uniq_wb_links = WBMedia(
            video=card.video,
            photos=new_uniq_photos or []
        )

        if card.photos:
            tm = card.photos[0]["tm"]
            await self._card_data_repo.update_card_photo(card.nm_id, tm, user_id)

        await self._wb_media_repo.replace_card_media(data.nm_id, new_uniq_wb_links, user_id=user_id)

    async def upload_product_media_file(
            self,
            product_id: str,
            is_video: bool,
            file: UploadFile,
            user_id: Optional[int] = None,
    ) -> list[int]:
        """Загрузка медиа файла для товара (во все карточки товара)."""
        articles, _, invalid_lvc = await self._article_repo.get_articles_by_criteria(
            local_vendor_codes=[product_id]
        )

        if invalid_lvc or not articles:
            raise ValueError(f"Для товара '{product_id}' не найдено карточек.")

        product_media = await self._wb_media_repo.get_media_by_product(product_id)
        content = await file.read()
        last_display_order = (
            max(
                product_media.photos,
                key=lambda x: x.display_order
            ).display_order
        ) if product_media.photos else 0

        upload_tasks = []
        for item in articles:
            nm_id = item["nm_id"]
            account = item["account"]

            upload_tasks.append(asyncio.create_task(self._upload_media_file_old(
                nm_id=nm_id,
                account=account,
                is_video=is_video,
                file_content=content,
                filename=file.filename,
                content_type=file.content_type,
                user_id=user_id,
            )))

        results = await asyncio.gather(*upload_tasks, return_exceptions=True)
        updated_nm_ids: list[int] = []
        new_media: str | WBPhoto | None = None

        for (res, article) in zip(results, articles):
            if isinstance(res, Exception):
                logger.exception(
                    f"Ошибка во время загрузки медиа для карточки товара {product_id}-{article["nm_id"]}: {res}"
                )
                continue

            nm_id = article["nm_id"]
            card_media = await self._wb_media_repo.get_media_by_article(nm_id)

            if is_video and not card_media.video:
                new_media = res
            else:
                if not isinstance(new_media, WBPhoto):
                    new_media = WBPhoto(
                        url="",
                        display_order=1
                    )

                new_media.url = res.url

            updated_nm_ids.append(nm_id)

        if new_media and is_video:
            product_media.video = new_media
        elif new_media and isinstance(new_media, WBPhoto):
            new_media.display_order = last_display_order + 1
            product_media.photos.append(new_media)

        if product_media:
            await self._wb_media_repo.replace_product_media(product_id, product_media, user_id=user_id)

        return updated_nm_ids

    async def upload_card_media_file(
            self,
            nm_id: int,
            account: Optional[str],
            is_video: bool,
            file: UploadFile,
            display_order: int = 1,
            user_id: Optional[int] = None,
    ) -> str:
        """Загрузка медиа файла для карточки товара."""
        resolved_account = account or await self._get_account_by_nm_id(nm_id)
        card_video_and_cover: WBMedia = await self._wb_media_repo.get_cover_and_video_of_card(nm_id)

        content = await file.read()

        new_link = await self._upload_media_file(
            nm_id=nm_id,
            account=resolved_account,
            is_video=is_video,
            file_content=content,
            filename=file.filename,
            content_type=file.content_type,
            user_id=user_id,
            display_order=display_order,
            is_cover=not is_video,
        )

        new_card_media = WBMedia(photos=[])

        if is_video:
            new_card_media.video = new_link
            new_card_media.photos = card_video_and_cover.photos
        elif not is_video and display_order == 1:
            new_card_media.video = card_video_and_cover.video
            new_card_media.photos.append(new_link)

        await self._wb_media_repo.replace_card_media(nm_id, new_card_media, user_id=user_id)
        return resolved_account

    async def _upload_media_file_old(
        self,
        nm_id: int,
        account: Optional[str],
        is_video: bool,
        file_content: bytes,
        filename: str,
        content_type: str,
        photo_number: int,
        expected_count: int,
        user_id: Optional[int] = None,
    ) -> str | WBPhoto | None:
        """Загрузить один медиа файл на WB. (Старый метод.)"""
        resolved_account = account or await self._get_account_by_nm_id(nm_id)
        wb_client = CardsWBAPI(session=self._session, account_name=resolved_account)

        await wb_client.upload_media_file(
            nm_id=nm_id,
            photo_number=photo_number,
            filename=filename,
            content_type=content_type or "application/octet-stream",
            content=file_content,
        )

        await self._ensure_card_media_count(
            wb_client=wb_client,
            nm_id=nm_id,
            expected_count=expected_count,
        )

        for _ in range(3):
            card = await wb_client.get_card(nm_id=nm_id)

            if not card:
                raise RuntimeError(f"Карточка nm_id={nm_id} не найдена после загрузки медиа.")

            current_card_media = self._media_from_card(card)

            new_link: str | WBPhoto | None = None

            if is_video:
                new_link = current_card_media.video
            else:
                new_link = next(
                    (photo for photo in current_card_media.photos if photo.display_order == photo_number), None
                )

            if card.photos:
                tm = card.photos[0]["tm"]
                await self._card_data_repo.update_card_photo(card.nm_id, tm, user_id)

            if new_link:
                return new_link

        logger.error(f"Не удалось обработать загруженные медиафайлы для карточки: {nm_id}.")
        raise RuntimeError(f"Не удалось обработать загруженные медиафайлы для карточки: {nm_id}.")

    async def _upload_media_file(
            self,
            nm_id: int,
            account: Optional[str],
            is_video: bool,
            file_content: bytes,
            filename: str,
            content_type: str,
            display_order: int = 1,
            is_cover: bool = False,
            user_id: Optional[int] = None,
    ) -> str | WBPhoto | None:
        """Загрузка медиа файла для карточки товара."""
        logger.info(f"Загрузка файла для карточки [{account}:{nm_id}]...")
        resolved_account = account or await self._get_account_by_nm_id(nm_id)
        product_id = await self._get_product_id(nm_id, resolved_account)

        card_cover_and_video = await self._wb_media_repo.get_cover_and_video_of_card(nm_id)

        cover = next((ph for ph in card_cover_and_video.photos), None)
        video = card_cover_and_video.video or None
        products_additionals = await self._wb_media_repo.get_product_additional(product_id)

        all_links = self._build_links_of_card(
            cover=cover,
            video=video,
            additionals=products_additionals,
        )
        last_count_photos = max(len(all_links), display_order)

        if not is_video and last_count_photos > self.MAX_COUNT_PHOTOS_FOR_CARD - 1:
            error_message = f"Ошибка при загрузке фото для карточки {nm_id}. Достигнуто максимальное количество."
            logger.error(error_message)
            raise RuntimeError(error_message)

        if is_video or (is_cover and cover is not None):
            display_order = 1
        elif is_cover and cover is None:
            display_order = last_count_photos + 1
        elif display_order > last_count_photos:
            display_order = last_count_photos + 1

        wb_client = CardsWBAPI(session=self._session, account_name=resolved_account)

        await wb_client.upload_media_file(
            nm_id=nm_id,
            photo_number=display_order,
            filename=filename,
            content_type=content_type or "application/octet-stream",
            content=file_content,
        )

        expected_count = last_count_photos

        if (
            (display_order > last_count_photos)
            or (is_video and not video)
            or (is_cover and not cover)
        ):
            expected_count += 1

        await self._ensure_card_media_count(
            wb_client=wb_client,
            nm_id=nm_id,
            expected_count=expected_count,
        )

        for _ in range(3):
            card = await wb_client.get_card(nm_id=nm_id)

            if not card:
                raise RuntimeError(f"Карточка nm_id={nm_id} не найдена после загрузки файла.")

            current_card_media = self._media_from_card(card)
    
            if is_video:
                return current_card_media.video
            
            if is_cover:
                if display_order != 1:
                    data_to_update = []
                    if card.video:
                        data_to_update.append(card.video)

                    if card.photos:
                        data_to_update.append(card.photos[-1]["big"])
                        data_to_update.extend(list(c["big"] for c in card.photos[:-1]))

                    await wb_client.upload_media_by_links(CardMediaUploadByLinks(
                        nm_id=card.nm_id, data=data_to_update
                    ))
                    await self._wb_media_repo.replace_product_media(
                        product_id=product_id,
                        media=WBMedia(
                            photos=[WBPhoto(url=c["big"], display_order=i) for i, c in enumerate(card.photos[1:], start=1)]
                        )
                    )
                tm = card.photos[0]["tm"]
                await self._card_data_repo.update_card_photo(card.nm_id, tm, user_id)
                return current_card_media.photos[0]

            return current_card_media.photos[display_order - 1]

        logger.error(f"Ошибка при получении последней фотографии из карточки {nm_id}.")
        raise RuntimeError(f"Ошибка при получении последней фотографии из карточки {nm_id}.")

    async def upload_product_media_files(
        self,
        product_id: str,
        files: list[UploadFile],
        user_id: Optional[int] = None,
    ) -> list[int]:
        """Загрузить дополнительные фотографии для всех карточек товаров в указанном порядке."""
        logger.info(f"Загрузка файлов для товара {product_id}...")
        if not files:
            return []

        articles, _, invalid_lvc = await self._article_repo.get_articles_by_criteria(local_vendor_codes=[product_id])

        if invalid_lvc or not articles:
            raise ValueError(f"Для товара '{product_id}' не найдено карточек.")

        updated_nm_ids = []

        await self.update_product_additionals(user_id=user_id, data=ProductWBMediaLinksUpdate(
            photos=[],
            product_id=product_id
        ))

        for i, file in enumerate(files, start=1):
            content = await file.read()
            logger.info(f"Загрузка файла {i} для товара {product_id}...")
            if not content:
                logger.warning(f"Пустое содержимое файла {file.filename} для product {product_id}")
                continue

            upload_tasks = []

            for item in articles:
                nm_id = item["nm_id"]
                account = item["account"]
                card_cover_and_video = await self._wb_media_repo.get_cover_and_video_of_card(nm_id)
                has_cover = 1 if card_cover_and_video.photos else 0
                photo_number = i + has_cover
                upload_tasks.append(asyncio.create_task(self._upload_media_file(
                    nm_id=nm_id,
                    account=account,
                    is_video=False,
                    file_content=content,
                    filename=file.filename,
                    content_type=file.content_type,
                    display_order=photo_number,
                    user_id=user_id,
                )))

            results = await asyncio.gather(*upload_tasks, return_exceptions=True)
            updated_nm_ids.extend(
                [
                    article["nm_id"] 
                    for article, res in zip(articles, results)
                    if not isinstance(res, Exception)
                ]
            )

        for item in articles:
            nm_id = item["nm_id"]
            account = item["account"]
            card_cover_and_video = await self._wb_media_repo.get_cover_and_video_of_card(nm_id)
            has_cover = 1 if card_cover_and_video.photos else 0

            wb_client = CardsWBAPI(session=self._session, account_name=account)

            can_update = False
            
            for _ in range(3):
                card = await wb_client.get_card(nm_id)

                if not card:
                    logger.warning(f"Не найдена карточка: [{account}:{nm_id}]")
                    break

                card_photos = [ph["big"] for ph in card.photos]

                if has_cover:
                    card_photos = card_photos[1:]
                
                card_photos = card_photos[:len(files)]

                if not (len(card_photos) == len(files)):
                    logger.warning(f"Количество ссылок в карточке не совпадает: {len(card_photos)}-{len(files)}")
                    await asyncio.sleep(2)
                    continue

                can_update = True

            if can_update:            
                new_product_media = [WBPhoto(url=url, display_order=i) for i, url in enumerate(card_photos, start=1)]
                await self._wb_media_repo.replace_product_media(product_id, WBMedia(photos=new_product_media), user_id=user_id)
                break

        return sorted(set(updated_nm_ids))

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
    def _merge_media_links(product_media: WBMedia, card_media: WBMedia) -> list[str]:
        links = [p.url for p in product_media.photos]
        card_photos = sorted(card_media.photos, key=lambda x: x.display_order)

        for photo in card_photos:
            position = max(photo.display_order - 1, 0)

            if position > len(links):
                links.append(photo.url)
            else:
                links.insert(position, photo.url)

        video = card_media.video or product_media.video

        if video:
            links.append(video)

        return links

    @staticmethod
    def _build_media_from_links(
            data: WBMediaLinksUpdate, /,
            is_uniq_card_links: bool = False,
            product_photo_links_count: int = 0
    ) -> WBMedia:
        photos = [
            WBPhoto(url=photo.url, display_order=photo.display_order)
            for photo in data.photos
        ]
        photos_sorted = sorted(photos, key=lambda x: x.display_order)
        place_inc = 1

        if is_uniq_card_links:
            for photo in photos_sorted:
                if photo.display_order > product_photo_links_count:
                    photo.display_order = product_photo_links_count + place_inc
                    place_inc += 1

        return WBMedia(
            video=data.video.url if data.video else None,
            photos=photos_sorted,
        )

    @staticmethod
    async def _ensure_card_media_count(
            wb_client: CardsWBAPI,
            nm_id: int,
            expected_count: int,
            attempts: int = 20,
            delay_seconds: float = 3.0,
    ) -> None:
        """Проверить, что в карточке ожидаемое количество файлов."""
        logger.info(f"Проверяем соответствия ожидаемого количества медиа в карточке [{wb_client.account_name}:{nm_id}]...")
        for _ in range(attempts):
            card = await wb_client.get_card(nm_id=nm_id)

            if not card:
                raise RuntimeError(f"Карточка nm_id={nm_id} не найдена после обновления медиа.")

            actual_count = len(card.photos or []) + (1 if card.video else 0)

            if actual_count != expected_count:
                await asyncio.sleep(delay_seconds)
            else:
                return

        raise RuntimeError(
            f"Количество медиа в карточке nm_id={nm_id} не совпадает. "
            f"Ожидалось {expected_count}, получено {actual_count}."
        )

    @staticmethod
    def _media_from_card(card) -> WBMedia:
        photos = [
            WBPhoto(url=photo["big"], display_order=i)
            for i, photo in enumerate(card.photos or [], start=1)
        ]
        return WBMedia(video=card.video, photos=photos)

    @staticmethod
    def _build_links_of_card(cover: WBPhoto | None, video: str | None, additionals: list[WBPhoto]) -> list[str]:
        additionals = sorted(additionals, key=lambda x: x.display_order)
        all_links = [] 

        if video:
            all_links.append(video)

        if cover:
            all_links.append(cover.url)
        
        all_links.extend([adds.url for adds in additionals])

        return all_links
