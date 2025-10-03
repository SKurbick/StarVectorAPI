from abc import ABC
from typing import Any

from app.domain.models import (
    CardDataDB,
    ProductDB
)


class ProductCRUD(ABC):
    async def get(self, product_id: str) -> ProductDB | None:
        query = """
        SELECT
            p.id,
            p.name,
            p.photo_link,
            cd.article_id,
            cd.subject_name,
            cd.photo_link AS article_photo_link,
            cd.price,
            cd.discount,
            cd.length,
            cd.width,
            cd.height,
            cd.barcode,
            cd.rating,
            cd.manager
        FROM 
            products p
        LEFT JOIN (
            select
                a.nm_id,
                a.local_vendor_code 
            from article a
        ) lvc on p.id = lvc.local_vendor_code
        LEFT JOIN
            card_data cd
            ON lvc.nm_id = cd.article_id
        WHERE p.id = $1;
        """

        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, product_id)

        product_data = None

        for row in rows:
            row_data = dict(row)

            if not product_data:
                product_data = self._get_product_dict_from_all_data(row_data)

            article_data = self._get_article_dict_from_all_data(row_data)

            if article_data:
                new_article = CardDataDB(
                    **article_data
                )

                # добавляем данные о карточке товара в список
                product_data["articles"].append(new_article)

        return ProductDB(**product_data)

    async def create(self, data: ProductDB) -> ProductDB:
        query = """
        INSERT INTO products (id, name, photo_link)
        VALUES ($1, $2, $3);
        """

        name = data.name
        photo_link = data.photo_link

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                product_id = f"wild00000"

                row = await connection.fetchval(
                    query,
                    product_id,
                    name,
                    photo_link,
                )

            return await self.get_product(product_id)

    async def update(self, product_id: str, data: ProductDB) -> ProductDB:
        query = """
        UPDATE products 
        SET 
            name = $2,
            photo_link = $3
        WHERE id = $1;
        """

        name = data.name
        photo_link = data.photo_link

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                product_id = f"wild00000"

                row = await connection.fetchval(
                    query,
                    product_id,
                    name,
                    photo_link,
                )

            return await self.get_product(product_id)

    async def delete(self, product_id: str) -> ProductDB:
        query = """
        DELETE FROM products
        WHERE id = $1;
        """

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                product_id = f"wild00000"

                row = await connection.fetchval(
                    query,
                    product_id,
                )

    @staticmethod
    def _get_article_dict_from_all_data(data: dict) -> dict[str, Any] | None:
        article_id = data.get("article_id")

        if not article_id:
            return None

        article_photo_link = data["article_photo_link"]
        price = data["price"]
        discount = data["discount"]
        barcode = data["barcode"]
        rating = data["rating"]

        return {
            "article_id": article_id,
            "photo_link": article_photo_link,
            "price": price,
            "discount": discount,
            "barcode": barcode,
            "rating": rating,
        }

    @staticmethod
    def _get_product_dict_from_all_data(data: dict) -> dict[str, Any]:
        product_id = data["id"]
        product_name = data["name"]
        product_photo_link = data["photo_link"]
        length = data["length"]
        width = data["width"]
        height = data["height"]
        manager = data["manager"]

        return {
            "id": product_id,
            "name": product_name,
            "photo_link": product_photo_link,
            "length": length,
            "width": width,
            "height": height,
            "manager": manager,
            "articles": [],
        }
