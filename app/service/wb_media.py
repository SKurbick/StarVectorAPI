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

            places_uniq_card = {photo.display_order for photo in updated_uniq_card_media.photos}
            new_product_photos: list[WBPhoto] = []

            display_order_count = 1

            for i, photo in enumerate(card.photos, start=1):
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
            for i, photo in enumerate(card.photos, start=1) if i in places_uniq_card
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

            upload_tasks.append(asyncio.create_task(self._upload_media_file(
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
            user_id: Optional[int] = None,
    ) -> str:
        """Загрузка медиа файла для карточки товара."""
        resolved_account = account or await self._get_account_by_nm_id(nm_id)
        card_media = await self._wb_media_repo.get_media_by_article(nm_id)
        content = await file.read()

        new_link = await self._upload_media_file(
            nm_id=nm_id,
            account=resolved_account,
            is_video=is_video,
            file_content=content,
            filename=file.filename,
            content_type=file.content_type,
            user_id=user_id,
        )

        if is_video:
            card_media.video = new_link
        else:
            card_media.photos.append(new_link)

        await self._wb_media_repo.replace_card_media(nm_id, card_media, user_id=user_id)
        return resolved_account

    async def _upload_media_file(
            self,
            nm_id: int,
            account: Optional[str],
            is_video: bool,
            file_content: bytes,
            filename: str,
            content_type: str,
            user_id: Optional[int] = None,
    ) -> str | WBPhoto | None:
        """Загрузка медиа файла для карточки товара."""
        resolved_account = account or await self._get_account_by_nm_id(nm_id)
        product_id = await self._get_product_id(nm_id, resolved_account)
        product_media = await self._wb_media_repo.get_media_by_product(product_id)
        card_media = await self._wb_media_repo.get_media_by_article(nm_id)
        last_count_photos = len(product_media.photos or []) + len(card_media.photos or [])

        if not is_video and last_count_photos > self.MAX_COUNT_PHOTOS_FOR_CARD - 1:
            error_message = f"Ошибка при загрузке фото для карточки {nm_id}. Достигнуто максимальное количество."
            logger.error(error_message)
            raise RuntimeError(error_message)

        if is_video:
            display_order = 1
        else:
            display_order = last_count_photos + 1

        wb_client = CardsWBAPI(session=self._session, account_name=resolved_account)

        await wb_client.upload_media_file(
            nm_id=nm_id,
            photo_number=display_order,
            filename=filename,
            content_type=content_type or "application/octet-stream",
            content=file_content,
        )

        has_video = card_media.video or product_media.video
        expected_count = last_count_photos + (1 if has_video else 0)

        if not is_video or (is_video and not has_video):
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
            new_link = current_card_media.video if is_video else current_card_media.photos[-1]

            if card.photos:
                tm = card.photos[0]["tm"]
                await self._card_data_repo.update_card_photo(card.nm_id, tm, user_id)

            if not (isinstance(new_link, WBPhoto) and new_link.display_order != last_count_photos + 1):
                return new_link

        logger.error(f"Ошибка при получении последней фотографии из карточки {nm_id}.")
        raise RuntimeError(f"Ошибка при получении последней фотографии из карточки {nm_id}.")

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
