import fastapi
from . import controllers

ROUTER = fastapi.APIRouter(
    prefix="/hypnosis",
    tags=["hipnosis"],
)

for controller in controllers.ALL_CONTROLLERS:
    ROUTER.include_router(controller)