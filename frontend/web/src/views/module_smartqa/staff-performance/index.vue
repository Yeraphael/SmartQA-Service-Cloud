<template>
  <div class="smartqa-page">
    <div class="smartqa-toolbar">
      <ElInput
        v-model="keyword"
        clearable
        placeholder="客服、账号"
        prefix-icon="Search"
        class="search-input"
      />
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

    <ElCard shadow="never">
      <ElTable :loading="loading" :data="filteredRows" row-key="staff_id" height="600">
        <ElTableColumn prop="staff_name" label="客服" min-width="120" show-overflow-tooltip />
        <ElTableColumn prop="primary_account" label="千牛账号" min-width="180" show-overflow-tooltip />
        <ElTableColumn prop="conversation_count" label="会话" width="90" />
        <ElTableColumn prop="qc_count" label="质检" width="90" />
        <ElTableColumn prop="avg_score" label="均分" width="90" />
        <ElTableColumn prop="issue_count" label="问题" width="90" />
        <ElTableColumn prop="fail_count" label="不通过" width="90" />
        <ElTableColumn prop="high_risk_count" label="高风险" width="90" />
        <ElTableColumn label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <ElDrawer v-model="drawerVisible" size="720px" :title="drawerTitle">
      <div class="drawer-body">
        <ElDescriptions v-if="selectedStaff" :column="2" border>
          <ElDescriptionsItem label="客服">{{ selectedStaff.staff_name }}</ElDescriptionsItem>
          <ElDescriptionsItem label="千牛账号">{{ selectedStaff.primary_account }}</ElDescriptionsItem>
          <ElDescriptionsItem label="质检">{{ selectedStaff.qc_count }}</ElDescriptionsItem>
          <ElDescriptionsItem label="均分">{{ selectedStaff.avg_score }}</ElDescriptionsItem>
          <ElDescriptionsItem label="问题">{{ selectedStaff.issue_count }}</ElDescriptionsItem>
          <ElDescriptionsItem label="高风险">{{ selectedStaff.high_risk_count }}</ElDescriptionsItem>
        </ElDescriptions>

        <ElTable :loading="detailLoading" :data="improvement?.issue_summary || []" row-key="rule_code" height="220">
          <ElTableColumn prop="rule_code" label="问题类型" min-width="150" show-overflow-tooltip />
          <ElTableColumn prop="severity" label="等级" width="90" />
          <ElTableColumn prop="issue_count" label="数量" width="90" />
        </ElTable>

        <ElTable :loading="detailLoading" :data="improvement?.frequent_issues || []" row-key="title" height="260">
          <ElTableColumn prop="title" label="高频问题" min-width="180" show-overflow-tooltip />
          <ElTableColumn prop="reason" label="原因" min-width="240" show-overflow-tooltip />
          <ElTableColumn prop="suggested_action" label="建议动作" min-width="220" show-overflow-tooltip />
          <ElTableColumn prop="issue_count" label="次数" width="80" />
        </ElTable>
      </div>
    </ElDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import SmartQAAPI, {
  type ImprovementSummary,
  type StaffPerformance,
} from "@/api/module_smartqa";

const loading = ref(false);
const detailLoading = ref(false);
const rows = ref<StaffPerformance[]>([]);
const keyword = ref("");
const drawerVisible = ref(false);
const selectedStaff = ref<StaffPerformance>();
const improvement = ref<ImprovementSummary>();

const filteredRows = computed(() => {
  const kw = keyword.value.trim().toLowerCase();
  if (!kw) return rows.value;
  return rows.value.filter((row) =>
    [row.staff_name, row.primary_account].some((item) => String(item || "").toLowerCase().includes(kw)),
  );
});

const metrics = computed(() => {
  const staffCount = rows.value.length;
  const qcCount = rows.value.reduce((sum, row) => sum + (row.qc_count || 0), 0);
  const issueCount = rows.value.reduce((sum, row) => sum + (row.issue_count || 0), 0);
  const highRiskCount = rows.value.reduce((sum, row) => sum + (row.high_risk_count || 0), 0);
  const avgScore = staffCount
    ? (rows.value.reduce((sum, row) => sum + Number(row.avg_score || 0), 0) / staffCount).toFixed(2)
    : "0.00";
  return [
    { label: "客服", value: staffCount },
    { label: "质检", value: qcCount },
    { label: "平均分", value: avgScore },
    { label: "问题", value: issueCount },
    { label: "高风险", value: highRiskCount },
    { label: "不通过", value: rows.value.reduce((sum, row) => sum + (row.fail_count || 0), 0) },
  ];
});

const drawerTitle = computed(() => selectedStaff.value ? `${selectedStaff.value.staff_name} 表现` : "客服表现");

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.staffPerformance({ limit: 200 });
    rows.value = res.data.data || [];
  } finally {
    loading.value = false;
  }
}

async function openDetail(row: StaffPerformance) {
  selectedStaff.value = row;
  drawerVisible.value = true;
  detailLoading.value = true;
  try {
    const res = await SmartQAAPI.improvements(20, row.staff_id);
    improvement.value = res.data.data;
  } finally {
    detailLoading.value = false;
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
  gap: 8px;
}

.search-input {
  max-width: 280px;
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
  font-size: 24px;
  font-weight: 700;
}

.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
</style>
