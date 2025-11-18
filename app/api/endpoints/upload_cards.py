from fastapi import APIRouter, Body

from app.domain.models import CreateCardsRequest, CreateCardsResponse


router = APIRouter(tags=["Создание карточек товара на маркетплейсах"])

upload_cards_request_example = {  
	"local_vendor_code": "wild123",
	"marketplaces": [
		{
			"name": "wildberries",
			"data": {
				"subject_id": 105,
				"brand": "MyBrand",
				"dimensions": {
					"length": 12,
					"width": 7,
					"height": 5,
					"weightBrutto": 0.950
				},
				"characteristics": [
					{
						"id": 12,
						"value": ["red"]
					},
					{
						"id": 25471,
						"value": 1200
					}
				],
				"sizes": [
					{
						"tech_size": "S",
						"ru_size": "44"
					},
					{
						"tech_size": "M",
						"ru_size": "46"
					}
				],
				"accounts": [
					{
						"account_id": 101,
						"cards_count": 3
					}
				]
			}
		}
	]
}


@router.post("/cards/upload")
async def upload_cards(
    data: CreateCardsRequest = Body(..., example=upload_cards_request_example)
) -> CreateCardsResponse:
    return {
		"task_id": "task_abc123xyz789",
		"timestamp": "2025-11-12T10:04:42.105207",
		"status": "pending",
		"summary": {
		"total_cards_to_create": 3,
		"marketplaces_count": 1,
		"accounts_count": 1
		},
		"details": [
			{
				"local_vendor_code": "wild123",
				"title": "Бутылка для воды пластиковая с крышкой",
				"marketplaces": [
					{
						"marketplace": "wildberries",
						"data": {
							"subject": "Бутылка для воды",
							"brand": "MyBrand"
						},
						"accounts": [
							{
								"account": "СТАРТ",
								"cards_count_requested": 1,
								"cards_to_create": [
									{
										"vendor_code": "wild123/d123",
										"status": "pending_creating",
										"updated_at": "2025-11-12T10:04:42.105207"
									}
								]
							}
						]
					}
				]
			}
		]
	}
