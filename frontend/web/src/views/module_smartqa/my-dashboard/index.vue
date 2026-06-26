<template>
  <div class="smartqa-page">
    <div class="smartqa-toolbar">
      <h2>我的工作台</h2>
      <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
    </div>

    <ElRow :gutter="12">
      <ElCol v-for="item in metrics" :key="item.label" :xs="12" :sm="8" :lg="4">
        <ElCard shadow="never" class="metric-card">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
        </ElCard>
      </ElCol>
    </ElRow>

    <ElRow :gutter="12">
      <ElCol :xs="24" :lg="10">
        <ElCard shadow="never">
          <template #header>
            <div class="card-title">
              <FaSvgIcon icon="ri:bar-chart-2-line" />
              <span>问题类型</span>
            </div>
          </template>
          <ElTable :loading="loading" :data="issues" row-key="rule_code" height="420">
            <ElTableColumn prop="rule_code" label="类型" min-width="150" show-overflow-tooltip />
            <ElTableColumn prop="severity" label="等级" width="90" />
            <ElTableColumn prop="issue_count" label="数量" width="90" />
          </ElTable>
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :lg="14">
        <ElCard shadow="never">
          <template #header>
            <div class="card-title">
              <FaSvgIcon icon="ri:error-warning-line" />
              <span>高风险会话</span>
            </div>
          </template>
          <ElTable :loading="loading" :data="highRisk" row-key="result_id" height="420">
            <ElTableColumn prop="conversation_id" label="会话" min-width="150" show-overflow-tooltip />
            <ElTableColumn prop="score" label="分数" width="80" />
            <ElTableColumn prop="risk_level" label="风险" width="90" />
            <ElTableColumn prop="product_name" label="商品" min-width="200" show-overflow-tooltip />
            <ElTableColumn prop="summary" label="摘要" min-width="220" show-overflow-tooltip />
          </ElTable>
        </ElCard>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import SmartQAAPI, {
  type DashboardOverview,
  type IssueDistribution,
  type RecentHighRisk,
} from "@/api/module_smartqa";

const loading = ref(false);
const overview = ref<DashboardOverview>();
const issues = ref<IssueDistribution[]>([]);
const highRisk = ref<RecentHighRisk[]>([]);

const metrics = computed(() => [
  { label: "会话", value: overview.value?.conversation_count ?? 0 },
  { label: "已质检", value: overview.value?.qc_count ?? 0 },
  { label: "平均分", value: overview.value?.avg_score ?? 0 },
  { label: "不通过", value: overview.value?.fail_count ?? 0 },
  { label: "高风险", value: overview.value?.high_risk_count ?? 0 },
  { label: "问题", value: overview.value?.issue_count ?? 0 },
]);

async function loadData() {
  loading.value = true;
  try {
    const [overviewRes, issueRes, improvementRes] = await Promise.all([
      SmartQAAPI.dashboardOverview(),
      SmartQAAPI.issueDistribution(),
      SmartQAAPI.improvements(10),
    ]);
    overview.value = overviewRes.data.data;
    issues.value = issueRes.data.data || [];
    highRisk.value = improvementRes.data.data?.recent_high_risk || [];
  } finally {
    loading.value = false;
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
}

.smartqa-toolbar h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
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
  font-size: 26px;
  font-weight: 700;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
