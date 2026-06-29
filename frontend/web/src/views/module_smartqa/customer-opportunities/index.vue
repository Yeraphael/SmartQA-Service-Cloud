<template>
  <div class="smartqa-screen smartqa-product-page">
    <section class="page-head">
      <div>
        <h2>客户商机</h2>
        <p>按意向等级、跟进缺口和证据定位客户机会。</p>
      </div>
      <div class="head-actions">
        <ElInput
          v-model="keyword"
          clearable
          placeholder="客户、客服、商品"
          prefix-icon="Search"
          @keyup.enter="search"
        />
        <ElSelect v-model="tier" clearable placeholder="意向等级" @change="search">
          <ElOption label="H1 立即跟进" value="H1" />
          <ElOption label="H2 重点跟进" value="H2" />
          <ElOption label="H3 常规跟进" value="H3" />
          <ElOption label="H4 待观察" value="H4" />
          <ElOption label="L 低意向" value="L" />
        </ElSelect>
        <ElButton icon="RefreshLeft" @click="resetFilters">重置</ElButton>
        <ElButton :loading="loading" type="primary" icon="Search" @click="search">查询</ElButton>
      </div>
    </section>

    <section class="summary-grid">
      <article v-for="item in summaryCards" :key="item.label" class="summary-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <em>{{ item.hint }}</em>
      </article>
    </section>

    <section class="content-grid">
      <ElCard shadow="never" class="main-card">
        <template #header>
          <div class="card-head">
            <strong>客户机会列表</strong>
            <ElButton :loading="loading" icon="Refresh" text @click="loadData">刷新</ElButton>
          </div>
        </template>
        <ElTable :loading="loading" :data="rows" row-key="result_id" height="590" @row-dblclick="openDetail">
          <ElTableColumn prop="intent_tier" label="等级" width="86" fixed>
            <template #default="{ row }">
              <ElTag :type="tierTag(row.intent_tier)">{{ row.intent_tier }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="intent_score" label="意向分" width="86" />
          <ElTableColumn prop="customer_account" label="客户" min-width="138" show-overflow-tooltip />
          <ElTableColumn prop="staff_name" label="负责客服" min-width="116" show-overflow-tooltip />
          <ElTableColumn prop="product_name" label="意向商品" min-width="220" show-overflow-tooltip />
          <ElTableColumn prop="need_summary" label="客户需求" min-width="250" show-overflow-tooltip />
          <ElTableColumn label="当前缺口" min-width="170" show-overflow-tooltip>
            <template #default="{ row }">{{ gapText(row) }}</template>
          </ElTableColumn>
          <ElTableColumn prop="next_action" label="建议动作" min-width="240" show-overflow-tooltip />
          <ElTableColumn label="证据" width="88" fixed="right">
            <template #default="{ row }">
              <ElButton link type="primary" @click="openDetail(row)">查看</ElButton>
            </template>
          </ElTableColumn>
        </ElTable>
      </ElCard>

      <aside class="side-panel">
        <ElCard shadow="never">
          <template #header><strong>跟进状态</strong></template>
          <div class="status-list">
            <div v-for="item in statusStats" :key="item.label">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </ElCard>
        <ElCard shadow="never">
          <template #header><strong>建议动作 Top</strong></template>
          <div class="action-list">
            <article v-for="item in actionStats" :key="item.text">
              <span>{{ item.text }}</span>
              <strong>{{ item.count }}</strong>
            </article>
          </div>
        </ElCard>
      </aside>
    </section>

    <ElDrawer v-model="drawerVisible" size="780px" title="客户商机证据">
      <div v-if="selected" class="drawer-body">
        <section class="detail-card">
          <div class="detail-title">
            <div>
              <h3>{{ selected.customer_account || selected.customer_alias_masked || "未知客户" }}</h3>
              <p>{{ selected.product_name || "未知商品" }} · {{ selected.staff_name || "未绑定客服" }}</p>
            </div>
            <ElTag :type="tierTag(selected.intent_tier)" size="large">{{ selected.intent_tier }} / {{ selected.intent_score }}</ElTag>
          </div>
          <ElDescriptions :column="2" border>
            <ElDescriptionsItem label="意向原因">{{ selected.intent_reason_text || "-" }}</ElDescriptionsItem>
            <ElDescriptionsItem label="跟进缺口">{{ gapText(selected) }}</ElDescriptionsItem>
            <ElDescriptionsItem label="沉默时长">{{ selected.silent_hours ?? "-" }} 小时</ElDescriptionsItem>
            <ElDescriptionsItem label="证据数">{{ selected.evidence_count || 0 }}</ElDescriptionsItem>
          </ElDescriptions>
        </section>

        <section class="detail-card">
          <div class="card-head">
            <strong>建议话术</strong>
            <ElButton icon="DocumentCopy" text @click="copyReply">复制</ElButton>
          </div>
          <ElInput :model-value="selected.suggested_reply || '暂无建议话术'" type="textarea" :rows="4" readonly />
        </section>

        <section class="detail-card">
          <strong>原始聊天证据</strong>
          <div v-loading="detailLoading" class="messages">
            <div v-for="msg in detail?.messages || []" :key="msg.id" class="message" :class="msg.speaker_type">
              <div class="message-meta">
                <span>{{ msg.speaker_type === "staff" ? "客服" : msg.speaker_type === "customer" ? "客户" : "未知" }}</span>
                <span>{{ msg.speaker_account }}</span>
                <span>{{ msg.message_time }}</span>
              </div>
              <div class="message-text">{{ msg.content_text || "-" }}</div>
            </div>
          </div>
        </section>
      </div>
    </ElDrawer>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import SmartQAAPI, { type ConversationDetail, type IntentCustomer } from "@/api/module_smartqa";

const loading = ref(false);
const detailLoading = ref(false);
const rows = ref<IntentCustomer[]>([]);
const keyword = ref("");
const tier = ref("");
const selected = ref<IntentCustomer>();
const detail = ref<ConversationDetail>();
const drawerVisible = ref(false);

const highIntentRows = computed(() => rows.value.filter((row) => ["H1", "H2"].includes(row.intent_tier)));
const pendingRows = computed(() => highIntentRows.value.filter((row) => !row.contact_requested || (row.silent_hours ?? 0) >= 24));

const summaryCards = computed(() => [
  { label: "客户机会", value: rows.value.length, hint: "当前筛选结果" },
  { label: "高意向客户", value: highIntentRows.value.length, hint: "H1/H2" },
  { label: "待跟进", value: pendingRows.value.length, hint: "联系确认或唤回动作" },
  { label: "已留联系方式", value: rows.value.filter((row) => row.contact_provided).length, hint: "可继续交接" },
]);

const statusStats = computed(() => [
  { label: "待报价", value: rows.value.filter((row) => !row.quote_given && ["H1", "H2"].includes(row.intent_tier)).length },
  { label: "待补问", value: rows.value.filter((row) => (row.missing_infos || []).length > 0).length },
  { label: "待联系确认", value: rows.value.filter((row) => !row.contact_requested && ["H1", "H2"].includes(row.intent_tier)).length },
  { label: "待唤回", value: rows.value.filter((row) => (row.silent_hours ?? 0) >= 24).length },
]);

const actionStats = computed(() => {
  const bucket = new Map<string, number>();
  rows.value.forEach((row) => {
    const text = row.next_action || "复盘会话并补齐下一步";
    bucket.set(text, (bucket.get(text) || 0) + 1);
  });
  return [...bucket.entries()]
    .map(([text, count]) => ({ text, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);
});

function tierTag(value: string): "danger" | "warning" | "success" | "info" {
  if (value === "H1") return "danger";
  if (value === "H2") return "warning";
  if (value === "H3") return "success";
  return "info";
}

function gapText(row: IntentCustomer) {
  if (!row.quote_given && ["H1", "H2"].includes(row.intent_tier)) return "待报价";
  if ((row.missing_infos || []).length) return `待补问：${row.missing_infos?.join("、")}`;
  if (!row.contact_requested && ["H1", "H2"].includes(row.intent_tier)) return "待联系确认";
  if ((row.silent_hours ?? 0) >= 24) return "待唤回";
  return "持续推进";
}

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.intentCustomers({
      limit: 200,
      keyword: keyword.value || undefined,
      tier: tier.value || undefined,
    });
    rows.value = res.data.data || [];
  } finally {
    loading.value = false;
  }
}

function search() {
  loadData();
}

function resetFilters() {
  keyword.value = "";
  tier.value = "";
  loadData();
}

async function openDetail(row: IntentCustomer) {
  selected.value = row;
  detail.value = undefined;
  drawerVisible.value = true;
  detailLoading.value = true;
  try {
    const res = await SmartQAAPI.conversationDetail(row.conversation_pk);
    detail.value = res.data.data;
  } finally {
    detailLoading.value = false;
  }
}

async function copyReply() {
  const text = selected.value?.suggested_reply || "";
  if (!text) {
    ElMessage.info("暂无可复制话术");
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制建议话术");
  } catch {
    ElMessage.warning("当前环境不支持自动复制");
  }
}

onMounted(loadData);
</script>

<style scoped>
.smartqa-product-page {
}

.page-head,
.card-head,
.detail-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.page-head h2,
.detail-title h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 760;
}

.page-head p,
.detail-title p {
  margin: 4px 0 0;
  color: #667085;
}

.head-actions {
  display: grid;
  grid-template-columns: minmax(240px, 320px) 138px auto auto;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-card,
.detail-card {
  border: 1px solid rgba(51, 84, 128, 0.1);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 26px rgba(29, 59, 103, 0.06);
}

.summary-card {
  padding: 16px;
}

.summary-card span,
.summary-card em {
  display: block;
  color: #667085;
  font-style: normal;
}

.summary-card strong {
  display: block;
  margin: 6px 0;
  color: #1f7bff;
  font-size: 30px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 12px;
}

.main-card,
.side-panel :deep(.el-card) {
  border-radius: 8px;
}

.side-panel {
  display: grid;
  align-content: start;
  gap: 12px;
}

.status-list,
.action-list,
.drawer-body,
.messages {
  display: grid;
  gap: 10px;
}

.status-list div,
.action-list article {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px;
  border-radius: 7px;
  background: #f7f9fd;
}

.detail-card {
  padding: 14px;
}

.message {
  padding: 10px;
  border: 1px solid #edf1f7;
  border-left: 4px solid #98a2b3;
  border-radius: 8px;
  background: #fff;
}

.message.staff {
  border-left-color: #2f80ed;
}

.message.customer {
  border-left-color: #16b364;
}

.message-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
  color: #667085;
  font-size: 12px;
}

.message-text {
  line-height: 1.65;
  white-space: pre-wrap;
}

@media (max-width: 1100px) {
  .page-head,
  .content-grid {
    grid-template-columns: 1fr;
  }

  .page-head {
    display: grid;
  }

  .head-actions,
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
