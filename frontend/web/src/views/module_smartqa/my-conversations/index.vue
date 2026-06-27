<template>
  <div class="intent-page">
    <div class="page-head">
      <div>
        <h2>我的意向客户</h2>
        <p>按优先级处理客户，看到原因、缺什么、下一步怎么说</p>
      </div>
      <div class="actions">
        <ElInput
          v-model="keyword"
          clearable
          placeholder="客户、商品"
          prefix-icon="Search"
          @keyup.enter="loadData"
        />
        <ElSelect v-model="tier" clearable placeholder="等级" @change="loadData">
          <ElOption label="H1 立即跟进" value="H1" />
          <ElOption label="H2 重点跟进" value="H2" />
          <ElOption label="H3 常规跟进" value="H3" />
          <ElOption label="H4 待观察" value="H4" />
          <ElOption label="L 低意向" value="L" />
        </ElSelect>
        <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
      </div>
    </div>

    <div class="summary-grid">
      <section v-for="item in summary" :key="item.label">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </section>
    </div>

    <ElTable :loading="loading" :data="rows" row-key="result_id" height="620" @row-dblclick="openDetail">
      <ElTableColumn prop="intent_tier" label="等级" width="86" fixed>
        <template #default="{ row }">
          <ElTag :type="tierTag(row.intent_tier)">{{ row.intent_tier }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="intent_score" label="意向分" width="86" />
      <ElTableColumn prop="customer_account" label="客户" min-width="135" show-overflow-tooltip />
      <ElTableColumn prop="product_name" label="商品" min-width="220" show-overflow-tooltip />
      <ElTableColumn prop="need_summary" label="需求摘要" min-width="280" show-overflow-tooltip />
      <ElTableColumn prop="intent_reason_text" label="为什么有意向" min-width="240" show-overflow-tooltip />
      <ElTableColumn label="缺失信息" min-width="170" show-overflow-tooltip>
        <template #default="{ row }">{{ (row.missing_infos || []).join("、") || "暂未识别" }}</template>
      </ElTableColumn>
      <ElTableColumn label="留资承接" width="116">
        <template #default="{ row }">
          <ElTag :type="contactTag(row).type" effect="plain">{{ contactTag(row).text }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="silent_hours" label="沉默(h)" width="90" />
      <ElTableColumn prop="next_action" label="下一步动作" min-width="240" show-overflow-tooltip />
      <ElTableColumn label="操作" width="106" fixed="right">
        <template #default="{ row }">
          <ElButton link type="primary" @click="openDetail(row)">证据</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDrawer v-model="drawerVisible" size="760px" title="客户跟进详情">
      <div v-if="selected" class="drawer-body">
        <section class="intent-card">
          <div class="intent-card-head">
            <div>
              <h3>{{ selected.customer_account || "未知客户" }}</h3>
              <p>{{ selected.product_name || "未知商品" }}</p>
            </div>
            <ElTag :type="tierTag(selected.intent_tier)" size="large">{{ selected.intent_tier }} / {{ selected.intent_score }}</ElTag>
          </div>
          <ElDescriptions :column="2" border>
            <ElDescriptionsItem label="阶段">{{ selected.lifecycle_stage || "-" }}</ElDescriptionsItem>
            <ElDescriptionsItem label="留资状态">{{ contactTag(selected).text }}</ElDescriptionsItem>
            <ElDescriptionsItem label="证据数">{{ selected.evidence_count || 0 }}</ElDescriptionsItem>
            <ElDescriptionsItem label="沉默时长">{{ selected.silent_hours ?? "-" }} 小时</ElDescriptionsItem>
          </ElDescriptions>
        </section>

        <section class="intent-card">
          <h4>意向原因</h4>
          <div class="reason-list">
            <div v-for="reason in selected.intent_reasons || []" :key="reason.reason_code || reason.reason_text">
              <strong>{{ reason.reason_text || reason.reason_code }}</strong>
              <span>{{ (reason.evidence_message_ids || []).join("、") }}</span>
            </div>
          </div>
        </section>

        <section class="intent-card">
          <h4>下一步动作</h4>
          <p>{{ selected.next_action || "复盘会话并补齐下一步动作" }}</p>
          <ElInput :model-value="selected.suggested_reply || '暂无建议话术'" type="textarea" :rows="4" readonly />
        </section>

        <section class="intent-card">
          <h4>原始聊天</h4>
          <div v-if="detail" class="messages">
            <div v-for="msg in detail.messages" :key="msg.id" class="message" :class="msg.speaker_type">
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
import { computed, onMounted, ref } from "vue";
import SmartQAAPI, {
  type ConversationDetail,
  type IntentCustomer,
} from "@/api/module_smartqa";

const loading = ref(false);
const rows = ref<IntentCustomer[]>([]);
const keyword = ref("");
const tier = ref("");
const drawerVisible = ref(false);
const selected = ref<IntentCustomer>();
const detail = ref<ConversationDetail>();

const summary = computed(() => {
  const hRows = rows.value.filter((row) => ["H1", "H2"].includes(row.intent_tier));
  return [
    { label: "我的客户", value: rows.value.length },
    { label: "H1/H2", value: hRows.length },
    { label: "未留资", value: hRows.filter((row) => !row.contact_requested).length },
    { label: "已留资待承接", value: hRows.filter((row) => row.contact_provided && !["ready", "matched", "converted"].includes(row.xianfa_handoff_status)).length },
  ];
});

function tierTag(value: string): "danger" | "warning" | "success" | "info" {
  if (value === "H1") return "danger";
  if (value === "H2") return "warning";
  if (value === "H3") return "success";
  return "info";
}

function contactTag(row: IntentCustomer): { type: "success" | "warning" | "danger" | "info"; text: string } {
  if (["ready", "matched", "converted"].includes(row.xianfa_handoff_status)) return { type: "success", text: "已承接" };
  if (row.contact_provided) return { type: "warning", text: "已留资" };
  if (row.contact_requested) return { type: "info", text: "已询问" };
  if (["H1", "H2"].includes(row.intent_tier)) return { type: "danger", text: "未留资" };
  return { type: "info", text: "未涉及" };
}

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.intentCustomers({
      limit: 120,
      keyword: keyword.value || undefined,
      tier: tier.value || undefined,
    });
    rows.value = res.data.data || [];
  } finally {
    loading.value = false;
  }
}

async function openDetail(row: IntentCustomer) {
  selected.value = row;
  detail.value = undefined;
  drawerVisible.value = true;
  const res = await SmartQAAPI.conversationDetail(row.conversation_pk);
  detail.value = res.data.data;
}

onMounted(loadData);
</script>

<style scoped>
.intent-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100%;
  padding: 14px;
  background: var(--el-bg-color-page);
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.page-head h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 720;
}

.page-head p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
}

.actions {
  display: grid;
  grid-template-columns: minmax(220px, 320px) 150px auto;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-grid section,
.intent-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
}

.summary-grid section {
  padding: 14px;
}

.summary-grid span {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.summary-grid strong {
  display: block;
  margin-top: 8px;
  font-size: 26px;
}

.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.intent-card {
  padding: 14px;
}

.intent-card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.intent-card h3,
.intent-card h4 {
  margin: 0 0 10px;
}

.intent-card p {
  color: var(--el-text-color-secondary);
  line-height: 1.7;
}

.reason-list {
  display: grid;
  gap: 8px;
}

.reason-list div {
  display: grid;
  gap: 4px;
  padding: 10px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.reason-list span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.message {
  padding: 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-left: 4px solid var(--el-color-info);
  border-radius: 8px;
}

.message.staff {
  border-left-color: var(--el-color-primary);
}

.message.customer {
  border-left-color: var(--el-color-success);
}

.message-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.message-text {
  line-height: 1.65;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .page-head {
    flex-direction: column;
  }

  .actions,
  .summary-grid {
    width: 100%;
    grid-template-columns: 1fr;
  }
}
</style>
