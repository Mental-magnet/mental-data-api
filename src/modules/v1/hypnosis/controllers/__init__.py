from .hypnosis_controller import ROUTER as HYPNOSIS_ROUTER
from .pipeline_controller import router as PIPELINE_ROUTER

ALL_CONTROLLERS = [
    HYPNOSIS_ROUTER,
    PIPELINE_ROUTER,
]