from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import ConversationDetailSchema, ConversationQueryParam
from .service import ConversationService

ConversationRouter = APIRouter(route_class=OperationLogRoute, prefix="/conversations", tags=["SmartQA", "会话"])
router = ConversationRouter  # Alias for router import


@ConversationRouter.get("/list", summary="会话列表", response_model=ResponseSchema[dict])
async def get_conversation_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ConversationQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
) -> JSONResponse:
    result = await ConversationService(auth).page(page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="查询会话列表成功")


@ConversationRouter.get("/detail/{id}", summary="会话详情", response_model=ResponseSchema[ConversationDetailSchema])
async def get_conversation_detail_controller(
    id: Annotated[int, Path(description="会话主键ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission())],
) -> JSONResponse:
    result = await ConversationService(auth).detail(id=id)
    return SuccessResponse(data=result, msg="查询会话详情成功")
