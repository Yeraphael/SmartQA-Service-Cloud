<template>
  <div class="smartqa-screen smartqa-product-page">
    <section class="page-head">
      <div>
        <h2>商品机会</h2>
        <p>看清哪些商品咨询多、意向强、问题集中，辅助话术和详情页优化。</p>
      </div>
      <div class="head-actions">
        <ElInput v-model="keyword" clearable placeholder="搜索商品" prefix-icon="Search" />
        <ElButton icon="RefreshLeft" @click="resetKeyword">重置</ElButton>
        <ElButton :loading="loading" type="primary" icon="Refresh" @click="loadData">刷新</ElButton>
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
            <strong>商品机会排行</strong>
            <ElRadioGroup v-model="sortKey" size="small">
              <ElRadioButton label="h_customer_count">高意向</ElRadioButton>
              <ElRadioButton label="conversation_count">咨询量</ElRadioButton>
              <ElRadioButton label="h_customer_rate">意向率</ElRadioButton>
            </ElRadioGroup>
          </div>
        </template>
        <ElTable :loading="loading" :data="filteredRows" row-key="product_name" height="620" @row-click="selectProduct">
          <ElTableColumn label="排名" width="70">
            <template #default="{ $index }">{{ $index + 1 }}</template>
          </ElTableColumn>
          <ElTableColumn prop="product_name" label="商品/功能" min-width="240" show-overflow-tooltip />
          <ElTableColumn prop="conversation_count" label="咨询数" width="96" sortable />
          <ElTableColumn prop="h_customer_count" label="高意向" width="96" sortable />
          <ElTableColumn label="高意向率" width="120">
            <template #default="{ row }">
              <ElProgress :percentage="percent(row.h_customer_rate)" :stroke-width="8" />
            </template>
          </ElTableColumn>
          <ElTableColumn prop="avg_intent_score" label="平均意向分" width="116" />
          <ElTableColumn label="信号" min-width="210">
            <template #default="{ row }">
              <div class="tag-list">
                <ElTag v-if="row.custom_count" effect="plain">定制 {{ row.custom_count }}</ElTag>
                <ElTag v-if="row.bulk_count" type="success" effect="plain">批量 {{ row.bulk_count }}</ElTag>
                <ElTag v-if="row.price_sensitive_count" type="warning" effect="plain">价格 {{ row.price_sensitive_count }}</ElTag>
              </div>
            </template>
          </ElTableColumn>
          <ElTableColumn label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <ElButton link type="primary" @click.stop="selectProduct(row)">详情</ElButton>
            </template>
          </ElTableColumn>
        </ElTable>
      </ElCard>

      <aside class="side-panel">
        <ElCard shadow="never">
          <template #header><strong>当前商品</strong></template>
          <div v-if="selected" class="product-detail">
            <h3>{{ selected.product_name }}</h3>
            <div class="score-ring" :style="{ '--score-percent': `${percent(selected.h_customer_rate)}%` }">
              <strong>{{ percent(selected.h_customer_rate) }}%</strong>
              <span>高意向率</span>
            </div>
            <div class="detail-list">
              <div><span>咨询会话</span><strong>{{ selected.conversation_count }}</strong></div>
              <div><span>高意向客户</span><strong>{{ selected.h_customer_count }}</strong></div>
              <div><span>平均意向分</span><strong>{{ fixed(selected.avg_intent_score) }}</strong></div>
              <div><span>转化潜力</span><strong>{{ productStars(selected) }}</strong></div>
            </div>
          </div>
          <ElEmpty v-else description="点击商品查看详情" :image-size="80" />
        </ElCard>

        <ElCard shadow="never">
          <template #header><strong>优化方向</strong></template>
          <div v-if="selected" class="suggestion-list">
            <article v-for="item in suggestions" :key="item.title">
              <strong>{{ item.title }}</strong>
              <p>{{ item.text }}</p>
            </article>
          </div>
          <ElEmpty v-else description="选择商品后生成建议" :image-size="80" />
        </ElCard>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import SmartQAAPI, { type ProductOpportunity } from "@/api/module_smartqa";

const loading = ref(false);
const rows = ref<ProductOpportunity[]>([]);
const selected = ref<ProductOpportunity>();
const keyword = ref("");
const sortKey = ref<"h_customer_count" | "conversation_count" | "h_customer_rate">("h_customer_count");

const filteredRows = computed(() => {
  const kw = keyword.value.trim().toLowerCase();
  const list = kw ? rows.value.filter((row) => row.product_name.toLowerCase().includes(kw)) : rows.value;
  return [...list].sort((a, b) => Number(b[sortKey.value] || 0) - Number(a[sortKey.value] || 0));
});

const summaryCards = computed(() => {
  const conversationCount = rows.value.reduce((sum, row) => sum + row.conversation_count, 0);
  const highIntentCount = rows.value.reduce((sum, row) => sum + row.h_customer_count, 0);
  const customCount = rows.value.reduce((sum, row) => sum + row.custom_count, 0);
  const priceCount = rows.value.reduce((sum, row) => sum + row.price_sensitive_count, 0);
  return [
    { label: "商品数", value: rows.value.length, hint: "有咨询记录" },
    { label: "咨询会话", value: conversationCount, hint: "当前周期" },
    { label: "高意向客户", value: highIntentCount, hint: "H1/H2 聚合" },
    { label: "定制/价格信号", value: `${customCount}/${priceCount}`, hint: "定制需求 / 价格敏感" },
  ];
});

const suggestions = computed(() => {
  if (!selected.value) return [];
  const item = selected.value;
  return [
    {
      title: "话术重点",
      text: item.h_customer_count > 0 ? "优先准备报价、交期、规格差异和留资承接话术。" : "补充基础咨询答疑话术，先提升需求确认质量。",
    },
    {
      title: "详情页重点",
      text: item.price_sensitive_count > 0 ? "详情页突出价格构成、套餐差异和售后保障。" : "详情页补充规格、材质、安装、适用场景等高频信息。",
    },
    {
      title: "客服训练重点",
      text: item.custom_count > 0 ? "训练客服追问尺寸、场景、数量、预算、交期，并及时留资。" : "训练客服把客户问题转化为明确下一步动作。",
    },
  ];
});

function percent(value: number) {
  const numeric = Number(value || 0);
  return Math.max(0, Math.min(100, Math.round(numeric <= 1 ? numeric * 100 : numeric)));
}

function fixed(value: number) {
  return Number(value || 0).toFixed(1);
}

function productStars(item: ProductOpportunity) {
  const score = Math.min(5, Math.max(1, Math.ceil(percent(item.h_customer_rate) / 20)));
  return "★".repeat(score) + "☆".repeat(5 - score);
}

function selectProduct(row: ProductOpportunity) {
  selected.value = row;
}

function resetKeyword() {
  keyword.value = "";
}

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.productOpportunities(100);
    rows.value = res.data.data || [];
    selected.value = rows.value[0];
  } finally {
    loading.value = false;
  }
}

watch(filteredRows, (list) => {
  if (list.length && selected.value && !list.some((row) => row.product_name === selected.value?.product_name)) {
    selected.value = list[0];
  }
});

onMounted(loadData);
</script>

<style scoped>
.smartqa-product-page {
}

.page-head,
.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.page-head h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 760;
}

.page-head p {
  margin: 4px 0 0;
  color: #667085;
}

.head-actions {
  display: grid;
  grid-template-columns: minmax(240px, 320px) auto auto;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-card {
  padding: 16px;
  border: 1px solid rgba(51, 84, 128, 0.1);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 26px rgba(29, 59, 103, 0.06);
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
  grid-template-columns: minmax(0, 1fr) 340px;
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

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.product-detail h3 {
  margin: 0 0 12px;
  font-size: 17px;
}

.score-ring {
  display: grid;
  place-items: center;
  width: 148px;
  height: 148px;
  margin: 0 auto 14px;
  border-radius: 50%;
  background: conic-gradient(#2f80ed 0 var(--score-percent), #edf2f7 var(--score-percent) 100%);
}

.score-ring strong {
  color: #1f2a44;
  font-size: 28px;
}

.score-ring span {
  color: #667085;
}

.detail-list,
.suggestion-list {
  display: grid;
  gap: 10px;
}

.detail-list div,
.suggestion-list article {
  padding: 10px;
  border-radius: 7px;
  background: #f7f9fd;
}

.detail-list div {
  display: flex;
  justify-content: space-between;
}

.suggestion-list strong {
  display: block;
  margin-bottom: 5px;
}

.suggestion-list p {
  margin: 0;
  color: #667085;
  line-height: 1.65;
}

@media (max-width: 1100px) {
  .page-head,
  .content-grid {
    display: grid;
    grid-template-columns: 1fr;
  }

  .head-actions,
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
