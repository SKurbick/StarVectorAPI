from abc import ABC, abstractmethod
from typing import Optional

from asyncpg import Pool


class BaseCardService(ABC):
    def __init__(
        self, 
        pool: Pool,
        nm_ids: Optional[list[int]] = None,
        local_vendor_codes: Optional[list[str]] = None,
    ) -> None:
        self.nm_ids = nm_ids
        self.local_vendore_codes = local_vendor_codes
        self.pool = pool
    
    @abstractmethod
    async def execute(self):
        raise NotImplementedError
