"""会话和消息明细（DWD）构建器 - 生成会话主表和消息明细表。"""

import hashlib
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.plugin.module_smartqa.models.conversation import (
    DwdCustomerStaffRelationModel,
    DwdQnConversationModel,
    DwdQnMessageModel,
)
from app.plugin.module_smartqa.models.ods import OdsQnChatRecordModel, OdsQnShopRecordModel


class ConversationBuilder:
    """会话和消息构建器。"""

    def __init__(self, session: AsyncSession, batch_id: str, tenant_id: int | None = None):
        self.session = session
        self.batch_id = batch_id
        self.tenant_id = tenant_id

    async def build_conversations(
        self,
        shop_id_map: dict[str, int],
        product_id_map: dict[tuple[str, str], int],
        staff_id_map: dict[str, int],
        customer_id_map: dict[str, int],
    ) -> dict[tuple[str, str], int]:
        """构建会话主表，返回 (relation_id, business_id) -> conversation_pk 映射。"""
        shop_stmt = select(OdsQnShopRecordModel).where(
            OdsQnShopRecordModel.batch_id == self.batch_id,
            OdsQnShopRecordModel.is_deleted == False,  # noqa: E712
        )
        shop_result = await self.session.execute(shop_stmt)
        shop_records = {
            (row.relation_id, row.business_id): row for row in shop_result.scalars().all()
        }

        chat_stmt = (
            select(
                OdsQnChatRecordModel.relation_id,
                OdsQnChatRecordModel.business_id,
                OdsQnChatRecordModel.chat_target,
            )
            .where(
                OdsQnChatRecordModel.batch_id == self.batch_id,
                OdsQnChatRecordModel.is_deleted == False,  # noqa: E712
            )
        )
        chat_result = await self.session.execute(chat_stmt)
        chat_records = chat_result.fetchall()

        conversation_customers = {}
        for chat_rec in chat_records:
            conv_key = (chat_rec.relation_id, chat_rec.business_id)
            shop_rec = shop_records.get(conv_key)
            if shop_rec:
                seller = shop_rec.seller_wangwang
                if chat_rec.chat_target != seller:
                    conversation_customers[conv_key] = chat_rec.chat_target

        conversation_id_map = {}
        for conv_key, shop_rec in shop_records.items():
            relation_id, business_id = conv_key
            conversation_key = f"qianniu|{relation_id}|{business_id}"
            conversation_id = f"conv_{self._hash_key(conversation_key)}"

            shop_pk = shop_id_map.get(shop_rec.shop_name)
            product_pk = product_id_map.get((shop_rec.shop_name, shop_rec.product_id)) if shop_rec.product_id else None
            staff_pk = staff_id_map.get(shop_rec.seller_wangwang)
            customer_account = conversation_customers.get(conv_key)
            customer_pk = customer_id_map.get(customer_account) if customer_account else None

            existing_stmt = select(DwdQnConversationModel).where(
                DwdQnConversationModel.conversation_key == conversation_key,
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
            )
            existing_result = await self.session.execute(existing_stmt)
            existing_conv = existing_result.scalar_one_or_none()

            if existing_conv:
                existing_conv.qn_status = shop_rec.status
                existing_conv.start_time = shop_rec.start_time
                existing_conv.end_time = shop_rec.end_time
                existing_conv.shop_id = shop_pk
                existing_conv.product_id = product_pk
                existing_conv.staff_id = staff_pk
                existing_conv.customer_id = customer_pk
                existing_conv.updated_time = datetime.now()
                conversation_pk = existing_conv.id
            else:
                new_conv = DwdQnConversationModel(
                    conversation_key=conversation_key,
                    conversation_id=conversation_id,
                    source_system="qianniu",
                    relation_id=relation_id,
                    business_id=business_id,
                    shop_id=shop_pk,
                    product_id=product_pk,
                    staff_id=staff_pk,
                    customer_id=customer_pk,
                    qn_status=shop_rec.status,
                    start_time=shop_rec.start_time,
                    end_time=shop_rec.end_time,
                    message_count=0,
                    customer_message_count=0,
                    staff_message_count=0,
                    qc_status="pending",
                    data_hash="",
                    tenant_id=self.tenant_id,
                )
                self.session.add(new_conv)
                await self.session.flush()
                conversation_pk = new_conv.id

            conversation_id_map[conv_key] = conversation_pk

        await self.session.flush()
        return conversation_id_map

    async def build_messages(
        self,
        conversation_id_map: dict[tuple[str, str], int],
        staff_id_map: dict[str, int],
        customer_id_map: dict[str, int],
    ) -> None:
        """构建消息明细表。"""
        shop_stmt = select(
            OdsQnShopRecordModel.relation_id,
            OdsQnShopRecordModel.business_id,
            OdsQnShopRecordModel.seller_wangwang,
        ).where(
            OdsQnShopRecordModel.batch_id == self.batch_id,
            OdsQnShopRecordModel.is_deleted == False,  # noqa: E712
        )
        shop_result = await self.session.execute(shop_stmt)
        seller_map = {
            (row.relation_id, row.business_id): row.seller_wangwang for row in shop_result.all()
        }

        chat_stmt = select(OdsQnChatRecordModel).where(
            OdsQnChatRecordModel.batch_id == self.batch_id,
            OdsQnChatRecordModel.is_deleted == False,  # noqa: E712
        )
        chat_result = await self.session.execute(chat_stmt)
        chat_records = chat_result.scalars().all()

        conversation_messages = defaultdict(list)
        for chat_rec in chat_records:
            conv_key = (chat_rec.relation_id, chat_rec.business_id)
            conversation_pk = conversation_id_map.get(conv_key)
            if not conversation_pk:
                continue

            message_id = f"msg_{self._hash_key(chat_rec.source_id)}"
            seller_wangwang = seller_map.get(conv_key)

            if chat_rec.chat_target == seller_wangwang:
                speaker_type = "staff"
            elif chat_rec.chat_target in customer_id_map:
                speaker_type = "customer"
            else:
                speaker_type = "unknown"

            message_hash = self._hash_key(chat_rec.chat_content or "")

            existing_msg_stmt = select(DwdQnMessageModel).where(
                DwdQnMessageModel.message_id == message_id,
                DwdQnMessageModel.is_deleted == False,  # noqa: E712
            )
            existing_msg_result = await self.session.execute(existing_msg_stmt)
            existing_msg = existing_msg_result.scalar_one_or_none()

            if not existing_msg:
                new_message = DwdQnMessageModel(
                    message_id=message_id,
                    conversation_id=conversation_pk,
                    source_system="qianniu",
                    source_message_id=chat_rec.source_id,
                    message_fingerprint=chat_rec.message_fingerprint,
                    speaker_account=chat_rec.chat_target,
                    speaker_type=speaker_type,
                    content_text=chat_rec.chat_content,
                    message_time=chat_rec.chat_time,
                    message_hash=message_hash,
                    tenant_id=self.tenant_id,
                )
                self.session.add(new_message)
                conversation_messages[conversation_pk].append((speaker_type, chat_rec.chat_time))

        await self.session.flush()

        for conversation_pk, messages in conversation_messages.items():
            conv_stmt = select(DwdQnConversationModel).where(
                DwdQnConversationModel.id == conversation_pk,
                DwdQnConversationModel.is_deleted == False,  # noqa: E712
            )
            conv_result = await self.session.execute(conv_stmt)
            conv = conv_result.scalar_one_or_none()

            if conv:
                total_count = len(messages)
                customer_count = sum(1 for speaker, _ in messages if speaker == "customer")
                staff_count = sum(1 for speaker, _ in messages if speaker == "staff")

                conv.message_count = total_count
                conv.customer_message_count = customer_count
                conv.staff_message_count = staff_count

                sorted_messages = sorted(messages, key=lambda x: x[1])
                if not conv.start_time and sorted_messages:
                    conv.start_time = sorted_messages[0][1]
                if not conv.end_time and sorted_messages:
                    conv.end_time = sorted_messages[-1][1]

                first_customer_time = next((t for speaker, t in sorted_messages if speaker == "customer"), None)
                first_staff_response = next(
                    (t for speaker, t in sorted_messages if speaker == "staff" and (not first_customer_time or t > first_customer_time)),
                    None,
                )
                if first_customer_time and first_staff_response:
                    conv.first_response_seconds = int((first_staff_response - first_customer_time).total_seconds())

                message_ids = [msg_id for msg_id, _ in sorted((message_id, time) for _, time in messages)]
                data_hash_input = f"{conv.conversation_key}|{conv.qn_status}|{conv.staff_id}|{conv.customer_id}|{conv.product_id}|{'|'.join(str(m) for m in message_ids)}"
                conv.data_hash = hashlib.sha256(data_hash_input.encode()).hexdigest()

        await self.session.flush()

    async def build_customer_staff_relations(
        self,
        conversation_id_map: dict[tuple[str, str], int],
    ) -> None:
        """构建客户-客服服务关系表。"""
        conv_stmt = select(DwdQnConversationModel).where(
            DwdQnConversationModel.id.in_(list(conversation_id_map.values())),
            DwdQnConversationModel.customer_id.isnot(None),
            DwdQnConversationModel.staff_id.isnot(None),
            DwdQnConversationModel.shop_id.isnot(None),
            DwdQnConversationModel.is_deleted == False,  # noqa: E712
        )
        conv_result = await self.session.execute(conv_stmt)
        conversations = conv_result.fetchall()

        relations = defaultdict(list)
        for conv in conversations:
            relation_key = f"cust_{conv.customer_id}_staff_{conv.staff_id}_shop_{conv.shop_id}"
            relations[relation_key].append((conv.start_time, conv.id))

        for relation_key, conv_list in relations.items():
            parts = relation_key.split("_")
            customer_id = int(parts[1])
            staff_id = int(parts[3])
            shop_id = int(parts[5])

            existing_rel_stmt = select(DwdCustomerStaffRelationModel).where(
                DwdCustomerStaffRelationModel.relation_key == relation_key,
                DwdCustomerStaffRelationModel.is_deleted == False,  # noqa: E712
            )
            existing_rel_result = await self.session.execute(existing_rel_stmt)
            existing_rel = existing_rel_result.scalar_one_or_none()

            sorted_convs = sorted(conv_list, key=lambda x: x[0] if x[0] else datetime.min)
            first_time = sorted_convs[0][0] if sorted_convs else None
            last_time = sorted_convs[-1][0] if sorted_convs else None

            if existing_rel:
                existing_rel.conversation_count = len(conv_list)
                if first_time and (not existing_rel.first_conversation_at or first_time < existing_rel.first_conversation_at):
                    existing_rel.first_conversation_at = first_time
                if last_time and (not existing_rel.last_conversation_at or last_time > existing_rel.last_conversation_at):
                    existing_rel.last_conversation_at = last_time
                existing_rel.updated_time = datetime.now()
            else:
                new_relation = DwdCustomerStaffRelationModel(
                    relation_key=relation_key,
                    customer_id=customer_id,
                    staff_id=staff_id,
                    shop_id=shop_id,
                    first_conversation_at=first_time,
                    last_conversation_at=last_time,
                    conversation_count=len(conv_list),
                    tenant_id=self.tenant_id,
                )
                self.session.add(new_relation)

        await self.session.flush()

    def _hash_key(self, value: str) -> str:
        """生成短哈希键。"""
        return hashlib.sha256(value.encode()).hexdigest()[:16]
