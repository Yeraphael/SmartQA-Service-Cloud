<template>
  <div class="smartqa-page">
    <div class="smartqa-toolbar">
      <ElInput
        v-model="keyword"
        clearable
        placeholder="客户、客服、商品"
        prefix-icon="Search"
        class="search-input"
        @keyup.enter="search"
      />
      <ElSelect v-model="riskLevel" clearable placeholder="风险" class="risk-select" @change="search">
        <ElOption label="无" value="none" />
        <ElOption label="低" value="low" />
        <ElOption label="中" value="medium" />
        <ElOption label="高" value="high" />
        <ElOption label="严重" value="critical" />
      </ElSelect>
      <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
    </div>

    <ElCard shadow="never">
      <ElTable :loading="loading" :data="rows" row-key="id" height="620" @row-dblclick="openDetail">
        <ElTableColumn prop="conversation_id" label="会话" min-width="150" show-overflow-tooltip />
        <ElTableColumn prop="score" label="分数" width="90" />
        <ElTableColumn prop="result_level" label="结果" width="100">
          <template #default="{ row }">
            <ElTag :type="row.result_level === 'pass' ? 'success' : 'danger'">
              {{ row.result_level }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="risk_level" label="风险" width="100" />
        <ElTableColumn prop="staff_name" label="客服" width="120" show-overflow-tooltip />
        <ElTableColumn prop="customer_account" label="客户" min-width="140" show-overflow-tooltip />
        <ElTableColumn prop="product_name" label="商品" min-width="220" show-overflow-tooltip />
        <ElTableColumn prop="summary" label="摘要" min-width="260" show-overflow-tooltip />
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

    <ElDrawer v-model="drawerVisible" size="680px" title="质检详情">
      <div v-if="detail" class="detail">
        <ElDescriptions :column="2" border>
          <ElDescriptionsItem label="分数">{{ detail.result.score }}</ElDescriptionsItem>
          <ElDescriptionsItem label="风险">{{ detail.result.risk_level }}</ElDescriptionsItem>
          <ElDescriptionsItem label="规则">{{ detail.result.rule_version || "-" }}</ElDescriptionsItem>
          <ElDescriptionsItem label="模型">{{ detail.result.model_name || "-" }}</ElDescriptionsItem>
        </ElDescriptions>
        <ElAlert :title="detail.result.summary || '暂无摘要'" type="info" :closable="false" />
        <ElTable :data="detail.issues" row-key="id">
          <ElTableColumn prop="rule_code" label="规则" width="150" />
          <ElTableColumn prop="severity" label="等级" width="90" />
          <ElTableColumn prop="deduction_score" label="扣分" width="80" />
          <ElTableColumn prop="title" label="问题" min-width="180" show-overflow-tooltip />
          <ElTableColumn prop="reason" label="原因" min-width="220" show-overflow-tooltip />
        </ElTable>
        <ElTable :data="detail.evidences" row-key="evidence_id">
          <ElTableColumn prop="message_id" label="证据消息" min-width="150" show-overflow-tooltip />
          <ElTableColumn prop="speaker_type" label="角色" width="80" />
          <ElTableColumn prop="content_text" label="内容" min-width="300" show-overflow-tooltip />
        </ElTable>
      </div>
    </ElDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import SmartQAAPI, { type QcResultDetail, type QcResultRow } from "@/api/module_smartqa";

const loading = ref(false);
const rows = ref<QcResultRow[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const keyword = ref("");
const riskLevel = ref("");
const drawerVisible = ref(false);
const detail = ref<QcResultDetail>();

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.qcResults({
      page_no: pageNo.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      risk_level: riskLevel.value || undefined,
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

async function openDetail(row: QcResultRow) {
  const res = await SmartQAAPI.qcResultDetail(row.id);
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
  align-items: center;
  gap: 8px;
}

.search-input {
  max-width: 320px;
}

.risk-select {
  width: 130px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
</style>
