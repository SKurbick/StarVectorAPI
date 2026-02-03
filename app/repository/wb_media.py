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
