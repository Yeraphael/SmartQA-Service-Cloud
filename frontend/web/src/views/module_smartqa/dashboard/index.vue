<template>
  <div class="smartqa-page">
    <div class="smartqa-toolbar">
      <div>
        <h2>SmartQA 工作台</h2>
        <span>{{ health?.ali_model_name || "qwen3.7-plus" }}</span>
      </div>
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

    <ElRow :gutter="12" class="content-row">
      <ElCol :xs="24" :lg="14">
        <ElCard shadow="never">
          <template #header>
            <div class="card-title">
              <FaSvgIcon icon="ri:user-star-line" />
              <span>客服质检排行</span>
            </div>
          </template>
          <ElTable :data="ranking" height="420" row-key="staff_id">
            <ElTableColumn prop="staff_name" label="客服" min-width="120" show-overflow-tooltip />
            <ElTableColumn prop="primary_account" label="账号" min-width="180" show-overflow-tooltip />
            <ElTableColumn prop="qc_count" label="质检数" width="90" />
            <ElTableColumn prop="avg_score" label="均分" width="90" />
            <ElTableColumn prop="high_risk_count" label="高风险" width="90" />
          </ElTable>
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :lg="10">
        <ElCard shadow="never">
          <template #header>
            <div class="card-title">
              <FaSvgIcon icon="ri:store-2-line" />
              <span>店铺会话分布</span>
            </div>
          </template>
          <ElTable :data="shops" height="420" row-key="shop_id">
            <ElTableColumn prop="shop_name" label="店铺" min-width="160" show-overflow-tooltip />
            <ElTableColumn prop="conversation_count" label="会话数" width="110" />
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
  type ShopDistribution,
  type SmartQAHealth,
  type StaffRanking,
} from "@/api/module_smartqa";

const loading = ref(false);
const overview = ref<DashboardOverview>();
const health = ref<SmartQAHealth>();
const ranking = ref<StaffRanking[]>([]);
const shops = ref<ShopDistribution[]>([]);

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
    const [healthRes, overviewRes, rankingRes, shopRes] = await Promise.all([
      SmartQAAPI.health(),
      SmartQAAPI.dashboardOverview(),
      SmartQAAPI.staffRanking(20),
      SmartQAAPI.shopDistribution(),
    ]);
    health.value = healthRes.data.data;
    overview.value = overviewRes.data.data;
    ranking.value = rankingRes.data.data || [];
    shops.value = shopRes.data.data || [];
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

.smartqa-toolbar span {
  color: var(--el-text-color-secondary);
  font-size: 13px;
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

.content-row {
  min-height: 0;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
