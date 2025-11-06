from typing import Optional

from asyncpg import Pool

from app.domain.enums import CardStatusEnum


class CardStatusRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_cards_by_status(
        self,
        nm_ids: Optional[list[int]] = None,
        statuses: Optional[list[CardStatusEnum]] = None,
        exclude_statuses: Optional[list[CardStatusEnum]] = None,
    ) -> dict[str, list[int]]:
        """
        Возвращает карточки, сгруппированные по аккаунтам.
        """
        query = "SELECT account, nm_id FROM card_status WHERE 1=1"
        params = []
        param_index = 1

        if nm_ids is not None:
            if not nm_ids:
                return {}

            query += f" AND nm_id = ANY(${param_index})"
            params.append(nm_ids)
            param_index += 1

        if statuses is not None:
            query += f" AND status = ANY(${param_index})"
            params.append(statuses)
            param_index += 1

        if exclude_statuses is not None:
            query += f" AND status != ANY(${param_index})"
            params.append(exclude_statuses)
            param_index += 1

        query += " ORDER BY account"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        result = {}

        for row in rows:
            account = row["account"]

            if account not in result:
                result[account] = []

            result[account].append(row["nm_id"])

        return result

    async def update_card_status(
        self,
        account: str,
        nm_ids: list[int],
        new_status: CardStatusEnum,
        from_status: Optional[CardStatusEnum] = None,
    ) -> list[int]:
        """
        Универсальный метод обновления статуса карточек.
        
        Args:
            account: аккаунт
            nm_ids: список nm_id
            new_status: целевой статус
            from_status: если указан — обновлять только из этого статуса
        """
        if not nm_ids:
            return []

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                where_clause = "account = $1 AND nm_id = ANY($2)"
                params = [account, nm_ids]

                if from_status is not None:
                    where_clause += " AND status = $3"
                    params.append(from_status)

                query_select = f"""
                    SELECT nm_id, status
                    FROM card_status
                    WHERE {where_clause}
                    FOR UPDATE
                """

                rows = await conn.fetch(query_select, *params)
                current = {row["nm_id"]: row["status"] for row in rows}

                to_update = []

                for nm_id in nm_ids:
                    current_status = current.get(nm_id)

                    if from_status is not None and current_status != from_status:
                        continue

                    if current_status == new_status:
                        continue

                    to_update.append(nm_id)

                if not to_update:
                    return []

                upsert_query = """
                    INSERT INTO card_status (nm_id, account, status, updated_at)
                    SELECT unnest($1::bigint[]), $2, $3, NOW()
                    ON CONFLICT (nm_id, account)
                    DO UPDATE SET status = $3, updated_at = NOW()
                """
                await conn.execute(upsert_query, to_update, account, new_status)

                log_query = """
                    INSERT INTO card_status_log (nm_id, account, status, changed_at)
                    SELECT unnest($1::bigint[]), $2, $3, NOW()
                """
                await conn.execute(log_query, to_update, account, new_status)

                return to_update

    async def get_status_by_nm_ids(self, nm_ids: list[int]) -> dict[int, str]:
        """
        Возвращает {nm_id: status} для существующих записей в card_status.
        Если запись отсутствует — nm_id не будет в результате (считается 'active').
        """
        if not nm_ids:
            return {}

        query = "SELECT nm_id, status FROM card_status WHERE nm_id = ANY($1)"
        rows = await self.pool.fetch(query, nm_ids)

        return {row["nm_id"]: row["status"] for row in rows}
