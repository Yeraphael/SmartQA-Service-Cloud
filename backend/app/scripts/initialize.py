import asyncio
import json
import re
from datetime import datetime, time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_platform.menu.model import MenuModel
from app.api.v1.module_platform.tenant.model import TenantModel, TenantUserModel
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.dict.model import DictDataModel, DictTypeModel
from app.api.v1.module_system.params.model import ParamsModel
from app.api.v1.module_system.position.model import PositionModel
from app.api.v1.module_system.role.model import RoleMenusModel, RoleModel
from app.api.v1.module_system.user.model import UserModel, UserRolesModel
from app.config.path_conf import SCRIPT_DIR
from app.core.database import async_db_session, create_tables
from app.core.logger import logger
from app.plugin.module_smartqa.models.conversation import (
    DwdCustomerStaffRelationModel,
    DwdQnConversationModel,
    DwdQnMessageModel,
)
from app.plugin.module_smartqa.models.dimension import (
    DimCustomerIdentityModel,
    DimCustomerModel,
    DimProductModel,
    DimShopModel,
    DimStaffAccountModel,
    DimStaffModel,
)
from app.plugin.module_smartqa.models.ods import (
    OdsImportBatchModel,
    OdsQnChatRecordModel,
    OdsQnShopRecordModel,
)
from app.plugin.module_smartqa.models.qc import (
    ModelCallLogModel,
    QcIssueEvidenceModel,
    QcIssueModel,
    QcPromptTemplateModel,
    QcResultModel,
    QcRuleModel,
    QcRuleVersionModel,
    QcTaskModel,
)


class InitializeData:
    """Create required SmartQA tables and seed the minimal base data."""

    _DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
    _DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    _TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}(\.\d+)?$")

    prepare_init_models: list[type] = [
        TenantModel,
        MenuModel,
        ParamsModel,
        DeptModel,
        RoleModel,
        DictTypeModel,
        DictDataModel,
        PositionModel,
        UserModel,
        UserRolesModel,
        TenantUserModel,
        OdsImportBatchModel,
        OdsQnChatRecordModel,
        OdsQnShopRecordModel,
        DimShopModel,
        DimProductModel,
        DimStaffModel,
        DimStaffAccountModel,
        DimCustomerModel,
        DimCustomerIdentityModel,
        DwdQnConversationModel,
        DwdQnMessageModel,
        DwdCustomerStaffRelationModel,
        QcRuleModel,
        QcPromptTemplateModel,
        QcRuleVersionModel,
        QcTaskModel,
        QcResultModel,
        QcIssueModel,
        QcIssueEvidenceModel,
        ModelCallLogModel,
    ]

    _RECURSIVE_TABLES: set[str] = {"platform_menu", "sys_dept"}

    async def init_db(self) -> None:
        try:
            await create_tables()
        except asyncio.exceptions.TimeoutError:
            logger.error("database table initialization timed out")
            raise

        async with async_db_session() as session:
            async with session.begin():
                await self.__init_data(session)

    async def __init_data(self, db: AsyncSession) -> None:
        dict_type_mapping: dict[str, Any] = {}

        for model in self.prepare_init_models:
            table_name = model.__tablename__
            data = await self.__load_json(table_name)
            if not data:
                logger.info(f"skip {table_name}: no seed data")
                continue

            try:
                count = await db.execute(select(func.count()).select_from(model))
                if count.scalar():
                    logger.info(f"skip {table_name}: table already has data")
                    continue

                if table_name in self._RECURSIVE_TABLES:
                    db.add_all(self.__create_objects_with_children(data, model))
                    await db.flush()
                    logger.info(f"seeded {table_name}")
                    continue

                if table_name == "sys_dict_type":
                    objs = []
                    for item in data:
                        obj = model(**item)
                        objs.append(obj)
                        dict_type_mapping[item["dict_type"]] = obj
                    db.add_all(objs)
                    await db.flush()
                    logger.info("seeded sys_dict_type")
                    continue

                if table_name == "sys_dict_data":
                    objs = []
                    for item in data:
                        dict_type_str = item.get("dict_type")
                        if dict_type_str not in dict_type_mapping:
                            logger.warning(f"skip dict data without type: {dict_type_str}")
                            continue
                        item["dict_type_id"] = dict_type_mapping[dict_type_str].id
                        objs.append(model(**item))
                    db.add_all(objs)
                    await db.flush()
                    logger.info("seeded sys_dict_data")
                    continue

                db.add_all([model(**item) for item in data])
                await db.flush()
                logger.info(f"seeded {table_name}")
            except Exception:
                logger.exception(f"failed to seed {table_name}")
                raise

        await self.__ensure_role_menu_bindings(db)

    async def __ensure_role_menu_bindings(self, db: AsyncSession) -> None:
        role_rows = await db.execute(select(RoleModel).where(RoleModel.code.in_(["smartqa_boss", "smartqa_staff"])))
        role_map = {role.code: role for role in role_rows.scalars().all()}
        if "smartqa_boss" not in role_map or "smartqa_staff" not in role_map:
            return

        menu_rows = await db.execute(select(MenuModel).where(MenuModel.status == 0))
        menu_map = {menu.title or menu.name: menu for menu in menu_rows.scalars().all()}

        boss_titles = [
            "SmartQA",
            "工作台总览",
            "千牛数据源",
            "会话管理",
            "AI质检任务",
            "质检结果",
            "客服表现",
            "质检规则",
            "客服账号",
        ]
        staff_titles = ["SmartQA", "我的工作台", "我的会话", "我的质检结果", "我的改进建议"]

        await self.__bind_role_menus(db, role_map["smartqa_boss"].id, [menu_map[t].id for t in boss_titles if t in menu_map])
        await self.__bind_role_menus(db, role_map["smartqa_staff"].id, [menu_map[t].id for t in staff_titles if t in menu_map])

    @staticmethod
    async def __bind_role_menus(db: AsyncSession, role_id: int, menu_ids: list[int]) -> None:
        if not menu_ids:
            return
        existing_rows = await db.execute(select(RoleMenusModel.menu_id).where(RoleMenusModel.role_id == role_id))
        existing = set(existing_rows.scalars().all())
        db.add_all(
            RoleMenusModel(role_id=role_id, menu_id=menu_id)
            for menu_id in menu_ids
            if menu_id not in existing
        )
        await db.flush()

    @staticmethod
    def __create_objects_with_children(data: list[dict], model_class: type) -> list:
        def _create(obj_data: dict) -> Any:
            payload = dict(obj_data)
            children_data = payload.pop("children", [])
            obj = model_class(**payload)
            if children_data:
                obj.children = [_create(child) for child in children_data]
            return obj

        return [_create(item) for item in data]

    async def __load_json(self, filename: str) -> list[dict]:
        json_path = SCRIPT_DIR / f"{filename}.json"
        if not json_path.exists():
            return []

        try:
            with open(json_path, encoding="utf-8") as f:
                raw = json.loads(f.read())
            return [self._parse_date_strings(item) for item in raw]
        except json.JSONDecodeError as exc:
            logger.error(f"failed to parse {json_path}: {exc}")
            raise
        except Exception as exc:
            logger.error(f"failed to read {json_path}: {exc}")
            raise

    @classmethod
    def _parse_date_strings(cls, data: dict) -> dict:
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                if cls._DATETIME_RE.match(value):
                    result[key] = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                elif cls._DATE_RE.match(value):
                    result[key] = datetime.strptime(value, "%Y-%m-%d").date()
                elif cls._TIME_RE.match(value):
                    result[key] = time.fromisoformat(value)
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = cls._parse_date_strings(value)
            else:
                result[key] = value
        return result
