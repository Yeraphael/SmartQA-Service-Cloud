from fastapi import APIRouter

from app.api.v1.module_system.auth.controller import AuthRouter
from app.api.v1.module_system.params.public_controller import PublicParamsRouter
from app.api.v1.module_system.user.controller import UserRouter

system_router = APIRouter(prefix="/system")

system_router.include_router(AuthRouter)
system_router.include_router(PublicParamsRouter)
system_router.include_router(UserRouter)
