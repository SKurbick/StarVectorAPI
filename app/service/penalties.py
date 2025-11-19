from typing import NoReturn
from fastapi import UploadFile, HTTPException, status

from app.domain.models import DaylyPenaltiesReport, PeriodRequestModel, PenaltyAnnotationUpdate
from app.repository.penalties import PenaltyRepository


class PenaltyService:
    def __init__(self, repository: PenaltyRepository):
        self.repository = repository

    async def get_penalties_details(
        self,
        period: PeriodRequestModel,
    ) -> list[DaylyPenaltiesReport]:
        """Получить данные о штрафах по каждому дню."""
        return await self.repository.get_penalties_details(period)
    
    async def update_penalty_annotation(
        self,
        data: PenaltyAnnotationUpdate,
    ) -> NoReturn:
        """Обновить аннотации к штрафу."""
        return await self.repository.update_penalty_annotation(data)
    
    async def update_penalty_annotations_from_excel(
            self,
            upload_file: UploadFile
    ) -> NoReturn:
        """Обновить данные из Excel файла."""
        if not upload_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимо загрузить Excel файл в формате .xlsx, xlsm"
            )

        return self.repository.update_penalty_annotations_from_excel(upload_file=upload_file)
