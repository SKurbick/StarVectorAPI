from asyncpg import Pool

from app.domain.models import  (
    ProductWBCard,
    ProductWBHealthQueryParams,
    ProductAccountWBHealthDTO,
    ProductBase,
)
from app.domain.enums import GlobalProductWBStatus, ProductWBIssueType, AccountWBIssueType


MAX_PRICE_DEVIATION = 0.2
MIN_VALID_RATING = 4.0


class ProductRepository:
    """Репозиторий для работы с товарами в базе данных."""

    def __init__(self, pool: Pool):
        self.pool = pool

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
            WHERE cs.status IS NULL OR cs.status != 'deleted'
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
        products_accounts_where_clauses = ["1=1"]

        if params.account_ids:
            products_accounts_where_clauses.append(f"account_id = ANY(${param_counter})")
            param_counter += 1
            query_params.append(params.account_ids)

        if params.search:
            products_accounts_where_clauses.append(
                f"(product_id ILIKE ${param_counter} OR product_name ILIKE ${param_counter})"
            )
            param_counter += 1
            query_params.append(f"%{params.search}%")

        sort_expression = self._get_sort_expression(params.sort_by, params.sort_order)

        filtered_products_accounts_cte = f"""
            filtered_products_accounts AS (
                SELECT
                    account_id,
                    account_name,
                    account_vat,
                    product_id,
                    product_name,
                    current_physical_quantity,
                    product_photo_link,
                    active_nm_id,
                    active_rating,
                    active_price,
                    active_vat,
                    active_cards_count,
                    ready_to_activate_nm_id,
                    ready_to_activate_cards_count,
                    is_error_multiple_cards,
                    is_error_vat_mismatch,
                    is_warning_no_active_cards,
                    is_warning_low_rating,
                    (
                        is_warning_no_active_cards = TRUE
                        AND is_warning_ready_to_activate = TRUE
                    ) AS is_warning_ready_to_activate
                FROM mv_wb_product_health_analytics
                WHERE {' AND '.join(products_accounts_where_clauses)}
            )
        """

        product_state_cte = f"""
            product_state AS (
                SELECT
                    product_id,
                    product_name,
                    current_physical_quantity,
                    MIN(active_price) AS min_price,
                    MAX(active_price) AS max_price,
                    bool_or(is_error_multiple_cards) AS is_error_multiple_cards,
                    bool_or(is_error_vat_mismatch) AS is_error_vat_mismatch,
                    bool_or(is_warning_no_active_cards) AS is_warning_no_active_cards,
                    bool_or(is_warning_low_rating) AS is_warning_low_rating,
                    bool_or(is_warning_ready_to_activate) AS is_warning_ready_to_activate,
                    CASE
                        WHEN MIN(active_price) IS NOT NULL
                        AND ((MAX(active_price) - MIN(active_price)) / MIN(active_price)) > 0.2
                        THEN TRUE
                        ELSE FALSE
                    END AS is_warning_price_deviation
                FROM filtered_products_accounts
                GROUP BY product_id, product_name, current_physical_quantity
            )
        """

        global_products_status_where_clauses = ["1=1"]

        if params.issue_type:
            issue_filters = []

            for issue in params.issue_type:
                col = self._get_issue_type_filter_expression(issue)

                if col:
                    issue_filters.append(f"{col} = TRUE")

            if issue_filters:
                global_products_status_where_clauses.append(f"({' AND '.join(issue_filters)})")

        global_product_status_cte = f"""
            global_product_status AS (
                SELECT
                    product_id,
                    product_name,
                    current_physical_quantity,
                    CASE
                        WHEN is_error_multiple_cards = TRUE 
                        OR is_error_vat_mismatch = TRUE 
                        THEN 'has_error'
                        WHEN is_warning_no_active_cards = TRUE 
                        OR is_warning_low_rating = TRUE 
                        OR is_warning_price_deviation = TRUE
                        OR is_warning_ready_to_activate = TRUE 
                        THEN 'has_warning'
                        ELSE 'ok'
                    END AS global_status
                FROM product_state
                WHERE {' AND '.join(global_products_status_where_clauses)}
            )
        """

        main_query_where_clauses = ["1=1"]

        if params.status in GlobalProductWBStatus:
            main_query_where_clauses.append(f"global_status = ${param_counter}")
            param_counter += 1
            query_params.append(params.status)

        limit = params.size
        offset = (params.page - 1) * params.size

        all_cte = f"""
            {filtered_products_accounts_cte},
            {product_state_cte},
            {global_product_status_cte}
        """

        main_query = "WITH " + all_cte + f"""
            SELECT
                fpa.product_id,
                fpa.product_name,
                fpa.product_photo_link,
                fpa.current_physical_quantity,
                fpa.account_id,
                fpa.account_name,
                fpa.account_vat,
                fpa.active_nm_id,
                fpa.active_rating,
                fpa.active_price,
                fpa.active_vat,
                fpa.active_cards_count,
                fpa.ready_to_activate_nm_id,
                fpa.ready_to_activate_cards_count,
                fpa.is_error_multiple_cards,
                fpa.is_error_vat_mismatch,
                fpa.is_warning_no_active_cards,
                fpa.is_warning_low_rating,
                fpa.is_warning_ready_to_activate,
                ps.min_price,
                ps.max_price,
                ps.is_warning_price_deviation,
                gps.global_status,
                gps.total_count
            FROM (
                SELECT 
                    product_id,
                    product_name,
                    current_physical_quantity,
                    global_status,
                    COUNT(*) OVER() AS total_count
                FROM global_product_status gps
                WHERE {' AND '.join(main_query_where_clauses)}
                ORDER BY {sort_expression}
                LIMIT ${param_counter} OFFSET ${param_counter + 1}
            ) gps
            LEFT JOIN product_state ps ON gps.product_id = ps.product_id
            LEFT JOIN filtered_products_accounts fpa ON gps.product_id = fpa.product_id
            ORDER BY {sort_expression}, fpa.account_id ASC
        """

        param_counter += 2
        query_params.extend((limit, offset))
        rows = await self.pool.fetch(main_query, *query_params)
        return [ProductAccountWBHealthDTO(**row) for row in rows]

    def _get_sort_expression(self, sort_by: str, sort_order: str) -> str:
        allowed_columns = {
            "product_id": "gps.product_id",
            "product_name": "gps.product_name",
            "current_physical_quantity": "gps.current_physical_quantity",
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
            AccountWBIssueType.READY_TO_ACTIVATE: "is_warning_ready_to_activate",
        }
        return allowed_columns.get(issue)

    async def get_products_by_wb_subject(
            self,
            subject_id: int,
    ) -> list[ProductBase]:
        """Получить список товаров по предметам."""
        query = """
            SELECT
                p.id AS product_id,
                p.name AS product_name,
                mvph.product_photo_link
            FROM products p
            LEFT JOIN products_data pd ON p.id = pd.product_id
            JOIN (
                SELECT
                    product_id,
                    product_name,
                    MAX(product_photo_link) AS product_photo_link
                FROM mv_wb_product_health_analytics
                GROUP BY product_id, product_name
            ) mvph ON p.id = mvph.product_id
            WHERE pd.wb_subject_id = $1
            ORDER BY p.id
        """

        rows = await self.pool.fetch(query, subject_id)

        return [ProductBase(**row) for row in rows]
