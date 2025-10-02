from asyncpg import Pool, Record
from collections import defaultdict
from typing import Any

from app.domain.models import  ArticleResponse, ProductResponse, SubjectDataWithProductsResponse, CreateProduct


ProductsData = defaultdict[str, str | int | None | list[ArticleResponse]]
SubjectsData = defaultdict[str, ProductsData]


class ProductRepository:
    """Репозиторий для работы с товарами в базе данных."""

    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_product(self, product_id: str) -> ProductResponse:
        pass

    async def create_product(self, data: CreateProduct) -> ProductResponse:
        pass

    async def update_product(self, product_id: str, data: CreateProduct) -> ProductResponse:
        pass

    async def delete_product(self, product_id: str) -> ProductResponse:
        pass

    async def get_products_grouped_by_subjects(
        self,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[SubjectDataWithProductsResponse]:
        """Получить список товаров с группировкой по предметам."""
        async with self.pool.acquire() as connection:
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
            ORDER BY
                cd.subject_name,
                p.id
            LIMIT $1
            OFFSET $2;
            """

            data = await connection.fetch(query, limit, offset)

        return self.__transform_asyncpg_data_to_subjects_response(data)

    @classmethod
    def __transform_asyncpg_data_to_subjects_response(
        cls,
        data: list[Record]
    ) -> SubjectDataWithProductsResponse:
        """Привести сырые данные из БД в структурированный ответ."""
        subjects_data = cls.__transform_asyncpg_data_to_subject_data(data)
        transformed_data = cls.__transform_subject_data_to_response(subjects_data)

        return transformed_data

    @staticmethod
    def __transform_subject_data_to_response(
        subjects_data: SubjectsData
    ) -> list[SubjectDataWithProductsResponse]:
        result = []

        for subject_name, products_dict in subjects_data.items():
            products_list = []

            for product_data in products_dict.values():
                product_response = ProductResponse(
                    id=product_data["id"],
                    name=product_data["name"],
                    photo_link=product_data["photo_link"],
                    length=product_data["length"],
                    width=product_data["width"],
                    height=product_data["height"],
                    manager=product_data["manager"],
                    articles=product_data["articles"],
                )
                products_list.append(product_response)

            subject_response = SubjectDataWithProductsResponse(
                subject_name=subject_name,
                products=products_list,
            )

            result.append(subject_response)

        return result
    
    @classmethod
    def __transform_asyncpg_data_to_subject_data(
        cls,
        data: list[Record]
    ) -> SubjectsData:
        subjects_data = defaultdict(lambda: defaultdict(dict))

        for row in data:
            row_data = dict(row)

            product_id = row_data["id"]
            subject_name = row_data["subject_name"]

            # добавляем данные о товарах в предмет
            if product_id not in subjects_data[subject_name]:
                subjects_data[subject_name][product_id] = cls.__get_product_dict_from_all_data(row_data)

            article_data = cls.__get_article_dict_from_all_data(row_data)

            if article_data:
                new_article = ArticleResponse(
                    **cls.__get_article_dict_from_all_data(row_data)
                )

                # добавляем данные о карточке товара в список
                subjects_data[subject_name][product_id]["articles"].append(new_article)

        return subjects_data
    
    @staticmethod
    def __get_article_dict_from_all_data(data: dict) -> dict[str, Any] | None:
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
    def __get_product_dict_from_all_data(data: dict) -> dict[str, Any]:
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
