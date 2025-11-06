import fastapi
from . import controllers

ROUTER = fastapi.APIRouter(
    prefix="/users",
    tags=["usuarios"],
)

for controller in controllers.ALL_CONTROLLERS:
    ROUTER.include_router(controller)