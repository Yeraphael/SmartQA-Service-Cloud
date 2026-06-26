"""数据构建服务 - 协调ODS到DIM/DWD的完整转换流程。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema
from app.plugin.module_smartqa.builder.conversation_builder import ConversationBuilder
from app.plugin.module_smartqa.builder.dimension_builder import DimensionBuilder


class DataBuildService:
    """数据构建服务 - 从ODS扩展到DIM/DWD层。"""

    def __init__(self, auth: AuthSchema | None = None) -> None:
        self.auth = auth

    async def build_from_batch(self, session: AsyncSession, batch_id: str) -> dict:
        """从指定批次构建维表和明细表。

        Args:
            session: 数据库会话
            batch_id: 导入批次ID

        Returns:
            构建结果统计
        """
        tenant_id = self.auth.tenant_id if self.auth else None

        dim_builder = DimensionBuilder(session, batch_id, tenant_id)
        conv_builder = ConversationBuilder(session, batch_id, tenant_id)

        shop_id_map = await dim_builder.build_shops()
        product_id_map = await dim_builder.build_products(shop_id_map)
        staff_id_map = await dim_builder.build_staff(shop_id_map)
        customer_id_map = await dim_builder.build_customers(staff_id_map)

        conversation_id_map = await conv_builder.build_conversations(
            shop_id_map,
            product_id_map,
            staff_id_map,
            customer_id_map,
        )

        await conv_builder.build_messages(
            conversation_id_map,
            staff_id_map,
            customer_id_map,
        )

        await conv_builder.build_customer_staff_relations(conversation_id_map)

        await session.commit()

        return {
            "batch_id": batch_id,
            "shops_count": len(shop_id_map),
            "products_count": len(product_id_map),
            "staff_count": len(staff_id_map),
            "customers_count": len(customer_id_map),
            "conversations_count": len(conversation_id_map),
        }
