from aiohttp import ClientSession
from fastapi import Depends

# from app.dependencies.repositories.wb_media_repo import get_wb_media_repository
# from app.dependencies.repositories.products_data_repo import ProducsDataRepository, get_products_data_repository
# from app.dependencies.repositories.products_repo import ProductRepository, get_product_repository
# from app.dependencies.http_session import get_wb_http_session
# from app.dependencies.article import get_article_repository, ArticleRepository
# from app.dependencies.card_data import get_card_data_repository, CardDataRepository
# from app.dependencies.card_status import CardStatusService, get_card_status_service
# from app.service.wb_media import WBMediaService
# from app.repository.wb_media import WBMediaRepository


# def get_wb_media_service(
#     products_repo: ProductRepository = Depends(get_product_repository),
#     products_data_repo: ProducsDataRepository = Depends(get_products_data_repository),
#     wb_media_repo: WBMediaRepository = Depends(get_wb_media_repository),
#     article_repo: ArticleRepository = Depends(get_article_repository),
#     card_data_repo: CardDataRepository = Depends(get_card_data_repository),
#     card_status_service: CardStatusService = Depends(get_card_status_service),
#     session: ClientSession = Depends(get_wb_http_session),
# ) -> WBMediaService:
#     return WBMediaService(
#         products_repo=products_repo,
#         products_data_repo=products_data_repo,
#         wb_media_repo=wb_media_repo,
#         article_repo=article_repo,
#         card_data_repo=card_data_repo,
#         card_status_service=card_status_service,
#         session=session,
#     )
