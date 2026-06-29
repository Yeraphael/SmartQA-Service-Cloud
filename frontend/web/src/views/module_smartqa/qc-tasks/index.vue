<template>
  <div class="smartqa-screen smartqa-page">
    <section class="page-head">
      <div>
        <h2>AI分析任务</h2>
        <p>创建、抽样并执行每日会话质检任务，结果直接写入 SmartQA 真实质检表。</p>
      </div>
      <div class="head-actions">
        <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
      </div>
    </section>

    <section class="summary-grid">
      <article v-for="item in taskMetrics" :key="item.label" class="summary-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <em>{{ item.hint }}</em>
      </article>
    </section>

    <section class="panel smartqa-toolbar">
      <ElInput v-model="conversationIds" placeholder="会话主键ID，逗号分隔" class="ids-input" />
      <ElInput v-model="ruleVersion" placeholder="规则版本" class="version-input" />
      <ElButton :loading="creating" type="primary" icon="Plus" @click="createTasks">创建任务</ElButton>
      <ElButton :disabled="!selected.length" :loading="executing" type="success" icon="VideoPlay" @click="executeTasks">
        执行选中
      </ElButton>
      <ElInputNumber v-model="sampleLimit" :min="1" :max="1000" :step="10" controls-position="right" class="sample-input" />
      <ElButton :loading="sampling" type="warning" icon="Aim" @click="createDailySample(false)">今日抽检</ElButton>
      <ElButton :loading="samplingExecuting" type="danger" icon="Connection" @click="createDailySample(true)">
        抽检并执行
      </ElButton>
    </section>

    <section v-if="sampleResult" class="metric-grid">
      <article v-for="item in sampleMetrics" :key="item.label" class="metric-card">
        <span class="metric-label">{{ item.label }}</span>
        <strong class="metric-value">{{ item.value }}</strong>
      </article>
    </section>

    <section class="panel">
      <ElTable :loading="loading" :data="tasks" row-key="id" height="640" @selection-change="selected = $event">
        <ElTableColumn type="selection" width="48" />
        <ElTableColumn prop="id" label="ID" width="80" />
        <ElTableColumn prop="task_id" label="任务" min-width="260" show-overflow-tooltip />
        <ElTableColumn prop="conversation_id" label="会话PK" width="100" />
        <ElTableColumn prop="rule_version" label="规则版本" min-width="170" show-overflow-tooltip />
        <ElTableColumn prop="model_name" label="模型" width="140" />
        <ElTableColumn prop="status" label="状态" width="110">
          <template #default="{ row }">
            <ElTag :type="statusType(row.status)">{{ row.status }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="error_message" label="错误" min-width="220" show-overflow-tooltip />
        <ElTableColumn prop="created_time" label="创建时间" min-width="170" show-overflow-tooltip />
      </ElTable>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import SmartQAAPI, { type QcDailySampleResult, type QcTask } from "@/api/module_smartqa";

const loading = ref(false);
const creating = ref(false);
const executing = ref(false);
const sampling = ref(false);
const samplingExecuting = ref(false);
const tasks = ref<QcTask[]>([]);
const selected = ref<QcTask[]>([]);
const conversationIds = ref("");
const ruleVersion = ref("smartqa-p0-20260625");
const sampleLimit = ref(100);
const sampleResult = ref<QcDailySampleResult>();

const sampleMetrics = computed(() => [
  { label: "抽检会话", value: sampleResult.value?.selected_count ?? 0 },
  { label: "覆盖客服", value: `${sampleResult.value?.covered_staff_count ?? 0}/${sampleResult.value?.staff_count ?? 0}` },
  { label: "新任务", value: sampleResult.value?.create_result.created ?? 0 },
  { label: "已存在", value: sampleResult.value?.create_result.skipped ?? 0 },
  { label: "执行成功", value: sampleResult.value?.execute_result?.success ?? "-" },
  { label: "执行失败", value: sampleResult.value?.execute_result?.failed ?? "-" },
]);

const taskMetrics = computed(() => [
  { label: "任务总数", value: tasks.value.length, hint: "当前列表" },
  { label: "待执行", value: tasks.value.filter((task) => task.status === "pending").length, hint: "可选中执行" },
  { label: "执行成功", value: tasks.value.filter((task) => task.status === "success").length, hint: "已生成质检结果" },
  { label: "执行失败", value: tasks.value.filter((task) => task.status === "failed").length, hint: "需查看错误" },
]);

function statusType(status: string) {
  if (status === "success") return "success";
  if (status === "failed") return "danger";
  if (status === "running") return "warning";
  return "info";
}

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.qcTasks({ limit: 500 });
    tasks.value = res.data.data || [];
  } finally {
    loading.value = false;
  }
}

async function createTasks() {
  const ids = conversationIds.value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter(Boolean);
  if (!ids.length) {
    ElMessage.warning("请输入会话主键ID");
    return;
  }
  creating.value = true;
  try {
    await SmartQAAPI.createTasks({
      conversation_ids: ids,
      rule_version: ruleVersion.value,
      model_name: "qwen3.7-plus",
    });
    conversationIds.value = "";
    await loadData();
  } finally {
    creating.value = false;
  }
}

async function executeTasks() {
  executing.value = true;
  try {
    await SmartQAAPI.executeTasks({
      task_ids: selected.value.map((task) => task.id),
      batch_size: selected.value.length,
    });
    await loadData();
  } finally {
    executing.value = false;
  }
}

async function createDailySample(execute: boolean) {
  if (execute) {
    samplingExecuting.value = true;
  } else {
    sampling.value = true;
  }
  try {
    const res = await SmartQAAPI.dailyQcSample({
      limit: sampleLimit.value,
      execute,
      rule_version: ruleVersion.value,
      model_name: "qwen3.7-plus",
    });
    sampleResult.value = res.data.data;
    ElMessage.success(execute ? "抽检执行完成" : "抽检任务已创建");
    await loadData();
  } finally {
    sampling.value = false;
    samplingExecuting.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped>
.smartqa-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ids-input {
  width: 300px;
}

.version-input {
  width: 220px;
}

.sample-input {
  width: 120px;
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
</style>
