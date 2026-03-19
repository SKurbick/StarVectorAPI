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

        filtered_accounts_clauses = ""
        if params.account_ids:
            filtered_accounts_clauses = f"AND sa.id = ANY(${param_counter})"
            param_counter += 1
            query_params.append(params.account_ids)

        filtered_accounts_cte = f"""
            filtered_accounts AS (
                SELECT 
                    sa.id AS account_id,
                    sa.account_name,
                    sa.vat_rate AS account_vat
                FROM seller_account sa
                WHERE sa.is_active = TRUE {filtered_accounts_clauses}
                ORDER BY sa.account_name ASC
            )
        """

        filtered_products_clauses = ""
        if params.search:
            filtered_products_clauses = f"""
                AND (p.id ILIKE '%' || ${param_counter} || '%'
                    OR p.name ILIKE '%' || ${param_counter} || '%')
            """
            param_counter += 1
            query_params.append(params.search)

        filtered_products_cte = f"""
            filtered_products AS (
                SELECT
                    p.id AS product_id,
                    p.name AS product_name
                FROM products p
                WHERE p.is_active = TRUE {filtered_products_clauses}
            )
        """

        cards_with_stocks_cte = """
            cards_with_stocks AS (
                SELECT 
                    csq.article_id AS nm_id,
                    a.local_vendor_code,
                    a.account AS account_name
                FROM current_stocks_quantity csq
                INNER JOIN article a ON a.nm_id = csq.article_id
                INNER JOIN filtered_accounts fa ON a.account = fa.account_name
                INNER JOIN filtered_products fp ON a.local_vendor_code = fp.product_id
                GROUP BY csq.article_id, a.local_vendor_code, a.account
                HAVING SUM(csq.quantity) > 0
            )
        """

        prices_cte = """
            prices AS (
                SELECT DISTINCT ON (cws.local_vendor_code, cws.nm_id)
                    cws.nm_id,
                    sh.spp_price AS price
                FROM cards_with_stocks cws
                LEFT JOIN spp_history sh ON cws.nm_id = sh.nm_id
                ORDER BY cws.local_vendor_code, cws.nm_id, sh.created_at DESC
            )
        """

        ranked_active_cards_cte = """
            ranked_active_cards AS (
                SELECT 
                    cws.nm_id,
                    cws.local_vendor_code,
                    cws.account_name,
                    pr.price,
                    cd.vat_rate,
                    cd.rating,
                    ROW_NUMBER() OVER (
                        PARTITION BY cws.local_vendor_code, cws.account_name 
                        ORDER BY cd.rating DESC NULLS LAST, cws.nm_id ASC
                    ) AS rn,
                    COUNT(*) OVER (PARTITION BY cws.local_vendor_code, cws.account_name) AS total_active_count
                FROM cards_with_stocks cws
                LEFT JOIN prices pr ON cws.nm_id = pr.nm_id
                LEFT JOIN card_data cd ON cd.article_id = cws.nm_id
            )
        """

        product_price_stats_cte = """
            product_price_stats AS (
                SELECT 
                    local_vendor_code,
                    MIN(price) AS min_price,
                    MAX(price) AS max_price,
                    COUNT(*) AS accounts_with_price
                FROM ranked_active_cards
                WHERE price IS NOT NULL
                GROUP BY local_vendor_code
            )
        """

        products_metrics_cte = """
            products_metrics AS (
                SELECT
                    fa.account_id,
                    fa.account_name,
                    fa.account_vat,
                    fp.product_id,
                    fp.product_name,
                    rac.nm_id,
                    COALESCE(rac.total_active_count, 0) AS active_cards_count,
                    rac.vat_rate AS current_vat,
                    rac.rating AS best_rating,
                    rac.price AS active_price
                FROM filtered_products fp
                CROSS JOIN filtered_accounts fa
                LEFT JOIN ranked_active_cards rac 
                    ON rac.local_vendor_code = fp.product_id 
                    AND rac.account_name = fa.account_name 
                    AND rac.rn = 1
            )
        """

        account_state_cte = f"""
            account_state AS (
                SELECT 
                    pm.account_id,
                    pm.product_id,
                    pm.product_name,
                    (pm.active_cards_count > 1) AS is_error_multiple_cards,
                    (pm.account_vat IS NOT NULL AND pm.current_vat IS NOT NULL AND pm.account_vat != pm.current_vat) AS is_error_vat_mismatch,
                    (pm.active_cards_count IS null or pm.active_cards_count < 1) AS is_warning_no_active_cards,
                    (pm.best_rating IS NOT NULL AND pm.best_rating < {MIN_VALID_RATING}) AS is_warning_low_rating
                FROM products_metrics pm
            )
        """

        product_filters_cte = f"""
            product_filters AS (
                SELECT
                    acst.product_id,
                    acst.product_name,
                    MAX(acst.is_error_multiple_cards::int) AS is_error_multiple_cards,
                    MAX(acst.is_error_vat_mismatch::int) AS is_error_vat_mismatch,
                    MAX(acst.is_warning_no_active_cards::int) AS is_warning_no_active_cards,
                    MAX(acst.is_warning_low_rating::int) AS is_warning_low_rating,
                    MAX((
                        pps.min_price IS NOT NULL AND pps.min_price > 0
                        AND ((pps.max_price - pps.min_price) / pps.min_price) > {MAX_PRICE_DEVIATION}
                    )::int) AS is_warning_price_deviation,
                    CASE
                        WHEN MAX(acst.is_error_multiple_cards::int) = 1 
                            OR MAX(acst.is_error_vat_mismatch::int) = 1 
                        THEN 'has_error'
                        WHEN MAX(acst.is_warning_no_active_cards::int) = 1 
                            OR MAX(acst.is_warning_low_rating::int) = 1 
                            OR MAX((
                                pps.min_price IS NOT NULL AND pps.min_price > 0
                                AND ((pps.max_price - pps.min_price) / pps.min_price) > {MAX_PRICE_DEVIATION}
                            )::int) = 1 
                        THEN 'has_warning'
                        ELSE 'ok'
                    END AS global_status
                FROM account_state acst
                LEFT JOIN product_price_stats pps ON acst.product_id = pps.local_vendor_code
                GROUP BY acst.product_id, acst.product_name
            )
        """

        issue_where_clauses = []
        if params.issue_type:
            for issue in params.issue_type:
                issue_where_clauses.append(f" AND {self._get_issue_type_filter_expression(issue)}")

        status_clause = ""
        if params.status in GlobalProductWBStatus:
            status_clause = f" AND pf.global_status = ${param_counter}"
            param_counter += 1
            query_params.append(params.status)

        limit = params.size
        offset = (params.page - 1) * params.size
        sort_expression = self._get_sort_expression(params.sort_by, params.sort_order)

        paginated_products_cte = f"""
            paginated_products AS (
                SELECT
                    pf.product_id,
                    COUNT(*) OVER () AS total_count
                FROM product_filters pf
                WHERE 1=1
                {"".join(issue_where_clauses)}
                {status_clause}
                ORDER BY {sort_expression}
                LIMIT ${param_counter} OFFSET ${param_counter + 1}
            )
        """

        param_counter += 2 
        query_params.extend((limit, offset))

        all_cte = f"""WITH
            {filtered_accounts_cte},
            {filtered_products_cte},
            {cards_with_stocks_cte},
            {prices_cte},
            {ranked_active_cards_cte},
            {product_price_stats_cte},
            {products_metrics_cte},
            {account_state_cte},
            {product_filters_cte},
            {paginated_products_cte}
        """

        final_sort_expression = self._get_sort_expression(params.sort_by, params.sort_order).replace("pf.", "pm.")

        full_query = all_cte + f"""
            SELECT
                pm.account_id,
                pm.account_name,
                pm.account_vat,
                pm.product_id,
                pm.product_name,
                pm.active_cards_count,
                pm.current_vat,
                pm.best_rating,
                pm.active_price,
                ac.is_error_multiple_cards,
                ac.is_error_vat_mismatch,
                ac.is_warning_no_active_cards,
                ac.is_warning_low_rating,
                (pf.is_warning_price_deviation = 1) AS is_warning_price_deviation,
                pf.global_status,
                pps.max_price,
                pps.min_price,
                pp.total_count
            FROM paginated_products pp
            JOIN products_metrics pm ON pp.product_id = pm.product_id
            JOIN account_state ac ON pm.product_id = ac.product_id AND pm.account_id = ac.account_id
            JOIN product_filters pf ON pp.product_id = pf.product_id
            LEFT JOIN product_price_stats pps ON pf.product_id = pps.local_vendor_code
            ORDER BY {final_sort_expression}, pm.account_name ASC
        """

        rows = await self.pool.fetch(full_query, *query_params)
        return [ProductAccountWBHealthDTO(**row) for row in rows]

    def _get_sort_expression(self, sort_by: str, sort_order: str) -> str:
        allowed_columns = {
            "product_id": "pf.product_id",
            "product_name": "pf.product_name",
        }
        column = allowed_columns.get(sort_by, "pf.product_id")
        order = "ASC" if sort_order == "asc" else "DESC"
        return f"{column} {order} NULLS LAST"

    def _get_issue_type_filter_expression(self, issue: AccountWBIssueType | ProductWBIssueType) -> str:
        allowed_columns = {
            ProductWBIssueType.PRICE_DEVIATION: "pf.is_warning_price_deviation",
            AccountWBIssueType.NO_ACTIVE_CARDS: "pf.is_warning_no_active_cards",
            AccountWBIssueType.MULTIPLE_ACTIVE_CARDS: "pf.is_error_multiple_cards",
            AccountWBIssueType.VAT_MISMATCH: "pf.is_error_vat_mismatch",
            AccountWBIssueType.LOW_RATING: "pf.is_warning_low_rating",
        }

        column = allowed_columns.get(issue, 1)
        return f"{column} = 1"
