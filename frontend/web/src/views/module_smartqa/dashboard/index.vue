<template>
  <div class="smartqa-screen boss-workbench" v-loading="loading">
    <section class="data-strip">
      <div class="strip-item">
        <span>RPA 获取时间</span>
        <strong>{{ formatDateTime(workbench?.status.rpa_fetch_time) }}</strong>
      </div>
      <div class="strip-item">
        <span>AI 分析完成时间</span>
        <strong>{{ formatDateTime(workbench?.status.ai_finished_time) }}</strong>
      </div>
      <div class="strip-item">
        <span>已分析会话数</span>
        <strong>{{ numberText(workbench?.status.analyzed_conversation_count) }}</strong>
      </div>
      <div class="strip-item">
        <span>系统状态</span>
        <strong class="status-ok">{{ workbench?.status.system_status || "待分析" }}</strong>
      </div>
    </section>

    <section class="metric-grid">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card">
        <div class="metric-icon" :class="metric.tone">
          <FaSvgIcon :icon="metric.icon" />
        </div>
        <div>
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
        </div>
      </article>
    </section>

    <main class="workbench-grid">
      <section class="panel ranking-panel">
        <div class="panel-title">
          <div>
            <h3>客服质检榜单</h3>
            <p>支持滚动查看全部客服，触碰高亮，点击后更新右侧客服详情</p>
          </div>
          <ElSelect v-model="selectedRange" size="small" class="range-select">
            <ElOption label="近7天" value="7d" />
            <ElOption label="今日" value="today" />
          </ElSelect>
        </div>

        <div class="dimension-tabs" role="tablist">
          <button
            v-for="dimension in dimensions"
            :key="dimension.key"
            class="dimension-tab"
            :class="{ active: activeDimension === dimension.key }"
            type="button"
            @click="activeDimension = dimension.key"
          >
            {{ dimension.label }}
          </button>
        </div>

        <div class="mini-awards">
          <div v-for="award in awardCards" :key="award.title" class="award-card">
            <span>{{ award.title }}</span>
            <strong>{{ award.name }}</strong>
            <em>{{ award.score }}</em>
          </div>
        </div>

        <div class="ranking-table">
          <div class="ranking-head">
            <span>排名</span>
            <span>客服</span>
            <span>{{ currentDimensionLabel }}得分</span>
            <span>综合得分</span>
            <span>排名变化</span>
            <span>趋势（近7日）</span>
            <span>主要问题</span>
            <span>状态</span>
          </div>
          <div class="ranking-body">
            <button
              v-for="(staff, index) in sortedStaff"
              :key="staff.staff_id"
              class="ranking-row"
              :class="{ selected: selectedStaff?.staff_id === staff.staff_id }"
              type="button"
              @click="selectStaff(staff)"
            >
              <span class="rank-cell">
                <b :class="rankClass(index)">{{ index + 1 }}</b>
              </span>
              <span class="staff-cell">
                <img :src="avatarUrl(staff.staff_id)" :alt="staff.staff_name" />
                <i>
                  <strong>{{ staff.staff_name }}</strong>
                  <em>{{ staff.role_label || staff.primary_account }}</em>
                </i>
              </span>
              <span class="score-cell" :class="scoreClass(dimensionScore(staff, activeDimension))">
                {{ dimensionScore(staff, activeDimension) }}
              </span>
              <span class="score-cell">{{ staff.overall_score }}</span>
              <span class="rank-change" :class="rankChangeClass(staff)">
                {{ rankChangeText(staff) }}
              </span>
              <span class="spark-cell">
                <SparkLine :points="staff.trend.map((item) => item.score)" />
              </span>
              <span class="issue-cell">{{ staff.main_issue }}</span>
              <span>
                <i class="status-pill" :class="statusClass(staff)">{{ statusText(staff) }}</i>
              </span>
            </button>
          </div>
        </div>
      </section>

      <section class="panel staff-detail-card" v-if="selectedStaff">
        <div class="staff-profile">
          <img :src="avatarUrl(selectedStaff.staff_id)" :alt="selectedStaff.staff_name" />
          <div>
            <h3>{{ selectedStaff.staff_name }}</h3>
            <ElTag type="success" effect="light" round>{{ statusText(selectedStaff) }}</ElTag>
            <p>{{ selectedStaff.primary_account || "已绑定客服账号" }}</p>
          </div>
        </div>
        <div class="detail-score">
          <span>综合服务分</span>
          <strong>{{ selectedStaff.overall_score }}</strong>
          <em>/100</em>
        </div>
        <RadarHexagon :values="radarValues" />
        <div class="detail-counts">
          <div>
            <span>高风险会话</span>
            <strong>{{ selectedStaff.high_risk_count }}</strong>
          </div>
          <div>
            <span>待跟进意向</span>
            <strong>{{ selectedStaff.pending_intent_count }}</strong>
          </div>
        </div>
      </section>

      <section class="panel quadrant-card">
        <div class="panel-title compact">
          <div>
            <h3>客服能力四象限</h3>
            <p>横轴服务效率，纵轴服务质量</p>
          </div>
        </div>
        <div class="quadrant-plot">
          <div class="axis x-axis"></div>
          <div class="axis y-axis"></div>
          <button
            v-for="point in quadrantPoints"
            :key="point.staff_id"
            class="quadrant-point"
            :class="{ active: selectedStaff?.staff_id === point.staff_id }"
            :style="{ left: `${point.x}%`, bottom: `${point.y}%` }"
            type="button"
            @click="selectStaffById(point.staff_id)"
          >
            {{ point.staff_name.slice(0, 2) }}
          </button>
          <span class="quad-label top-right">质量优秀 效率优秀</span>
          <span class="quad-label top-left">质量优秀 效率待升</span>
          <span class="quad-label bottom-left">质量待升 效率待升</span>
          <span class="quad-label bottom-right">效率优秀 质量待升</span>
        </div>
      </section>

      <section class="panel product-card">
        <div class="panel-title compact">
          <div>
            <h3>商品机会 Top 5</h3>
            <p>按商品咨询与高意向表现排序</p>
          </div>
        </div>
        <div class="product-table">
          <div class="product-row head">
            <span>排名</span>
            <span>商品/功能</span>
            <span>相关会话数</span>
            <span>高意向数</span>
            <span>转化潜力</span>
          </div>
          <div v-for="(product, index) in products" :key="product.product_id || product.product_name" class="product-row">
            <span>{{ index + 1 }}</span>
            <span>{{ product.product_name }}</span>
            <span>{{ product.conversation_count }}</span>
            <span>{{ product.h_customer_count }}</span>
            <span class="stars">{{ productStars(product) }}</span>
          </div>
        </div>
      </section>

      <section class="panel trend-card">
        <div class="panel-title compact">
          <div>
            <h3>近7天趋势</h3>
            <p>质量分、高风险会话、待跟进意向与会话量</p>
          </div>
          <ElSelect v-model="selectedRange" size="small" class="range-select">
            <ElOption label="近7天" value="7d" />
          </ElSelect>
        </div>
        <TrendChart :points="trendPoints" />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref, watch } from "vue";
import SmartQAAPI, {
  type BossDimension,
  type BossQuadrantPoint,
  type BossStaffQuality,
  type BossTrendPoint,
  type BossWorkbench,
  type ProductOpportunity,
} from "@/api/module_smartqa";

const SIX_DIMENSIONS = [
  { key: "response_efficiency", label: "响应效率" },
  { key: "service_attitude", label: "服务态度" },
  { key: "professional_ability", label: "专业能力" },
  { key: "problem_solving", label: "问题解决" },
  { key: "demand_mining", label: "需求挖掘" },
  { key: "conversion_progress", label: "成交推进" },
] as const;

const loading = ref(false);
const selectedRange = ref("7d");
const activeDimension = ref<BossDimension["key"]>("overall");
const selectedStaff = ref<BossStaffQuality | null>(null);
const workbench = ref<BossWorkbench | null>(null);

const dimensions = computed<BossDimension[]>(() => workbench.value?.dimensions || []);

const staffList = computed(() => workbench.value?.staff_quality || []);
const products = computed<ProductOpportunity[]>(() => (workbench.value?.product_opportunities || []).slice(0, 5));
const trendPoints = computed<BossTrendPoint[]>(() => workbench.value?.trend_7d || []);
const quadrantPoints = computed<BossQuadrantPoint[]>(() => workbench.value?.quadrant.points || []);

const currentDimensionLabel = computed(() => dimensions.value.find((item) => item.key === activeDimension.value)?.label || "综合表现");

const sortedStaff = computed(() => {
  const overallOrder = new Map(
    [...staffList.value]
      .sort((a, b) => b.overall_score - a.overall_score)
      .map((item, index) => [item.staff_id, index + 1])
  );
  return [...staffList.value]
    .sort((a, b) => dimensionScore(b, activeDimension.value) - dimensionScore(a, activeDimension.value))
    .map((item, index) => ({ ...item, currentRank: index + 1, overallRank: overallOrder.get(item.staff_id) || index + 1 }));
});

const metrics = computed(() => {
  const data = workbench.value?.metrics;
  return [
    { label: "总体服务质量分", value: fixed(data?.service_quality_score), icon: "ri:shield-star-line", tone: "blue" },
    { label: "高风险会话", value: numberText(data?.high_risk_conversation_count), icon: "ri:flashlight-line", tone: "red" },
    { label: "需关注客服数", value: numberText(data?.need_attention_staff_count), icon: "ri:user-warning-line", tone: "purple" },
    { label: "高意向未跟进数", value: numberText(data?.high_intent_pending_count), icon: "ri:user-search-line", tone: "orange" },
  ];
});

const awardCards = computed(() => {
  const labels: Array<[string, string]> = [
    ["综合表现最佳", "overall"],
    ["响应效率最佳", "response_efficiency"],
    ["服务态度最佳", "service_attitude"],
    ["专业能力最佳", "professional_ability"],
    ["问题解决最佳", "problem_solving"],
    ["需求挖掘最佳", "demand_mining"],
    ["成交推进最佳", "conversion_progress"],
  ];
  return labels.map(([title, key]) => {
    const winner = [...staffList.value].sort((a, b) => dimensionScore(b, key) - dimensionScore(a, key))[0];
    return {
      title,
      name: winner?.staff_name || "-",
      score: winner ? `${dimensionScore(winner, key)}` : "-",
    };
  });
});

const radarValues = computed(() =>
  SIX_DIMENSIONS.map((dimension) => ({
    label: dimension.label,
    value: dimensionScore(selectedStaff.value, dimension.key),
  }))
);

watch(
  staffList,
  (list) => {
    if (!selectedStaff.value && list.length) {
      selectedStaff.value = list[0] || null;
    }
  },
  { immediate: true }
);

function dimensionScore(staff: BossStaffQuality | null | undefined, key: string): number {
  if (!staff) return 0;
  if (key === "overall") return Number(staff.overall_score || 0);
  return Number(staff.dimensions?.[key] ?? staff.overall_score ?? 0);
}

function selectStaff(staff: BossStaffQuality) {
  selectedStaff.value = staff;
}

function selectStaffById(staffId: number) {
  const staff = staffList.value.find((item) => item.staff_id === staffId);
  if (staff) selectStaff(staff);
}

function rankClass(index: number) {
  if (index === 0) return "gold";
  if (index === 1) return "silver";
  if (index === 2) return "bronze";
  return "";
}

function rankChangeText(staff: BossStaffQuality & { currentRank?: number; overallRank?: number }) {
  const diff = (staff.overallRank || 0) - (staff.currentRank || 0);
  if (!diff) return "-";
  return diff > 0 ? `↑ ${diff}` : `↓ ${Math.abs(diff)}`;
}

function rankChangeClass(staff: BossStaffQuality & { currentRank?: number; overallRank?: number }) {
  const diff = (staff.overallRank || 0) - (staff.currentRank || 0);
  return diff > 0 ? "up" : diff < 0 ? "down" : "";
}

function scoreClass(score: number) {
  if (score >= 85) return "good";
  if (score >= 75) return "warn";
  return "bad";
}

function statusText(staff: BossStaffQuality) {
  const score = dimensionScore(staff, activeDimension.value);
  if (score >= 90) return "优秀";
  if (score >= 80) return "良好";
  if (score >= 70) return "需关注";
  return "需改进";
}

function statusClass(staff: BossStaffQuality) {
  const text = statusText(staff);
  return {
    good: text === "优秀" || text === "良好",
    warn: text === "需关注",
    bad: text === "需改进",
  };
}

function avatarUrl(staffId: number) {
  const index = (staffId % 10) + 1;
  return new URL(`../../../assets/images/avatar/avatar${index}.webp`, import.meta.url).href;
}

function productStars(product: ProductOpportunity) {
  const score = Math.min(5, Math.max(1, Math.ceil(normalizePercent(product.h_customer_rate) / 20)));
  return "★".repeat(score) + "☆".repeat(5 - score);
}

function normalizePercent(value?: number) {
  const numeric = Number(value || 0);
  return Math.max(0, Math.min(100, numeric <= 1 ? numeric * 100 : numeric));
}

function numberText(value?: number) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function fixed(value?: number) {
  return Number(value || 0).toFixed(1);
}

function formatDateTime(value?: string) {
  if (!value) return "-";
  const text = value.replace("T", " ");
  return text.length > 16 ? text.slice(5, 16) : text;
}

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.bossWorkbench();
    workbench.value = res.data.data;
    if (workbench.value?.staff_quality?.length) {
      selectedStaff.value = workbench.value.staff_quality[0] || null;
    }
  } finally {
    loading.value = false;
  }
}

const SparkLine = defineComponent({
  name: "SparkLine",
  props: {
    points: {
      type: Array<number>,
      default: () => [],
    },
  },
  setup(props) {
    return () => {
      const values = props.points;
      if (!values.length) {
        return h("svg", { viewBox: "0 0 90 28", class: "sparkline" });
      }
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min || 1;
      const width = 90;
      const height = 28;
      const d = values
        .map((value, index) => {
          const x = (index / Math.max(values.length - 1, 1)) * width;
          const y = height - ((value - min) / range) * (height - 6) - 3;
          return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
      const lastValue = values[values.length - 1] ?? 0;
      return h("svg", { viewBox: `0 0 ${width} ${height}`, class: "sparkline" }, [
        h("path", { d, fill: "none", stroke: lastValue >= 80 ? "#18b866" : "#ff6b35", "stroke-width": "2.4", "stroke-linecap": "round", "stroke-linejoin": "round" }),
      ]);
    };
  },
});

const RadarHexagon = defineComponent({
  name: "RadarHexagon",
  props: {
    values: {
      type: Array<{ label: string; value: number }>,
      default: () => [],
    },
  },
  setup(props) {
    const center = 120;
    const radius = 78;
    const pointAt = (index: number, rate = 1) => {
      const angle = (-90 + index * 60) * (Math.PI / 180);
      return {
        x: center + Math.cos(angle) * radius * rate,
        y: center + Math.sin(angle) * radius * rate,
      };
    };
    return () => {
      const axes = props.values.length ? props.values : SIX_DIMENSIONS.map((item) => ({ label: item.label, value: 0 }));
      const grid = [1, 0.75, 0.5, 0.25].map((rate) => pointString(axes.map((_, index) => pointAt(index, rate))));
      const shape = pointString(axes.map((item, index) => pointAt(index, Math.max(Math.min(item.value, 100), 0) / 100)));
      return h("div", { class: "radar-wrap" }, [
        h("svg", { viewBox: "0 0 240 240", class: "radar-svg" }, [
          ...grid.map((points) => h("polygon", { points, class: "radar-grid" })),
          ...axes.map((_, index) => {
            const end = pointAt(index, 1);
            return h("line", { x1: center, y1: center, x2: end.x, y2: end.y, class: "radar-axis" });
          }),
          h("polygon", { points: shape, class: "radar-area" }),
          ...axes.map((item, index) => {
            const end = pointAt(index, 1.18);
            return h("text", { x: end.x, y: end.y, class: "radar-label", "text-anchor": "middle", "dominant-baseline": "middle" }, `${item.label} ${Math.round(item.value)}`);
          }),
        ]),
      ]);
    };
  },
});

const TrendChart = defineComponent({
  name: "TrendChart",
  props: {
    points: {
      type: Array<BossTrendPoint>,
      default: () => [],
    },
  },
  setup(props) {
    return () => {
      const points = props.points.length ? props.points : [];
      const width = 620;
      const height = 230;
      const series = [
        { key: "quality_score", label: "质量分", color: "#2f80ed" },
        { key: "high_risk_count", label: "高风险会话", color: "#ff3b30" },
        { key: "pending_intent_count", label: "高意向未跟进", color: "#ff9f1c" },
        { key: "conversation_count", label: "会话量", color: "#15b76c" },
      ] as const;
      const lines = series.map((item) => {
        const values = points.map((point) => Number(point[item.key] || 0));
        const max = Math.max(...values, item.key === "quality_score" ? 100 : 1);
        const min = item.key === "quality_score" ? 40 : 0;
        const range = max - min || 1;
        const d = values
          .map((value, index) => {
            const x = 34 + (index / Math.max(values.length - 1, 1)) * (width - 70);
            const y = height - 34 - ((value - min) / range) * (height - 76);
            return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${Math.max(20, Math.min(height - 34, y)).toFixed(1)}`;
          })
          .join(" ");
        return h("path", { d, fill: "none", stroke: item.color, "stroke-width": "3", "stroke-linecap": "round", "stroke-linejoin": "round" });
      });
      return h("div", { class: "trend-wrap" }, [
        h("div", { class: "trend-legend" }, series.map((item) => h("span", [h("i", { style: { background: item.color } }), item.label]))),
        h("svg", { viewBox: `0 0 ${width} ${height}`, class: "trend-svg" }, [
          h("line", { x1: 34, y1: 20, x2: 34, y2: height - 34, class: "trend-axis" }),
          h("line", { x1: 34, y1: height - 34, x2: width - 24, y2: height - 34, class: "trend-axis" }),
          ...[0, 1, 2, 3].map((i) => h("line", { x1: 34, y1: 38 + i * 42, x2: width - 24, y2: 38 + i * 42, class: "trend-grid" })),
          ...lines,
          ...points.map((point, index) => {
            const x = 34 + (index / Math.max(points.length - 1, 1)) * (width - 70);
            return h("text", { x, y: height - 10, class: "trend-date", "text-anchor": "middle" }, point.date);
          }),
        ]),
      ]);
    };
  },
});

function pointString(points: Array<{ x: number; y: number }>) {
  return points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
}

onMounted(loadData);
</script>

<style scoped>
.boss-workbench {
  min-height: 100%;
  overflow-x: auto;
  padding: 12px 16px 18px;
  color: #172033;
  background: #f5f8fd;
}

.data-strip,
.metric-card,
.panel {
  border: 1px solid rgba(51, 84, 128, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 26px rgba(29, 59, 103, 0.08);
}

.data-strip {
  display: grid;
  grid-template-columns: 1.1fr 1.25fr 1fr 0.9fr;
  gap: 0;
  min-width: 1320px;
  min-height: 48px;
  margin-bottom: 12px;
}

.strip-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  border-right: 1px solid #edf1f7;
}

.strip-item:last-child {
  border-right: 0;
}

.strip-item span {
  color: #667085;
  font-size: 13px;
}

.strip-item strong {
  color: #243654;
  font-size: 14px;
  font-weight: 720;
}

.status-ok {
  color: #18a957 !important;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  min-width: 1320px;
  margin-bottom: 10px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 18px;
  min-height: 84px;
  padding: 14px 18px;
}

.metric-icon {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border-radius: 50%;
  font-size: 32px;
}

.metric-icon.blue {
  color: #246bfe;
  background: #e8f0ff;
}

.metric-icon.red {
  color: #ff2f2f;
  background: #fff0ef;
}

.metric-icon.orange {
  color: #ff8a00;
  background: #fff3e2;
}

.metric-icon.purple {
  color: #7a43ff;
  background: #f0eaff;
}

.metric-icon.green {
  color: #16b364;
  background: #e9f8ef;
}

.metric-card span {
  display: block;
  color: #4d5a72;
  font-size: 14px;
}

.metric-card strong {
  display: block;
  margin-top: 4px;
  font-size: 30px;
  line-height: 1;
  color: #1f7bff;
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(620px, 1.55fr) minmax(320px, 0.8fr) minmax(320px, 0.8fr);
  grid-template-rows: minmax(560px, auto) minmax(250px, auto);
  gap: 10px;
  min-width: 1320px;
}

.panel {
  min-width: 0;
  padding: 12px;
}

.ranking-panel {
  grid-column: 1;
  grid-row: 1;
}

.staff-detail-card {
  display: flex;
  grid-column: 2;
  grid-row: 1;
  flex-direction: column;
}

.quadrant-card {
  display: flex;
  grid-column: 3;
  grid-row: 1;
  flex-direction: column;
}

.product-card {
  grid-column: 1;
  grid-row: 2;
  min-height: 250px;
}

.trend-card {
  grid-column: 2 / 4;
  grid-row: 2;
  min-height: 250px;
}

.panel-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-title h3 {
  margin: 0;
  color: #1f2a44;
  font-size: 17px;
  font-weight: 780;
}

.panel-title p {
  margin: 4px 0 0;
  color: #7a869c;
  font-size: 12px;
}

.panel-title.compact {
  margin-bottom: 8px;
}

.range-select {
  width: 92px;
}

.dimension-tabs {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.dimension-tab {
  height: 34px;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #41516f;
  background: #f4f7fb;
  cursor: pointer;
  transition: all 0.15s ease;
}

.dimension-tab.active,
.dimension-tab:hover {
  color: #fff;
  background: #2f80ed;
  box-shadow: 0 6px 14px rgba(47, 128, 237, 0.22);
}

.mini-awards {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 7px;
  margin-bottom: 10px;
}

.award-card {
  min-width: 0;
  padding: 8px;
  border: 1px solid #edf1f7;
  border-radius: 7px;
  background: #fbfcff;
}

.award-card span,
.award-card em {
  display: block;
  overflow: hidden;
  color: #69758c;
  font-size: 11px;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.award-card strong {
  display: block;
  overflow: hidden;
  margin: 4px 0;
  color: #253858;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ranking-table {
  overflow: hidden;
  border: 1px solid #edf1f7;
  border-radius: 7px;
}

.ranking-head,
.ranking-row {
  display: grid;
  grid-template-columns: 58px minmax(140px, 1.2fr) 108px 96px 90px 120px minmax(150px, 1fr) 86px;
  align-items: center;
  gap: 8px;
}

.ranking-head {
  height: 40px;
  padding: 0 10px;
  color: #667085;
  font-size: 12px;
  background: #f7f9fd;
}

.ranking-body {
  max-height: 510px;
  overflow-y: auto;
}

.ranking-row {
  width: 100%;
  min-height: 50px;
  padding: 0 10px;
  border: 0;
  border-bottom: 1px solid #eef2f7;
  color: #26344d;
  text-align: left;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ranking-row:hover,
.ranking-row.selected {
  position: relative;
  z-index: 1;
  background: #f0f7ff;
  box-shadow: inset 3px 0 0 #2f80ed;
}

.rank-cell b {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: #53627c;
  background: #edf2f7;
}

.rank-cell b.gold {
  color: #fff;
  background: #f5a400;
}

.rank-cell b.silver {
  color: #fff;
  background: #a7b0c1;
}

.rank-cell b.bronze {
  color: #fff;
  background: #e87933;
}

.staff-cell {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.staff-cell img,
.staff-profile img {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
}

.staff-cell i,
.staff-cell strong,
.staff-cell em {
  display: block;
  min-width: 0;
  font-style: normal;
}

.staff-cell strong,
.issue-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.staff-cell em {
  overflow: hidden;
  color: #718096;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.score-cell {
  font-weight: 760;
}

.score-cell.good {
  color: #13a65b;
}

.score-cell.warn {
  color: #ff8a00;
}

.score-cell.bad {
  color: #f04438;
}

.rank-change {
  color: #9aa5b8;
  font-weight: 700;
}

.rank-change.up {
  color: #12a150;
}

.rank-change.down {
  color: #ef4444;
}

.sparkline {
  width: 90px;
  height: 28px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 54px;
  height: 24px;
  border-radius: 999px;
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
}

.status-pill.good {
  color: #14a85b;
  background: #e9f8ef;
}

.status-pill.warn {
  color: #e67e00;
  background: #fff4df;
}

.status-pill.bad {
  color: #dc2626;
  background: #fff0ef;
}

.staff-profile {
  display: flex;
  align-items: center;
  gap: 12px;
}

.staff-profile img {
  width: 58px;
  height: 58px;
}

.staff-profile h3 {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0 8px 3px 0;
  font-size: 18px;
}

.staff-profile p {
  margin: 3px 0 0;
  color: #6b778d;
  font-size: 12px;
}

.detail-score {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 6px;
  margin: 10px 0 0;
}

.detail-score span {
  color: #667085;
  font-size: 13px;
}

.detail-score strong {
  color: #14a85b;
  font-size: 32px;
  line-height: 1;
}

.detail-score em {
  color: #98a2b3;
  font-style: normal;
}

.radar-wrap {
  flex: 1;
  min-height: 280px;
}

.radar-svg {
  width: 100%;
  height: 100%;
}

.radar-grid {
  fill: none;
  stroke: #d5e2f3;
  stroke-width: 1;
}

.radar-axis {
  stroke: #e3ebf7;
  stroke-width: 1;
}

.radar-area {
  fill: rgba(20, 184, 106, 0.24);
  stroke: #16b364;
  stroke-width: 2;
}

.radar-label {
  fill: #42526d;
  font-size: 10px;
}

.detail-counts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.detail-counts div {
  padding: 10px;
  border: 1px solid #edf1f7;
  border-radius: 7px;
  text-align: center;
  background: #fbfcff;
}

.detail-counts span {
  display: block;
  color: #667085;
  font-size: 12px;
}

.detail-counts strong {
  display: block;
  margin-top: 5px;
  color: #1f2a44;
  font-size: 22px;
}

.quadrant-plot {
  position: relative;
  flex: 1;
  min-height: 430px;
  overflow: hidden;
  border-radius: 8px;
  background:
    linear-gradient(90deg, transparent calc(50% - 1px), #cfdbec calc(50% - 1px), #cfdbec calc(50% + 1px), transparent calc(50% + 1px)),
    linear-gradient(0deg, transparent calc(50% - 1px), #cfdbec calc(50% - 1px), #cfdbec calc(50% + 1px), transparent calc(50% + 1px)),
    #f8fbff;
}

.quadrant-point {
  position: absolute;
  display: grid;
  place-items: center;
  width: 38px;
  height: 26px;
  border: 2px solid #fff;
  border-radius: 999px;
  color: #fff;
  font-size: 12px;
  background: #2f80ed;
  box-shadow: 0 8px 18px rgba(47, 128, 237, 0.22);
  transform: translate(-50%, 50%);
  cursor: pointer;
}

.quadrant-point.active {
  background: #16b364;
  box-shadow: 0 0 0 5px rgba(22, 179, 100, 0.16);
}

.quad-label {
  position: absolute;
  color: #7b88a1;
  font-size: 11px;
  font-weight: 700;
}

.top-right {
  top: 12px;
  right: 12px;
  color: #16a05d;
}

.top-left {
  top: 12px;
  left: 12px;
  color: #2f80ed;
}

.bottom-left {
  bottom: 12px;
  left: 12px;
  color: #f04438;
}

.bottom-right {
  right: 12px;
  bottom: 12px;
  color: #6f6ce8;
}

.product-table {
  display: grid;
  gap: 0;
  overflow: hidden;
  border: 1px solid #edf1f7;
  border-radius: 7px;
}

.product-row {
  display: grid;
  grid-template-columns: 56px minmax(180px, 1fr) 100px 86px 98px;
  align-items: center;
  min-height: 34px;
  padding: 0 12px;
  border-bottom: 1px solid #eef2f7;
  color: #344054;
  font-size: 13px;
}

.product-row.head {
  color: #667085;
  background: #f7f9fd;
}

.product-row:last-child {
  border-bottom: 0;
}

.stars {
  color: #ff9f1c;
  letter-spacing: 1px;
}

.trend-wrap {
  min-height: 206px;
}

.trend-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin: 4px 0 2px;
  color: #4f5f7a;
  font-size: 12px;
}

.trend-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.trend-legend i {
  width: 18px;
  height: 3px;
  border-radius: 999px;
}

.trend-svg {
  width: 100%;
  height: 205px;
}

.trend-axis {
  stroke: #bcc8da;
  stroke-width: 1.2;
}

.trend-grid {
  stroke: #ecf1f8;
  stroke-width: 1;
}

.trend-date {
  fill: #738096;
  font-size: 12px;
}

</style>
