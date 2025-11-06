from .suscribers_controller import ROUTER as SUSCRIBERS_ROUTER
from .users_controller import ROUTER as USERS_ROUTER

ALL_CONTROLLERS = [
    SUSCRIBERS_ROUTER,
    USERS_ROUTER,
]