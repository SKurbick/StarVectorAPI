from abc import ABC, abstractmethod
from typing import Optional


class BaseCardService(ABC):
    def __init__(
        self, nm_ids: Optional[list[int]],
        local_vendor_codes: Optional[list[str]],
    ) -> None:
        self.nm_ids = nm_ids
        self.local_vendore_codes = local_vendor_codes
    
    @abstractmethod
    async def execute(self):
        raise NotImplementedError
