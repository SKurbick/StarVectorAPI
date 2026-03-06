from typing import Optional

from asyncpg import Pool

from app.domain.models import WBPhoto, WBMedia


class WBMediaRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def replace_product_media(self, product_id: str, media: WBMedia, user_id: Optional[int] = None) -> None:
        """Полностью заменить медиа товара (общие для всех карточек)."""
        await self._replace_media(product_id=product_id, article_id=None, media=media, user_id=user_id)

    async def _replace_media(
        self,
        product_id: str | None,
        article_id: int | None,
        media: WBMedia,
        user_id: Optional[int] = None,
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

        into_cols = "product_id, article_id, media_type, media_url, display_order"
        params_placeholders = "$1, $2, $3, $4, $5"

        if user_id is not None:
            into_cols += ", last_modified_by_user_id"
            params_placeholders += ", $6"

        insert_query = f"""
            INSERT INTO wb_media ({into_cols})
            VALUES ({params_placeholders})
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if not product_id:
                    product_id = await conn.fetchval(get_product_id_query, article_id)

                await conn.execute(delete_query, product_id, article_id)

                rows = []
                if media.video:
                    video_item = [product_id, article_id, "video", media.video, 0]

                    if user_id is not None:
                        video_item.append(user_id)

                    rows.append(tuple(video_item))

                for photo in media.photos:
                    photo_item = [product_id, article_id, "photo", photo.url, photo.display_order]

                    if user_id is not None:
                        photo_item.append(user_id)

                    rows.append(tuple(photo_item))

                if rows:
                    await conn.executemany(insert_query, rows)

    async def get_video_url_of_card(self, nm_id: int) -> str | None:
        query = """
            SELECT media_url
            FROM wb_media
            WHERE article_id = $1
            AND media_type = 'video';
        """

        return await self.pool.fetchval(query, nm_id)

    async def get_cover_url_of_card(self, nm_id: int) -> str | None:
        query = """
            SELECT media_url
            FROM wb_media
            WHERE article_id = $1
            AND media_type = 'photo'
            AND display_order = 1;
        """

        return await self.pool.fetchval(query, nm_id)

    async def get_product_additionals(self, product_id: str) -> list[WBPhoto]:
        """Получить медиа-ссылки на допники WB для товара."""
        query = """
            SELECT
                media_url,
                display_order
            FROM
                wb_media
            WHERE product_id = $1
            AND article_id IS NULL
            AND media_type != 'video'
            ORDER BY display_order;
        """

        rows = await self.pool.fetch(query, product_id)
        media = []

        for row in rows:
            media.append(WBPhoto(
                url=row["media_url"],
                display_order=row["display_order"],
            ))

        return media

    async def update_cover_of_card(self, article_id: int, media_url: str | None, user_id: int | None = None):
        delete_cover_link_query = """
            DELETE FROM wb_media
            WHERE article_id = $1
            AND media_type = 'photo';
        """
        
        get_product_id_query = """
            SELECT local_vendor_code
            FROM article
            WHERE nm_id = $1
        """
        
        product_id = await self.pool.fetchval(get_product_id_query, article_id)

        into_cols = "product_id, article_id, media_type, media_url, display_order"
        params_placeholders = "$1, $2, 'photo', $3, 1"
        params = [product_id, article_id, media_url]

        if user_id is not None:
            into_cols += ", last_modified_by_user_id"
            params_placeholders += ", $4"
            params.append(user_id)

        insert_query = f"""
            INSERT INTO wb_media ({into_cols})
            VALUES ({params_placeholders})
            ON CONFLICT (article_id, media_type) DO UPDATE
            SET product_id = EXCLUDED.product_id,
                media_url = EXCLUDED.media_url,
                display_order = EXCLUDED.display_order
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if not media_url:
                    await conn.execute(delete_cover_link_query, article_id)
                    return

                await conn.execute(insert_query, *params)

    async def update_video_of_card(self, article_id: int, media_url: str | None, user_id: int | None = None):
        delete_video_link_query = """
            DELETE FROM wb_media
            WHERE article_id = $1
            AND media_type = 'video';
        """
        
        get_product_id_query = """
            SELECT local_vendor_code
            FROM article
            WHERE nm_id = $1
        """

        product_id = await self.pool.fetchval(get_product_id_query, article_id)

        into_cols = "product_id, article_id, media_type, media_url, display_order"
        params_placeholders = "$1, $2, 'video', $3, 0"
        params = [product_id, article_id, media_url]

        if user_id is not None:
            into_cols += ", last_modified_by_user_id"
            params_placeholders += ", $4"
            params.append(user_id)

        insert_query = f"""
            INSERT INTO wb_media ({into_cols})
            VALUES ({params_placeholders})
            ON CONFLICT (article_id, media_type) DO UPDATE
            SET product_id = EXCLUDED.product_id,
                media_url = EXCLUDED.media_url,
                display_order = EXCLUDED.display_order
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if not media_url:
                    await conn.execute(delete_video_link_query, article_id)
                    return

                await conn.execute(insert_query, *params)
