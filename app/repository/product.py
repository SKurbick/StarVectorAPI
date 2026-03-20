from collections import defaultdict
import json

from asyncpg import Pool

from app.domain.models import  (
    ArticleResponse,
    ProductResponse,
    SubjectDataWithProductsResponse,
    ProductWBCard,
    ProductWBHealthQueryParams,
    ProductAccountWBHealthDTO,
)
from app.domain.enums import GlobalProductWBStatus, ProductWBIssueType, AccountWBIssueType


MAX_PRICE_DEVIATION = 0.2
MIN_VALID_RATING = 4.0


class ProductRepository:
    """Репозиторий для работы с товарами в базе данных."""

    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_products_grouped_by_subjects(
        self,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[SubjectDataWithProductsResponse]:
        """Получить список товаров с группировкой по предметам."""
        query = """
            WITH all_cards_data AS (
                SELECT
                    a.local_vendor_code,
                    cd.subject_name,
                    json_agg(
                        json_build_object(
                            'article_id', cd.article_id,
                            'photo_link', cd.photo_link,
                            'price', cd.price,
                            'discount', cd.discount,
                            'length', cd.length,
                            'width', cd.width,
                            'height', cd.height,
                            'barcode', cd.barcode,
                            'rating', cd.rating,
                            'manager', cd.manager
                        )
                    ) AS cards
                FROM
                    article a
                INNER JOIN
                    card_data AS cd
                    ON a.nm_id = cd.article_id
                GROUP BY
                    a.local_vendor_code, cd.subject_name
            )
            SELECT
                p.id,
                p.name,
                p.photo_link,
                p.length,
                p.width,
                p.height,
                p.manager,
                acd.subject_name,
                coalesce(acd.cards, '[]') AS articles
            FROM
                products p
            LEFT JOIN
                all_cards_data acd
                ON acd.local_vendor_code = p.id
            ORDER BY acd.subject_name, p.name
            LIMIT $1
            OFFSET $2;
        """

        async with self.pool.acquire() as connection:
            data = await connection.fetch(query, limit, offset)

        subjects_dict = defaultdict(list)

        for row in data:
            subject_name = row["subject_name"]
            articles_data = json.loads(row["articles"])

            articles = [ArticleResponse(**article) for article in articles_data]

            product = ProductResponse(
                id=row["id"],
                name=row["name"],
                photo_link=row["photo_link"],
                length=row["length"],
                width=row["width"],
                height=row["height"],
                manager=row["manager"],
                articles=articles,
            )

            subjects_dict[subject_name].append(product)

        return [SubjectDataWithProductsResponse(
            subject_name=name,
            products=products
        ) for name, products in subjects_dict.items()]

    async def get_product_wb_cards(self, product_id: str) -> list[ProductWBCard]:
        """Получить все карточки товара."""
        query = """
            WITH product_cards AS (
                SELECT
                    a.nm_id,
                    a.account,
                    a.vendor_code,
                    a.local_vendor_code
                FROM article a 
                WHERE a.local_vendor_code = $1
            ),
            card_statuses AS (
                SELECT
                    cs.nm_id,
                    cs.status
                FROM card_status cs
                WHERE cs.nm_id IN (
                    SELECT nm_id
                    FROM product_cards
                )
            ),
            prices AS (
                SELECT DISTINCT ON (pc.local_vendor_code, pc.nm_id)
                    pc.local_vendor_code,
                    pc.nm_id,
                    sh.spp_price AS price,
                    ROUND(sh.spp_percent::NUMERIC, 0) AS discount
                FROM product_cards pc
                LEFT JOIN spp_history sh ON pc.nm_id = sh.nm_id
                ORDER BY pc.local_vendor_code, pc.nm_id, created_at DESC
            ),
            stocks AS (
                SELECT
                    csq.article_id,
                    csq.quantity
                FROM current_stocks_quantity csq
                WHERE csq.article_id IN (
                    SELECT nm_id
                    FROM product_cards
                )
                AND quantity_type = 'ФБС'
            )
            SELECT
                pc.nm_id,
                pc.account,
                pc.vendor_code,
                pc.local_vendor_code,
                COALESCE(cs.status, 'active') AS status,
                cd.barcode,
                cd.rating,
                cd.photo_link AS small_photo_link,
                cd.wb_name AS name,
                cd.wb_description AS description,
                p.price,
                p.discount,
                COALESCE(s.quantity, 0) AS fbs_stock_quantity
            FROM product_cards pc
            LEFT JOIN card_statuses cs
                ON pc.nm_id = cs.nm_id
            LEFT JOIN prices p
                ON p.nm_id = pc.nm_id
            LEFT JOIN card_data cd
                ON cd.article_id = pc.nm_id 
            LEFT JOIN stocks s
                ON s.article_id = pc.nm_id
            ORDER BY pc.account, pc.vendor_code
        """

        rows = await self.pool.fetch(query, product_id)
        return [ProductWBCard(**row) for row in rows]

    async def check_product_exists(self, product_id: str) -> bool:
        """Проверить, существует ли товар."""
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM products
                WHERE id = $1
            );
        """

        return await self.pool.fetchval(query, product_id)

    async def get_products_wb_health_analitics(
            self,
            params: ProductWBHealthQueryParams
    ) -> list[ProductAccountWBHealthDTO]:
        
        query_params = []
        param_counter = 1
        where_clauses = ["1=1"]

        if params.account_ids:
            where_clauses.append(f"account_id = ANY(${param_counter})")
            param_counter += 1
            query_params.append(params.account_ids)

        if params.search:
            where_clauses.append(f"(product_id ILIKE ${param_counter} OR product_name ILIKE ${param_counter})")
            param_counter += 1
            query_params.append(f"%{params.search}%")

        if params.issue_type:
            issue_filters = []
            for issue in params.issue_type:
                col = self._get_issue_type_filter_expression(issue)
                if col:
                    issue_filters.append(f"{col} = TRUE")
            if issue_filters:
                where_clauses.append(f"({' OR '.join(issue_filters)})")

        if params.status in GlobalProductWBStatus:
            where_clauses.append(f"global_status = ${param_counter}")
            param_counter += 1
            query_params.append(params.status)

        sort_expression = self._get_sort_expression(params.sort_by, params.sort_order)
        limit = params.size
        offset = (params.page - 1) * params.size

        query = f"""
            WITH paginated_products AS (
                SELECT DISTINCT product_id
                FROM mv_wb_product_health_analytics
                WHERE {' AND '.join(where_clauses)}
                ORDER BY {sort_expression}
                LIMIT ${param_counter} OFFSET ${param_counter + 1}
            ),
            total_count_cte AS (
                SELECT COUNT(DISTINCT product_id) AS total_count
                FROM mv_wb_product_health_analytics
                WHERE {' AND '.join(where_clauses)}
            )
            SELECT
                mv.account_id,
                mv.account_name,
                mv.account_vat,
                mv.product_id,
                mv.product_name,
                mv.active_photo_link,
                mv.active_cards_count,
                mv.current_vat,
                mv.best_rating,
                mv.active_price,
                mv.is_error_multiple_cards,
                mv.is_error_vat_mismatch,
                mv.is_warning_no_active_cards,
                mv.is_warning_low_rating,
                mv.is_warning_price_deviation,
                mv.global_status,
                mv.max_price,
                mv.min_price,
                tc.total_count
            FROM mv_wb_product_health_analytics mv
            JOIN paginated_products pp ON mv.product_id = pp.product_id
            CROSS JOIN total_count_cte tc
            ORDER BY {sort_expression}, mv.account_name ASC
        """

        param_counter += 2
        query_params.extend((limit, offset))

        rows = await self.pool.fetch(query, *query_params)
        return [ProductAccountWBHealthDTO(**row) for row in rows]

    def _get_sort_expression(self, sort_by: str, sort_order: str) -> str:
        allowed_columns = {
            "product_id": "product_id",
            "product_name": "product_name",
        }
        column = allowed_columns.get(sort_by, "product_id")
        order = "ASC" if sort_order == "asc" else "DESC"
        return f"{column} {order} NULLS LAST"

    def _get_issue_type_filter_expression(self, issue) -> str | None:
        allowed_columns = {
            ProductWBIssueType.PRICE_DEVIATION: "is_warning_price_deviation",
            AccountWBIssueType.NO_ACTIVE_CARDS: "is_warning_no_active_cards",
            AccountWBIssueType.MULTIPLE_ACTIVE_CARDS: "is_error_multiple_cards",
            AccountWBIssueType.VAT_MISMATCH: "is_error_vat_mismatch",
            AccountWBIssueType.LOW_RATING: "is_warning_low_rating",
        }
        return allowed_columns.get(issue)
