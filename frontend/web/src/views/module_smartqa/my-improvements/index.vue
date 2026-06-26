<template>
  <div class="smartqa-page">
    <div class="smartqa-toolbar">
      <h2>我的改进建议</h2>
      <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
    </div>

    <ElRow :gutter="12">
      <ElCol :xs="24" :lg="9">
        <ElCard shadow="never">
          <template #header>
            <div class="card-title">
              <FaSvgIcon icon="ri:bar-chart-box-line" />
              <span>问题汇总</span>
            </div>
          </template>
          <ElTable :loading="loading" :data="summary?.issue_summary || []" row-key="rule_code" height="260">
            <ElTableColumn prop="rule_code" label="类型" min-width="140" show-overflow-tooltip />
            <ElTableColumn prop="severity" label="等级" width="90" />
            <ElTableColumn prop="issue_count" label="数量" width="90" />
          </ElTable>
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :lg="15">
        <ElCard shadow="never">
          <template #header>
            <div class="card-title">
              <FaSvgIcon icon="ri:focus-3-line" />
              <span>高频问题</span>
            </div>
          </template>
          <ElTable :loading="loading" :data="summary?.frequent_issues || []" row-key="title" height="260">
            <ElTableColumn prop="title" label="问题" min-width="180" show-overflow-tooltip />
            <ElTableColumn prop="reason" label="原因" min-width="240" show-overflow-tooltip />
            <ElTableColumn prop="suggested_action" label="建议动作" min-width="220" show-overflow-tooltip />
            <ElTableColumn prop="issue_count" label="次数" width="80" />
          </ElTable>
        </ElCard>
      </ElCol>
    </ElRow>

    <ElRow :gutter="12">
      <ElCol :xs="24" :lg="12">
        <ElCard shadow="never">
          <template #header>
            <div class="card-title">
              <FaSvgIcon icon="ri:chat-quote-line" />
              <span>推荐话术</span>
            </div>
          </template>
          <ElTable :loading="loading" :data="summary?.suggested_replies || []" row-key="suggested_reply" height="350">
            <ElTableColumn prop="title" label="问题" min-width="160" show-overflow-tooltip />
            <ElTableColumn prop="suggested_reply" label="话术" min-width="300" show-overflow-tooltip />
            <ElTableColumn prop="issue_count" label="次数" width="80" />
          </ElTable>
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :lg="12">
        <ElCard shadow="never">
          <template #header>
            <div class="card-title">
              <FaSvgIcon icon="ri:error-warning-line" />
              <span>高风险结果</span>
            </div>
          </template>
          <ElTable :loading="loading" :data="summary?.recent_high_risk || []" row-key="result_id" height="350">
            <ElTableColumn prop="conversation_id" label="会话" min-width="150" show-overflow-tooltip />
            <ElTableColumn prop="score" label="分数" width="80" />
            <ElTableColumn prop="product_name" label="商品" min-width="200" show-overflow-tooltip />
            <ElTableColumn label="操作" width="90">
              <template #default="{ row }">
                <ElButton link type="primary" @click="openResult(row.result_id)">详情</ElButton>
              </template>
            </ElTableColumn>
          </ElTable>
        </ElCard>
      </ElCol>
    </ElRow>

    <ElDrawer v-model="drawerVisible" size="720px" title="质检详情">
      <div v-if="detail" class="detail">
        <ElAlert :title="detail.result.summary || '暂无摘要'" type="info" :closable="false" />
        <ElTable :data="detail.issues" row-key="id">
          <ElTableColumn prop="title" label="问题" min-width="180" show-overflow-tooltip />
          <ElTableColumn prop="reason" label="原因" min-width="220" show-overflow-tooltip />
          <ElTableColumn prop="suggested_reply" label="推荐话术" min-width="260" show-overflow-tooltip />
        </ElTable>
        <ElTable :data="detail.evidences" row-key="evidence_id">
          <ElTableColumn prop="speaker_type" label="角色" width="80" />
          <ElTableColumn prop="content_text" label="证据消息" min-width="360" show-overflow-tooltip />
          <ElTableColumn prop="message_time" label="时间" min-width="170" show-overflow-tooltip />
        </ElTable>
      </div>
    </ElDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import SmartQAAPI, {
  type ImprovementSummary,
  type QcResultDetail,
} from "@/api/module_smartqa";

const loading = ref(false);
const summary = ref<ImprovementSummary>();
const drawerVisible = ref(false);
const detail = ref<QcResultDetail>();

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.improvements(20);
    summary.value = res.data.data;
  } finally {
    loading.value = false;
  }
}

async function openResult(resultId: number) {
  const res = await SmartQAAPI.qcResultDetail(resultId);
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
  justify-content: space-between;
}

.smartqa-toolbar h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
</style>
