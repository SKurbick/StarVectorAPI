# from asyncpg import Pool
# from fastapi import Depends

# from app.service.subject_data import SubjectDataService
# from app.repository.subject_data import SubjectDataRepository
# from app.dependencies.database import get_pool


# def get_subject_data_repository(
#     pool: Pool = Depends(get_pool)
# ) -> SubjectDataRepository:
#     return SubjectDataRepository(pool)


# def get_subject_data_service(
#     repository: SubjectDataRepository = Depends(get_subject_data_repository)
# ) -> SubjectDataService:
#     return SubjectDataService(repository)
