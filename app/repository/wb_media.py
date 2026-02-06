from asyncpg import Pool

from app.domain.models import WBPhoto, WBMedia


class WBMediaRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_media_by_product(self, product_id: str) -> WBMedia:
        """Получить медиа-ссылки на WB для товара."""
        query = """
            SELECT
                media_type,
                media_url,
                display_order
            FROM 
                wb_media
            WHERE product_id = $1
            AND article_id IS NULL
            ORDER BY display_order;
        """

        rows = await self.pool.fetch(query, product_id)
        media = WBMedia(photos=[])

        for row in rows:
            if row["media_type"] == "video":
                media.video = row["media_url"]
                continue

            media.photos.append(WBPhoto(
                url=row["media_url"],
                display_order=row["display_order"],
            ))
        
        return media
    
    async def get_media_by_article(self, article_id: int) -> WBMedia:
        """Получить медиа-ссылки на WB для карточки."""
        query = """
            SELECT
                media_type,
                media_url,
                display_order
            FROM 
                wb_media
            WHERE article_id = $1
            ORDER BY display_order;
        """

        rows = await self.pool.fetch(query, article_id)
        media = WBMedia(photos=[])

        for row in rows:
            if row["media_type"] == "video":
                media.video = row["media_url"]
                continue

            media.photos.append(WBPhoto(
                url=row["media_url"],
                display_order=row["display_order"],
            ))

        return media

    async def replace_product_media(self, product_id: str, media: WBMedia) -> None:
        """Полностью заменить медиа товара (общие для всех карточек)."""
        await self._replace_media(product_id=product_id, article_id=None, media=media)

    async def replace_card_media(self, article_id: int, media: WBMedia) -> None:
        """Полностью заменить медиа карточки."""
        await self._replace_media(product_id=None, article_id=article_id, media=media)

    async def _replace_media(
        self,
        product_id: str | None,
        article_id: int | None,
        media: WBMedia,
    ) -> None:
        get_product_id_query = """
            SELECT local_vendor_code
            FROM article
            WHERE nm_id = $1
        """

        delete_query = """
            DELETE FROM wb_media
            WHERE
                product_id = $1
                AND (article_id = $2 OR ($2 IS NULL AND article_id IS NULL))
        """

        insert_query = """
            INSERT INTO wb_media (product_id, article_id, media_type, media_url, display_order)
            VALUES ($1, $2, $3, $4, $5)
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if not product_id:
                    product_id = await conn.fetchval(get_product_id_query, article_id)

                await conn.execute(delete_query, product_id, article_id)

                rows = []
                if media.video:
                    rows.append((product_id, article_id, "video", media.video, 0))

                for photo in media.photos:
                    rows.append((
                        product_id,
                        article_id,
                        "photo",
                        photo.url,
                        photo.display_order,
                    ))

                if rows:
                    await conn.executemany(insert_query, rows)
