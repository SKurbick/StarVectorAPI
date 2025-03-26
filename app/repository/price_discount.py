from typing import List

from asyncpg import Pool
from app.domain.models import PriceDiscountResponseModel, PriceDiscountDB


class PriceDiscountRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def update_price_and_discount_data(self, update_data: List[PriceDiscountDB]):
        a_ids, prices, discounts = [], [], []
        for data in update_data:
            a_ids.append(data.article_id)
            prices.append(data.price)
            discounts.append(data.discount)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Шаг 1: Создаем временную таблицу
                await conn.execute("""
                    CREATE TEMP TABLE _temp_articles 
                    (article_id INT PRIMARY KEY, price INT, discount INT) 
                    ON COMMIT DROP;
                """)

                # Шаг 2: Вставляем данные во временную таблицу
                await conn.execute("""
                    INSERT INTO _temp_articles (article_id, price, discount)
                    SELECT * FROM UNNEST($1::INT[], $2::INT[], $3::INT[]);
                """, a_ids, prices, discounts)

                # Шаг 3: Обновляем таблицу в card_data
                await conn.execute("""
                    UPDATE card_data AS cd
                    SET 
                        price = COALESCE(t.price, cd.price),
                        discount = COALESCE(t.discount, cd.discount)
                    FROM _temp_articles AS t
                    WHERE cd.article_id = t.article_id;
                """)
                # Шаг 4: Обновляем таблицу unit_economics
                await conn.execute("""
                    UPDATE unit_economics AS ue
                    SET 
                        price = COALESCE(t.price, ue.price),
                        discount = COALESCE(t.discount, ue.discount)
                    FROM _temp_articles AS t
                    WHERE ue.article_id = t.article_id;
                """)
