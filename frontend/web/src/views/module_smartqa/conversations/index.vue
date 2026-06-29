<template>
  <div class="smartqa-screen review-page">
    <section class="page-head">
      <div>
        <h2>会话复盘</h2>
        <p>按客户、客服、商品、风险和质检状态检索会话，打开后查看聊天时间线、AI总结、问题证据和建议话术。</p>
      </div>
      <div class="head-actions">
        <ElInput
          v-model="keyword"
          clearable
          placeholder="客户、客服、商品"
          prefix-icon="Search"
          @keyup.enter="search"
        />
        <ElSelect v-model="qcStatus" clearable placeholder="质检状态" @change="search">
          <ElOption label="待质检" value="pending" />
          <ElOption label="已完成" value="completed" />
          <ElOption label="失败" value="failed" />
        </ElSelect>
        <ElButton :loading="loading" type="primary" icon="Search" @click="search">查询</ElButton>
        <ElButton icon="RefreshLeft" @click="resetFilters">重置</ElButton>
      </div>
    </section>

    <section class="summary-grid">
      <article v-for="item in summaryCards" :key="item.label" class="summary-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <em>{{ item.hint }}</em>
      </article>
    </section>

    <section class="panel">
      <ElTable :loading="loading" :data="rows" row-key="id" height="620" @row-dblclick="openDetail">
        <ElTableColumn prop="conversation_id" label="会话ID" min-width="150" show-overflow-tooltip />
        <ElTableColumn prop="shop_name" label="店铺" min-width="130" show-overflow-tooltip />
        <ElTableColumn prop="staff_name" label="客服" width="120" show-overflow-tooltip />
        <ElTableColumn prop="customer_account" label="客户" min-width="140" show-overflow-tooltip />
        <ElTableColumn prop="product_name" label="商品" min-width="220" show-overflow-tooltip />
        <ElTableColumn prop="message_count" label="消息" width="80" />
        <ElTableColumn prop="first_response_seconds" label="首响(s)" width="100" />
        <ElTableColumn prop="qc_status" label="质检" width="100">
          <template #default="{ row }">
            <ElTag :type="row.qc_status === 'completed' ? 'success' : row.qc_status === 'failed' ? 'danger' : 'info'">
              {{ statusText(row.qc_status) }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="start_time" label="开始时间" min-width="170" show-overflow-tooltip />
        <ElTableColumn label="操作" width="92" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openDetail(row)">复盘</ElButton>
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
    </section>

    <ElDrawer v-model="drawerVisible" size="860px" title="会话复盘">
      <div v-loading="detailLoading" class="drawer-body">
        <template v-if="detail">
          <section class="detail-card">
            <div class="detail-title">
              <div>
                <h3>{{ detail.conversation.customer_account || "未知客户" }}</h3>
                <p>{{ detail.conversation.product_name || "未知商品" }} · {{ detail.conversation.staff_name || "未绑定客服" }}</p>
              </div>
              <ElTag :type="detail.conversation.qc_status === 'completed' ? 'success' : 'info'" size="large">
                {{ statusText(detail.conversation.qc_status) }}
              </ElTag>
            </div>
            <ElDescriptions :column="2" border>
              <ElDescriptionsItem label="会话ID">{{ detail.conversation.conversation_id }}</ElDescriptionsItem>
              <ElDescriptionsItem label="消息数">{{ detail.conversation.message_count }}</ElDescriptionsItem>
              <ElDescriptionsItem label="首响">{{ detail.conversation.first_response_seconds ?? "-" }} 秒</ElDescriptionsItem>
              <ElDescriptionsItem label="开始时间">{{ detail.conversation.start_time || "-" }}</ElDescriptionsItem>
            </ElDescriptions>
          </section>

          <section class="detail-card ai-card">
            <div class="card-head">
              <strong>AI总结与结论</strong>
              <ElTag v-if="qcDetail" :type="riskTag(qcDetail.result.risk_level)">
                {{ riskText(qcDetail.result.risk_level) }}
              </ElTag>
            </div>
            <template v-if="qcDetail">
              <div class="score-line">
                <span>质检分</span>
                <strong>{{ qcDetail.result.score }}</strong>
                <em>{{ qcDetail.result.summary || "暂无摘要" }}</em>
              </div>
              <div class="issue-list">
                <article v-for="issue in qcDetail.issues" :key="issue.id">
                  <div>
                    <strong>{{ issue.title }}</strong>
                    <ElTag :type="riskTag(issue.severity)" effect="plain">{{ riskText(issue.severity) }}</ElTag>
                  </div>
                  <p>{{ issue.reason || "未返回具体原因" }}</p>
                  <p>{{ issue.suggested_action || "建议复盘该段会话并补齐下一步动作。" }}</p>
                  <ElButton v-if="issue.suggested_reply" text icon="DocumentCopy" @click="copyText(issue.suggested_reply)">
                    复制话术
                  </ElButton>
                </article>
              </div>
            </template>
            <ElEmpty v-else description="当前会话暂无AI质检结果" :image-size="86" />
          </section>

          <section class="detail-card" v-if="qcDetail?.evidences?.length">
            <strong>问题证据</strong>
            <div class="evidence-list">
              <article v-for="evidence in qcDetail.evidences" :key="evidence.evidence_id">
                <span>{{ speakerText(evidence.speaker_type) }} · {{ evidence.speaker_account }} · {{ evidence.message_time || "-" }}</span>
                <p>{{ evidence.content_text || "-" }}</p>
              </article>
            </div>
          </section>

          <section class="detail-card">
            <strong>聊天时间线</strong>
            <div class="messages">
              <div v-for="msg in detail.messages" :key="msg.id" class="message" :class="msg.speaker_type">
                <div class="message-meta">
                  <span>{{ speakerText(msg.speaker_type) }}</span>
                  <span>{{ msg.speaker_account }}</span>
                  <span>{{ msg.message_time }}</span>
                </div>
                <div class="message-text">{{ msg.content_text || "-" }}</div>
              </div>
            </div>
          </section>
        </template>
      </div>
    </ElDrawer>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import SmartQAAPI, {
  type ConversationDetail,
  type ConversationRow,
  type QcResultDetail,
} from "@/api/module_smartqa";

const loading = ref(false);
const detailLoading = ref(false);
const rows = ref<ConversationRow[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const keyword = ref("");
const qcStatus = ref("");
const drawerVisible = ref(false);
const detail = ref<ConversationDetail>();
const qcDetail = ref<QcResultDetail>();

const summaryCards = computed(() => [
  { label: "当前页会话", value: rows.value.length, hint: `共 ${total.value} 条` },
  { label: "已完成质检", value: rows.value.filter((row) => row.qc_status === "completed").length, hint: "当前页" },
  { label: "待质检", value: rows.value.filter((row) => row.qc_status === "pending").length, hint: "当前页" },
  { label: "平均消息数", value: avgMessageCount.value, hint: "当前页" },
]);

const avgMessageCount = computed(() => {
  if (!rows.value.length) return "0.0";
  return (rows.value.reduce((sum, row) => sum + Number(row.message_count || 0), 0) / rows.value.length).toFixed(1);
});

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

function resetFilters() {
  keyword.value = "";
  qcStatus.value = "";
  search();
}

async function openDetail(row: ConversationRow) {
  drawerVisible.value = true;
  detailLoading.value = true;
  detail.value = undefined;
  qcDetail.value = undefined;
  try {
    const [conversationRes, qcListRes] = await Promise.all([
      SmartQAAPI.conversationDetail(row.id),
      SmartQAAPI.qcResults({ page_no: 1, page_size: 1, keyword: row.conversation_id }),
    ]);
    detail.value = conversationRes.data.data;
    const qcRow = qcListRes.data.data?.items?.[0];
    if (qcRow) {
      const qcRes = await SmartQAAPI.qcResultDetail(qcRow.id);
      qcDetail.value = qcRes.data.data;
    }
  } finally {
    detailLoading.value = false;
  }
}

function statusText(status?: string) {
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  return "待质检";
}

function riskText(value?: string) {
  const map: Record<string, string> = {
    none: "无风险",
    low: "低",
    medium: "中",
    high: "高",
    critical: "严重",
  };
  return map[value || ""] || value || "-";
}

function riskTag(value?: string): "success" | "warning" | "danger" | "info" {
  if (value === "critical" || value === "high") return "danger";
  if (value === "medium") return "warning";
  if (value === "none" || value === "low") return "success";
  return "info";
}

function speakerText(value?: string) {
  if (value === "staff") return "客服";
  if (value === "customer") return "客户";
  return "未知";
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制话术");
  } catch {
    ElMessage.warning("当前环境不支持自动复制");
  }
}

onMounted(loadData);
</script>

<style scoped>
.review-page {
}

.page-head,
.head-actions,
.detail-title,
.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.page-head h2,
.detail-title h3 {
  margin: 0;
  color: #1f2a44;
  font-size: 20px;
  font-weight: 760;
}

.page-head p,
.detail-title p {
  margin: 4px 0 0;
  color: #667085;
}

.head-actions {
  align-items: center;
}

.head-actions :deep(.el-input) {
  width: 280px;
}

.head-actions :deep(.el-select) {
  width: 140px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-card,
.panel,
.detail-card {
  border: 1px solid rgba(51, 84, 128, 0.1);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 26px rgba(29, 59, 103, 0.06);
}

.summary-card {
  padding: 14px;
}

.summary-card span,
.summary-card em {
  display: block;
  color: #667085;
  font-size: 12px;
  font-style: normal;
}

.summary-card strong {
  display: block;
  margin: 5px 0;
  color: #1f7bff;
  font-size: 28px;
}

.panel,
.detail-card {
  padding: 14px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

.drawer-body,
.messages,
.issue-list,
.evidence-list {
  display: grid;
  gap: 12px;
}

.score-line {
  display: grid;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 8px;
  background: #f7f9fd;
}

.score-line span,
.score-line em,
.evidence-list span {
  color: #667085;
  font-style: normal;
}

.score-line strong {
  color: #14a85b;
  font-size: 30px;
}

.issue-list article,
.evidence-list article,
.message {
  padding: 10px;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  background: #fff;
}

.issue-list article div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.issue-list p,
.evidence-list p {
  margin: 7px 0 0;
  color: #46546b;
  line-height: 1.65;
}

.message {
  border-left: 4px solid #98a2b3;
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
  .head-actions {
    display: grid;
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
