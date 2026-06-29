<template>
  <div class="smartqa-screen my-dashboard">
    <div class="page-head">
      <div>
        <h2>我的工作台</h2>
        <p>先处理高意向客户、待联系确认、待交接确认和高风险复盘</p>
      </div>
      <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
    </div>

    <div class="task-grid">
      <section v-for="item in metrics" :key="item.label" class="task-tile">
        <FaSvgIcon :icon="item.icon" />
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </section>
    </div>

    <div class="dashboard-grid">
      <section class="panel panel-main">
        <header>
          <h3>今日优先跟进</h3>
          <ElTag type="danger" effect="plain">{{ priorityRows.length }} 个客户</ElTag>
        </header>
        <ElTable :loading="loading" :data="priorityRows" height="420" row-key="result_id">
          <ElTableColumn prop="intent_tier" label="等级" width="78">
            <template #default="{ row }">
              <ElTag :type="row.intent_tier === 'H1' ? 'danger' : 'warning'">{{ row.intent_tier }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="customer_account" label="客户" min-width="130" show-overflow-tooltip />
          <ElTableColumn prop="product_name" label="商品" min-width="200" show-overflow-tooltip />
          <ElTableColumn prop="need_summary" label="需求" min-width="250" show-overflow-tooltip />
          <ElTableColumn label="任务" width="110">
            <template #default="{ row }">
              <ElTag :type="todoTag(row).type" effect="plain">{{ todoTag(row).text }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="next_action" label="下一步" min-width="240" show-overflow-tooltip />
        </ElTable>
      </section>

      <section class="panel">
        <header>
          <h3>我的待复盘问题</h3>
        </header>
        <ElTable :loading="loading" :data="summary?.frequent_issues || []" height="420" row-key="title">
          <ElTableColumn prop="title" label="问题" min-width="150" show-overflow-tooltip />
          <ElTableColumn prop="issue_count" label="次数" width="70" />
          <ElTableColumn prop="suggested_action" label="正确做法" min-width="190" show-overflow-tooltip />
        </ElTable>
      </section>

      <section class="panel panel-main">
        <header>
          <h3>可复制跟进话术</h3>
        </header>
        <div class="reply-list">
          <article v-for="reply in replyRows" :key="reply.suggested_reply">
            <strong>{{ reply.title }}</strong>
            <p>{{ reply.suggested_reply }}</p>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import SmartQAAPI, {
  type ImprovementSummary,
  type IntentCustomer,
} from "@/api/module_smartqa";

const loading = ref(false);
const intents = ref<IntentCustomer[]>([]);
const summary = ref<ImprovementSummary>();

const hRows = computed(() => intents.value.filter((row) => ["H1", "H2"].includes(row.intent_tier)));
const priorityRows = computed(() =>
  hRows.value
    .filter((row) => !row.contact_requested || row.contact_provided || (row.silent_hours ?? 0) >= 24 || row.risk_level === "high")
    .slice(0, 20)
);
const replyRows = computed(() => (summary.value?.suggested_replies || []).slice(0, 8));

const metrics = computed(() => [
  { label: "H1/H2客户", value: hRows.value.length, icon: "ri:user-star-line" },
  { label: "待联系确认", value: hRows.value.filter((row) => !row.contact_requested).length, icon: "ri:phone-line" },
  { label: "待交接确认", value: hRows.value.filter((row) => row.contact_provided && !["ready", "matched", "converted"].includes(row.xianfa_handoff_status)).length, icon: "ri:exchange-line" },
  { label: "待激活", value: hRows.value.filter((row) => (row.silent_hours ?? 0) >= 24).length, icon: "ri:timer-line" },
]);

function todoTag(row: IntentCustomer): { type: "danger" | "warning" | "success" | "info"; text: string } {
  if (!row.contact_requested) return { type: "danger", text: "待联系确认" };
  if (row.contact_provided && !["ready", "matched", "converted"].includes(row.xianfa_handoff_status)) return { type: "warning", text: "待交接确认" };
  if ((row.silent_hours ?? 0) >= 24) return { type: "info", text: "待激活" };
  return { type: "success", text: "继续推进" };
}

async function loadData() {
  loading.value = true;
  try {
    const [intentRes, improvementRes] = await Promise.all([
      SmartQAAPI.intentCustomers({ limit: 120 }),
      SmartQAAPI.improvements(20),
    ]);
    intents.value = intentRes.data.data || [];
    summary.value = improvementRes.data.data;
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped>
.my-dashboard {
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.page-head h2,
.panel h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 720;
}

.page-head p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
}

.task-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.task-tile,
.panel {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
}

.task-tile {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px 10px;
  align-items: center;
  padding: 16px;
}

.task-tile span {
  color: var(--el-text-color-secondary);
}

.task-tile strong {
  grid-column: 1 / -1;
  font-size: 28px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.65fr);
  gap: 12px;
}

.panel {
  min-width: 0;
  padding: 14px;
}

.panel-main {
  grid-column: span 1;
}

.panel header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.reply-list {
  display: grid;
  gap: 10px;
}

.reply-list article {
  padding: 12px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
}

.reply-list strong {
  display: block;
  margin-bottom: 6px;
}

.reply-list p {
  margin: 0;
  color: var(--el-text-color-regular);
  line-height: 1.7;
}

@media (max-width: 900px) {
  .task-grid,
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
