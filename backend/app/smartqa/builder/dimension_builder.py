"""维表（DIM）构建器 - 生成店铺、商品、客服、客户维表。"""

import hashlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.smartqa.models.dimension import (
    DimCustomerIdentityModel,
    DimCustomerModel,
    DimProductModel,
    DimShopModel,
    DimStaffAccountModel,
    DimStaffModel,
)
from app.smartqa.models.ods import OdsQnChatRecordModel, OdsQnShopRecordModel


class DimensionBuilder:
    """维表构建器。"""

    def __init__(self, session: AsyncSession, batch_id: str, tenant_id: int | None = None):
        self.session = session
        self.batch_id = batch_id
        self.tenant_id = tenant_id

    async def build_shops(self) -> dict[str, int]:
        """从ODS构建店铺维表，返回 shop_name -> shop_id 映射。"""
        stmt = (
            select(OdsQnShopRecordModel.shop_name)
            .where(
                OdsQnShopRecordModel.batch_id == self.batch_id,
                OdsQnShopRecordModel.is_deleted == False,  # noqa: E712
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        shop_names = [row[0] for row in result.fetchall()]

        shop_id_map = {}
        for shop_name in shop_names:
            if not shop_name:
                continue

            shop_key = f"qianniu_{self._hash_key(shop_name)}"

            existing_stmt = select(DimShopModel).where(
                DimShopModel.shop_key == shop_key,
                DimShopModel.is_deleted == False,  # noqa: E712
            )
            existing_result = await self.session.execute(existing_stmt)
            existing_shop = existing_result.scalar_one_or_none()

            if existing_shop:
                shop_id_map[shop_name] = existing_shop.id
            else:
                new_shop = DimShopModel(
                    shop_key=shop_key,
                    source_system="qianniu",
                    shop_name=shop_name,
                    status="active",
                    tenant_id=self.tenant_id,
                )
                self.session.add(new_shop)
                await self.session.flush()
                shop_id_map[shop_name] = new_shop.id

        return shop_id_map

    async def build_products(self, shop_id_map: dict[str, int]) -> dict[tuple[str, str], int]:
        """构建商品维表，返回 (shop_name, product_id) -> product_pk 映射。"""
        stmt = (
            select(
                OdsQnShopRecordModel.shop_name,
                OdsQnShopRecordModel.product_id,
                OdsQnShopRecordModel.product_name,
            )
            .where(
                OdsQnShopRecordModel.batch_id == self.batch_id,
                OdsQnShopRecordModel.product_id.isnot(None),
                OdsQnShopRecordModel.is_deleted == False,  # noqa: E712
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        products = result.fetchall()

        product_id_map = {}
        for shop_name, product_id, product_name in products:
            if not shop_name or not product_id:
                continue

            shop_pk = shop_id_map.get(shop_name)
            if not shop_pk:
                continue

            product_key = f"qianniu_{shop_pk}_{product_id}"

            existing_stmt = select(DimProductModel).where(
                DimProductModel.product_key == product_key,
                DimProductModel.is_deleted == False,  # noqa: E712
            )
            existing_result = await self.session.execute(existing_stmt)
            existing_product = existing_result.scalar_one_or_none()

            if existing_product:
                if existing_product.product_name != product_name:
                    existing_product.product_name = product_name
                    existing_product.updated_time = datetime.now()
                product_id_map[(shop_name, product_id)] = existing_product.id
            else:
                new_product = DimProductModel(
                    product_key=product_key,
                    source_system="qianniu",
                    shop_id=shop_pk,
                    product_id=product_id,
                    product_name=product_name,
                    status="active",
                    tenant_id=self.tenant_id,
                )
                self.session.add(new_product)
                await self.session.flush()
                product_id_map[(shop_name, product_id)] = new_product.id

        return product_id_map

    async def build_staff(self, shop_id_map: dict[str, int]) -> dict[str, int]:
        """构建客服维表，返回 seller_wangwang -> staff_id 映射。"""
        stmt = (
            select(
                OdsQnShopRecordModel.seller_wangwang,
                OdsQnShopRecordModel.shop_name,
            )
            .where(
                OdsQnShopRecordModel.batch_id == self.batch_id,
                OdsQnShopRecordModel.seller_wangwang.isnot(None),
                OdsQnShopRecordModel.is_deleted == False,  # noqa: E712
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        staff_accounts = result.fetchall()

        staff_id_map = {}
        staff_account_map = {}

        for seller_wangwang, shop_name in staff_accounts:
            if not seller_wangwang:
                continue

            staff_name = self._extract_staff_name(seller_wangwang)
            staff_key = f"qianniu_{self._hash_key(seller_wangwang)}"

            existing_stmt = select(DimStaffModel).where(
                DimStaffModel.staff_key == staff_key,
                DimStaffModel.is_deleted == False,  # noqa: E712
            )
            existing_result = await self.session.execute(existing_stmt)
            existing_staff = existing_result.scalar_one_or_none()

            if existing_staff:
                staff_pk = existing_staff.id
            else:
                new_staff = DimStaffModel(
                    staff_key=staff_key,
                    staff_name=staff_name,
                    primary_account=seller_wangwang,
                    source_system="qianniu",
                    status="active",
                    tenant_id=self.tenant_id,
                )
                self.session.add(new_staff)
                await self.session.flush()
                staff_pk = new_staff.id

            staff_id_map[seller_wangwang] = staff_pk

            shop_pk = shop_id_map.get(shop_name)
            if shop_pk:
                account_key = f"qianniu_{shop_pk}_{self._hash_key(seller_wangwang)}"
                staff_account_map[(seller_wangwang, shop_name)] = (staff_pk, shop_pk, account_key)

        for (seller_wangwang, shop_name), (staff_pk, shop_pk, account_key) in staff_account_map.items():
            existing_acc_stmt = select(DimStaffAccountModel).where(
                DimStaffAccountModel.staff_account_key == account_key,
                DimStaffAccountModel.is_deleted == False,  # noqa: E712
            )
            existing_acc_result = await self.session.execute(existing_acc_stmt)
            existing_account = existing_acc_result.scalar_one_or_none()

            if not existing_account:
                new_account = DimStaffAccountModel(
                    staff_account_key=account_key,
                    staff_id=staff_pk,
                    shop_id=shop_pk,
                    source_system="qianniu",
                    channel="qianniu",
                    account_name=seller_wangwang,
                    status="active",
                    tenant_id=self.tenant_id,
                )
                self.session.add(new_account)

        await self.session.flush()
        return staff_id_map

    async def build_customers(self, staff_id_map: dict[str, int]) -> dict[str, int]:
        """构建客户维表，返回 customer_account -> customer_id 映射。"""
        stmt = (
            select(
                OdsQnChatRecordModel.relation_id,
                OdsQnChatRecordModel.business_id,
                OdsQnChatRecordModel.chat_target,
            )
            .where(
                OdsQnChatRecordModel.batch_id == self.batch_id,
                OdsQnChatRecordModel.is_deleted == False,  # noqa: E712
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        chat_records = result.fetchall()

        shop_stmt = select(
            OdsQnShopRecordModel.relation_id,
            OdsQnShopRecordModel.business_id,
            OdsQnShopRecordModel.seller_wangwang,
            OdsQnShopRecordModel.buyer_wangwang,
        ).where(
            OdsQnShopRecordModel.batch_id == self.batch_id,
            OdsQnShopRecordModel.is_deleted == False,  # noqa: E712
        )
        shop_result = await self.session.execute(shop_stmt)
        shop_records = {
            (row.relation_id, row.business_id): (row.seller_wangwang, row.buyer_wangwang) for row in shop_result.fetchall()
        }

        conversation_customers = {}
        for relation_id, business_id, chat_target in chat_records:
            conv_key = (relation_id, business_id)
            seller_wangwang, buyer_wangwang = shop_records.get(conv_key, (None, None))

            if seller_wangwang and chat_target != seller_wangwang:
                if conv_key not in conversation_customers:
                    conversation_customers[conv_key] = (chat_target, buyer_wangwang)

        customer_id_map = {}
        for (customer_account, buyer_wangwang_masked) in set(conversation_customers.values()):
            if not customer_account:
                continue

            customer_key = f"qianniu_{self._hash_key(customer_account)}"

            existing_stmt = select(DimCustomerModel).where(
                DimCustomerModel.customer_key == customer_key,
                DimCustomerModel.is_deleted == False,  # noqa: E712
            )
            existing_result = await self.session.execute(existing_stmt)
            existing_customer = existing_result.scalar_one_or_none()

            if existing_customer:
                if buyer_wangwang_masked and not existing_customer.buyer_wangwang_masked:
                    existing_customer.buyer_wangwang_masked = buyer_wangwang_masked
                existing_customer.last_seen_at = datetime.now()
                customer_pk = existing_customer.id
            else:
                new_customer = DimCustomerModel(
                    customer_key=customer_key,
                    primary_taobao_account=customer_account,
                    buyer_wangwang_masked=buyer_wangwang_masked,
                    first_source="qianniu",
                    first_seen_at=datetime.now(),
                    last_seen_at=datetime.now(),
                    status="active",
                    tenant_id=self.tenant_id,
                )
                self.session.add(new_customer)
                await self.session.flush()
                customer_pk = new_customer.id

                identity = DimCustomerIdentityModel(
                    customer_id=customer_pk,
                    identity_type="taobao_account",
                    identity_value=customer_account,
                    source_system="qianniu",
                    confidence="high",
                    status="active",
                    tenant_id=self.tenant_id,
                )
                self.session.add(identity)

            customer_id_map[customer_account] = customer_pk

        await self.session.flush()
        return customer_id_map

    def _extract_staff_name(self, seller_wangwang: str) -> str:
        """从 seller_wangwang 提取客服名称，格式：店铺:姓名。"""
        if ":" in seller_wangwang:
            parts = seller_wangwang.split(":")
            return parts[-1] if len(parts) > 1 else seller_wangwang
        return seller_wangwang

    def _hash_key(self, value: str) -> str:
        """生成短哈希键。"""
        return hashlib.sha256(value.encode()).hexdigest()[:16]
