<template>
  <div class="smartqa-bi-page">
    <div class="page-head">
      <div>
        <h2>老板工作台</h2>
        <p>服务质量、客户意向、留资承接和商品机会一屏看清</p>
      </div>
      <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
    </div>

    <div class="metric-grid">
      <section v-for="item in metrics" :key="item.label" class="metric-tile">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <em>{{ item.hint }}</em>
      </section>
    </div>

    <div class="bi-grid">
      <section class="panel panel-wide">
        <header>
          <div>
            <h3>高意向客户池</h3>
            <p>H1/H2 客户、负责客服、承接状态和下一步动作</p>
          </div>
          <ElTag type="danger" effect="plain">{{ hCustomers.length }} 个重点客户</ElTag>
        </header>
        <ElTable :loading="loading" :data="hCustomers" height="420" row-key="result_id">
          <ElTableColumn prop="intent_tier" label="等级" width="76">
            <template #default="{ row }">
              <ElTag :type="row.intent_tier === 'H1' ? 'danger' : 'warning'">{{ row.intent_tier }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="intent_score" label="意向" width="78" />
          <ElTableColumn prop="customer_account" label="客户" min-width="130" show-overflow-tooltip />
          <ElTableColumn prop="staff_name" label="客服" width="110" show-overflow-tooltip />
          <ElTableColumn prop="product_name" label="商品" min-width="210" show-overflow-tooltip />
          <ElTableColumn prop="need_summary" label="需求摘要" min-width="260" show-overflow-tooltip />
          <ElTableColumn prop="intent_reason_text" label="意向原因" min-width="220" show-overflow-tooltip />
          <ElTableColumn label="留资" width="110">
            <template #default="{ row }">
              <ElTag :type="contactTag(row).type" effect="plain">{{ contactTag(row).text }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="next_action" label="下一步" min-width="220" show-overflow-tooltip />
          <ElTableColumn label="证据" width="82">
            <template #default="{ row }">{{ row.evidence_count || 0 }} 条</template>
          </ElTableColumn>
        </ElTable>
      </section>

      <section class="panel">
        <header>
          <div>
            <h3>商机漏斗</h3>
            <p>从咨询到留资承接的真实转化</p>
          </div>
        </header>
        <div class="funnel">
          <div v-for="stage in funnel" :key="stage.stage" class="funnel-row">
            <div class="funnel-meta">
              <span>{{ stage.label }}</span>
              <strong>{{ stage.value }}</strong>
            </div>
            <div class="funnel-bar">
              <i :style="{ width: `${Math.max(stage.rate, 4)}%` }"></i>
            </div>
            <em>{{ stage.rate }}%</em>
          </div>
        </div>
      </section>

      <section class="panel">
        <header>
          <div>
            <h3>客服承接能力</h3>
            <p>不只看均分，也看高意向客户有没有被接住</p>
          </div>
        </header>
        <ElTable :loading="loading" :data="ranking" height="320" row-key="staff_id">
          <ElTableColumn prop="staff_name" label="客服" min-width="110" show-overflow-tooltip />
          <ElTableColumn prop="avg_score" label="均分" width="76" />
          <ElTableColumn prop="h_customer_count" label="H客户" width="82" />
          <ElTableColumn prop="contact_request_rate" label="留资询问率" width="112">
            <template #default="{ row }">{{ row.contact_request_rate || 0 }}%</template>
          </ElTableColumn>
          <ElTableColumn prop="high_risk_count" label="高风险" width="86" />
        </ElTable>
      </section>

      <section class="panel panel-wide">
        <header>
          <div>
            <h3>商品机会</h3>
            <p>哪些商品更容易带来高意向、定制和批量需求</p>
          </div>
        </header>
        <ElTable :loading="loading" :data="products" height="340" row-key="product_name">
          <ElTableColumn prop="product_name" label="商品" min-width="260" show-overflow-tooltip />
          <ElTableColumn prop="conversation_count" label="会话" width="80" />
          <ElTableColumn prop="h_customer_count" label="H客户" width="86" />
          <ElTableColumn prop="h_customer_rate" label="高意向率" width="96">
            <template #default="{ row }">{{ row.h_customer_rate }}%</template>
          </ElTableColumn>
          <ElTableColumn prop="avg_intent_score" label="平均意向" width="100" />
          <ElTableColumn prop="custom_count" label="定制" width="80" />
          <ElTableColumn prop="bulk_count" label="批量" width="80" />
          <ElTableColumn prop="price_sensitive_count" label="价格敏感" width="100" />
        </ElTable>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import SmartQAAPI, {
  type DashboardOverview,
  type IntentCustomer,
  type OpportunityFunnelStage,
  type ProductOpportunity,
  type SmartQAHealth,
  type StaffRanking,
} from "@/api/module_smartqa";

const loading = ref(false);
const overview = ref<DashboardOverview>();
const health = ref<SmartQAHealth>();
const ranking = ref<StaffRanking[]>([]);
const intents = ref<IntentCustomer[]>([]);
const funnel = ref<OpportunityFunnelStage[]>([]);
const products = ref<ProductOpportunity[]>([]);

const hCustomers = computed(() => intents.value.filter((row) => ["H1", "H2"].includes(row.intent_tier)).slice(0, 30));

const metrics = computed(() => [
  { label: "总会话", value: overview.value?.conversation_count ?? 0, hint: "千牛真实会话" },
  { label: "已质检", value: overview.value?.qc_count ?? 0, hint: "AI结构化结果" },
  { label: "服务均分", value: overview.value?.avg_score ?? 0, hint: health.value?.ali_model_name || "qwen3.7-plus" },
  { label: "H1/H2客户", value: overview.value?.high_intent_count ?? 0, hint: "优先跟进池" },
  { label: "高意向承接率", value: `${overview.value?.h_handoff_rate ?? 0}%`, hint: "报价/留资/下单" },
  { label: "留资成功率", value: `${overview.value?.contact_success_rate ?? 0}%`, hint: "客户已提供联系方式" },
]);

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
    const [healthRes, overviewRes, rankingRes, intentsRes, funnelRes, productRes] = await Promise.all([
      SmartQAAPI.health(),
      SmartQAAPI.dashboardOverview(),
      SmartQAAPI.staffRanking(20),
      SmartQAAPI.intentCustomers({ limit: 120 }),
      SmartQAAPI.opportunityFunnel(),
      SmartQAAPI.productOpportunities(30),
    ]);
    health.value = healthRes.data.data;
    overview.value = overviewRes.data.data;
    ranking.value = rankingRes.data.data || [];
    intents.value = intentsRes.data.data || [];
    funnel.value = funnelRes.data.data || [];
    products.value = productRes.data.data || [];
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped>
.smartqa-bi-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 100%;
  padding: 14px;
  color: #17202a;
  background:
    linear-gradient(135deg, rgba(28, 126, 214, 0.08), transparent 38%),
    linear-gradient(315deg, rgba(18, 184, 134, 0.08), transparent 32%),
    var(--el-bg-color-page);
}

.page-head,
.panel,
.metric-tile {
  border: 1px solid rgba(70, 86, 105, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 8px 24px rgba(30, 41, 59, 0.06);
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
}

.page-head h2,
.panel h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 720;
}

.page-head p,
.panel p {
  margin: 5px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.metric-tile {
  display: grid;
  gap: 8px;
  min-height: 112px;
  padding: 16px;
}

.metric-tile span,
.metric-tile em {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  font-style: normal;
}

.metric-tile strong {
  font-size: 26px;
  line-height: 1;
}

.bi-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.65fr);
  gap: 12px;
}

.panel {
  min-width: 0;
  padding: 14px;
}

.panel-wide {
  grid-column: span 1;
}

.panel header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.funnel {
  display: grid;
  gap: 14px;
  padding: 4px 2px;
}

.funnel-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
}

.funnel-meta {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.funnel-bar {
  height: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: #eef2f7;
}

.funnel-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1c7ed6, #12b886);
}

.funnel-row em {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-style: normal;
}

@media (max-width: 1200px) {
  .metric-grid,
  .bi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .metric-grid,
  .bi-grid {
    grid-template-columns: 1fr;
  }
}
</style>
