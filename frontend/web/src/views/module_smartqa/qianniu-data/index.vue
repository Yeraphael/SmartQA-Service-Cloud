<template>
  <div class="smartqa-page">
    <div class="smartqa-toolbar">
      <div>
        <h2>千牛数据</h2>
        <span>精确同步数以源库 COUNT(*) 为准</span>
      </div>
      <div class="toolbar-actions">
        <ElCheckbox v-model="truncateDwd">重建明细</ElCheckbox>
        <ElButton :loading="syncing" type="primary" icon="RefreshRight" @click="syncSource">
          源库同步
        </ElButton>
        <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
      </div>
    </div>

    <ElRow :gutter="12">
      <ElCol v-for="item in metrics" :key="item.label" :xs="12" :sm="8" :lg="4">
        <ElCard shadow="never" class="metric-card">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
        </ElCard>
      </ElCol>
    </ElRow>

    <ElCard shadow="never">
      <ElTable :loading="loading" :data="batches" row-key="id" height="520">
        <ElTableColumn prop="batch_id" label="批次" min-width="240" show-overflow-tooltip />
        <ElTableColumn prop="source_type" label="来源" width="90" />
        <ElTableColumn prop="chat_rows" label="聊天" width="110" />
        <ElTableColumn prop="shop_rows" label="业务" width="100" />
        <ElTableColumn prop="conversation_count" label="会话" width="100" />
        <ElTableColumn prop="status" label="状态" width="110">
          <template #default="{ row }">
            <ElTag :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">
              {{ row.status }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="finished_at" label="完成时间" min-width="170" show-overflow-tooltip />
        <ElTableColumn prop="error_message" label="错误" min-width="180" show-overflow-tooltip />
      </ElTable>
      <div class="pager">
        <ElPagination
          v-model:current-page="pageNo"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @change="loadBatches"
        />
      </div>
    </ElCard>
  </div>
</template>

<script setup lang="ts">
import { ElMessageBox } from "element-plus";
import { computed, onMounted, ref } from "vue";
import SmartQAAPI, { type ImportBatch, type QianniuSummary } from "@/api/module_smartqa";

const loading = ref(false);
const syncing = ref(false);
const truncateDwd = ref(false);
const summary = ref<QianniuSummary>();
const batches = ref<ImportBatch[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);

const metrics = computed(() => [
  { label: "批次", value: summary.value?.batch_count ?? 0 },
  { label: "成功批次", value: summary.value?.success_batch_count ?? 0 },
  { label: "聊天", value: summary.value?.chat_rows ?? 0 },
  { label: "业务", value: summary.value?.shop_rows ?? 0 },
  { label: "会话", value: summary.value?.conversation_count ?? 0 },
  { label: "最新状态", value: summary.value?.latest_status || "-" },
]);

async function loadBatches() {
  const res = await SmartQAAPI.batches({ page_no: pageNo.value, page_size: pageSize.value });
  batches.value = res.data.data?.items || [];
  total.value = res.data.data?.total || 0;
}

async function loadData() {
  loading.value = true;
  try {
    const [summaryRes] = await Promise.all([SmartQAAPI.batchSummary(), loadBatches()]);
    summary.value = summaryRes.data.data;
  } finally {
    loading.value = false;
  }
}

async function syncSource() {
  if (truncateDwd.value) {
    await ElMessageBox.confirm("将清空并重建 DIM/DWD/QC 相关数据，确认继续？", "重建确认", {
      type: "warning",
    });
  }
  syncing.value = true;
  try {
    await SmartQAAPI.syncSourceDb({ build: true, seed: true, truncate_dwd: truncateDwd.value });
    await loadData();
  } finally {
    syncing.value = false;
  }
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
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.smartqa-toolbar h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}

.smartqa-toolbar span {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.metric-card {
  border-radius: 8px;
}

.metric-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.metric-value {
  margin-top: 8px;
  font-size: 22px;
  font-weight: 700;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}
</style>
