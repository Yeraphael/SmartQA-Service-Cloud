<template>
  <div class="smartqa-page">
    <div class="smartqa-toolbar">
      <ElInput
        v-model="keyword"
        clearable
        placeholder="客户、商品"
        prefix-icon="Search"
        class="search-input"
        @keyup.enter="search"
      />
      <ElSelect v-model="qcStatus" clearable placeholder="质检状态" class="status-select" @change="search">
        <ElOption label="待质检" value="pending" />
        <ElOption label="已完成" value="completed" />
        <ElOption label="失败" value="failed" />
      </ElSelect>
      <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
    </div>

    <ElCard shadow="never">
      <ElTable :loading="loading" :data="rows" row-key="id" height="620" @row-dblclick="openDetail">
        <ElTableColumn prop="conversation_id" label="会话ID" min-width="150" show-overflow-tooltip />
        <ElTableColumn prop="shop_name" label="店铺" min-width="130" show-overflow-tooltip />
        <ElTableColumn prop="customer_account" label="客户" min-width="140" show-overflow-tooltip />
        <ElTableColumn prop="product_name" label="商品" min-width="240" show-overflow-tooltip />
        <ElTableColumn prop="qn_status" label="千牛状态" width="140" show-overflow-tooltip />
        <ElTableColumn prop="message_count" label="消息" width="80" />
        <ElTableColumn prop="first_response_seconds" label="首响(s)" width="100" />
        <ElTableColumn prop="qc_status" label="质检" width="100">
          <template #default="{ row }">
            <ElTag :type="row.qc_status === 'completed' ? 'success' : row.qc_status === 'failed' ? 'danger' : 'info'">
              {{ row.qc_status }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="start_time" label="开始时间" min-width="170" show-overflow-tooltip />
        <ElTableColumn label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
      <div class="pager">
        <ElPagination
          v-model:current-page="pageNo"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @change="loadData"
        />
      </div>
    </ElCard>

    <ElDrawer v-model="drawerVisible" size="640px" title="会话详情">
      <div v-if="detail" class="detail">
        <ElDescriptions :column="2" border>
          <ElDescriptionsItem label="会话">{{ detail.conversation.conversation_id }}</ElDescriptionsItem>
          <ElDescriptionsItem label="状态">{{ detail.conversation.qn_status || "-" }}</ElDescriptionsItem>
          <ElDescriptionsItem label="客户">{{ detail.conversation.customer_account || "-" }}</ElDescriptionsItem>
          <ElDescriptionsItem label="商品">{{ detail.conversation.product_name || "-" }}</ElDescriptionsItem>
        </ElDescriptions>
        <div class="messages">
          <div v-for="msg in detail.messages" :key="msg.id" class="message" :class="msg.speaker_type">
            <div class="message-meta">
              <span>{{ msg.speaker_type }}</span>
              <span>{{ msg.speaker_account }}</span>
              <span>{{ msg.message_time }}</span>
            </div>
            <div class="message-text">{{ msg.content_text || "-" }}</div>
          </div>
        </div>
      </div>
    </ElDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import SmartQAAPI, {
  type ConversationDetail,
  type ConversationRow,
} from "@/api/module_smartqa";

const loading = ref(false);
const rows = ref<ConversationRow[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const keyword = ref("");
const qcStatus = ref("");
const drawerVisible = ref(false);
const detail = ref<ConversationDetail>();

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.conversations({
      page_no: pageNo.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      qc_status: qcStatus.value || undefined,
    });
    rows.value = res.data.data?.items || [];
    total.value = res.data.data?.total || 0;
  } finally {
    loading.value = false;
  }
}

function search() {
  pageNo.value = 1;
  loadData();
}

async function openDetail(row: ConversationRow) {
  const res = await SmartQAAPI.conversationDetail(row.id);
  detail.value = res.data.data;
  drawerVisible.value = true;
}

onMounted(loadData);
</script>

<style scoped>
.smartqa-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  padding: 12px;
}

.smartqa-toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-input {
  max-width: 300px;
}

.status-select {
  width: 140px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.message {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 10px;
  background: var(--el-fill-color-blank);
}

.message.staff {
  border-left: 4px solid var(--el-color-primary);
}

.message.customer {
  border-left: 4px solid var(--el-color-success);
}

.message-meta {
  display: flex;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-bottom: 6px;
}

.message-text {
  white-space: pre-wrap;
  line-height: 1.6;
}
</style>
