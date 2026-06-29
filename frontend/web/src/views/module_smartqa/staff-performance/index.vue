<template>
  <div class="smartqa-screen performance-page" v-loading="loading">
    <section class="page-head">
      <div>
        <h2>客服表现</h2>
        <p>按综合表现、响应效率、服务态度、专业能力、问题解决、需求挖掘、成交推进查看客服排名。</p>
      </div>
      <div class="head-actions">
        <ElInput v-model="keyword" clearable placeholder="搜索客服或账号" prefix-icon="Search" />
        <ElButton :loading="loading" type="primary" icon="Refresh" @click="loadData">刷新</ElButton>
      </div>
    </section>

    <section class="dimension-strip">
      <button
        v-for="dimension in dimensions"
        :key="dimension.key"
        class="dimension-card"
        :class="{ active: activeDimension === dimension.key }"
        type="button"
        @click="activeDimension = dimension.key"
      >
        <span>{{ dimension.label }}</span>
        <strong>{{ dimensionLeader(dimension.key)?.staff_name || "-" }}</strong>
        <em>{{ dimensionLeader(dimension.key) ? dimensionScore(dimensionLeader(dimension.key), dimension.key) : "-" }}</em>
      </button>
    </section>

    <section class="summary-grid">
      <article v-for="item in summaryCards" :key="item.label" class="summary-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <em>{{ item.hint }}</em>
      </article>
    </section>

    <main class="content-grid">
      <section class="panel ranking-panel">
        <div class="panel-head">
          <div>
            <h3>{{ currentDimensionLabel }}排名</h3>
            <p>触碰高亮，点击客服后查看右侧拆解。</p>
          </div>
          <ElTag effect="plain">{{ filteredStaff.length }} 人</ElTag>
        </div>

        <div class="ranking-table">
          <div class="ranking-head">
            <span>排名</span>
            <span>客服</span>
            <span>当前维度</span>
            <span>综合得分</span>
            <span>高风险</span>
            <span>待跟进意向</span>
            <span>主要问题</span>
            <span>状态</span>
          </div>
          <button
            v-for="(staff, index) in filteredStaff"
            :key="staff.staff_id"
            type="button"
            class="ranking-row"
            :class="{ selected: selectedStaff?.staff_id === staff.staff_id }"
            @click="selectStaff(staff)"
          >
            <span class="rank-badge" :class="rankClass(index)">{{ index + 1 }}</span>
            <span class="staff-cell">
              <img :src="avatarUrl(staff.staff_id)" :alt="staff.staff_name" />
              <i>
                <strong>{{ staff.staff_name }}</strong>
                <em>{{ staff.primary_account || "未绑定账号" }}</em>
              </i>
            </span>
            <span class="score-cell" :class="scoreClass(dimensionScore(staff, activeDimension))">
              {{ dimensionScore(staff, activeDimension) }}
            </span>
            <span class="score-cell">{{ staff.overall_score }}</span>
            <span>{{ staff.high_risk_count }}</span>
            <span>{{ staff.pending_intent_count }}</span>
            <span class="issue-cell">{{ staff.main_issue }}</span>
            <span>
              <i class="status-pill" :class="statusClass(staff)">{{ statusText(staff) }}</i>
            </span>
          </button>
        </div>
      </section>

      <aside class="panel detail-panel">
        <template v-if="selectedStaff">
          <div class="profile">
            <img :src="avatarUrl(selectedStaff.staff_id)" :alt="selectedStaff.staff_name" />
            <div>
              <h3>{{ selectedStaff.staff_name }}</h3>
              <p>{{ selectedStaff.primary_account || "未绑定账号" }}</p>
            </div>
            <strong>{{ selectedStaff.overall_score }}</strong>
          </div>

          <div class="bar-list">
            <div v-for="dimension in abilityDimensions" :key="dimension.key" class="bar-row">
              <span>{{ dimension.label }}</span>
              <div class="bar-track">
                <i :style="{ width: `${dimensionScore(selectedStaff, dimension.key)}%` }"></i>
              </div>
              <strong>{{ dimensionScore(selectedStaff, dimension.key) }}</strong>
            </div>
          </div>

          <div class="count-grid">
            <div>
              <span>高风险会话</span>
              <strong>{{ selectedStaff.high_risk_count }}</strong>
            </div>
            <div>
              <span>待跟进意向</span>
              <strong>{{ selectedStaff.pending_intent_count }}</strong>
            </div>
            <div>
              <span>已质检</span>
              <strong>{{ selectedStaff.qc_count }}</strong>
            </div>
            <div>
              <span>总会话</span>
              <strong>{{ selectedStaff.conversation_count }}</strong>
            </div>
          </div>

          <section class="insight-block">
            <div class="panel-head compact">
              <h4>主要问题</h4>
              <ElButton :loading="detailLoading" text icon="Refresh" @click="loadStaffInsight(selectedStaff)">刷新</ElButton>
            </div>
            <div v-if="staffInsight?.frequent_issues?.length" class="issue-list">
              <article v-for="issue in staffInsight.frequent_issues.slice(0, 5)" :key="issue.title">
                <strong>{{ issue.title }}</strong>
                <p>{{ issue.suggested_action || issue.reason || "复盘对应会话，补齐下一步动作。" }}</p>
                <em>{{ issue.issue_count }} 次</em>
              </article>
            </div>
            <ElEmpty v-else description="暂无明显问题" :image-size="78" />
          </section>

          <section class="insight-block">
            <h4>建议话术</h4>
            <div v-if="staffInsight?.suggested_replies?.length" class="reply-list">
              <article v-for="reply in staffInsight.suggested_replies.slice(0, 3)" :key="reply.suggested_reply">
                <strong>{{ reply.title }}</strong>
                <p>{{ reply.suggested_reply }}</p>
              </article>
            </div>
            <ElEmpty v-else description="暂无建议话术" :image-size="78" />
          </section>
        </template>
        <ElEmpty v-else description="点击左侧客服查看详情" />
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import SmartQAAPI, {
  type BossDimension,
  type BossStaffQuality,
  type BossWorkbench,
  type ImprovementSummary,
} from "@/api/module_smartqa";

const loading = ref(false);
const detailLoading = ref(false);
const keyword = ref("");
const activeDimension = ref<BossDimension["key"]>("overall");
const workbench = ref<BossWorkbench>();
const selectedStaff = ref<BossStaffQuality>();
const staffInsight = ref<ImprovementSummary>();

const dimensions = computed(() => workbench.value?.dimensions || []);
const abilityDimensions = computed(() => dimensions.value.filter((item) => item.key !== "overall"));
const currentDimensionLabel = computed(() => dimensions.value.find((item) => item.key === activeDimension.value)?.label || "综合表现");
const staffRows = computed(() => workbench.value?.staff_quality || []);

const filteredStaff = computed(() => {
  const kw = keyword.value.trim().toLowerCase();
  const list = kw
    ? staffRows.value.filter((row) => [row.staff_name, row.primary_account].some((item) => String(item || "").toLowerCase().includes(kw)))
    : staffRows.value;
  return [...list].sort((a, b) => dimensionScore(b, activeDimension.value) - dimensionScore(a, activeDimension.value));
});

const summaryCards = computed(() => {
  const rows = staffRows.value;
  const avgScore = rows.length ? (rows.reduce((sum, row) => sum + Number(row.overall_score || 0), 0) / rows.length).toFixed(1) : "0.0";
  return [
    { label: "客服数", value: rows.length, hint: "已参与质检" },
    { label: "综合均分", value: avgScore, hint: "当前样本" },
    { label: "需关注客服", value: rows.filter((row) => row.overall_score < 80).length, hint: "综合低于 80" },
    { label: "高风险会话", value: rows.reduce((sum, row) => sum + row.high_risk_count, 0), hint: "全部客服合计" },
    { label: "待跟进意向", value: rows.reduce((sum, row) => sum + row.pending_intent_count, 0), hint: "全部客服合计" },
  ];
});

watch(filteredStaff, (rows) => {
  const first = rows[0];
  if (!selectedStaff.value && first) {
    selectStaff(first);
  }
});

function dimensionScore(staff: BossStaffQuality | undefined, key: string): number {
  if (!staff) return 0;
  if (key === "overall") return Number(staff.overall_score || 0);
  return Number(staff.dimensions?.[key] ?? staff.overall_score ?? 0);
}

function dimensionLeader(key: string) {
  return [...staffRows.value].sort((a, b) => dimensionScore(b, key) - dimensionScore(a, key))[0];
}

function rankClass(index: number) {
  if (index === 0) return "gold";
  if (index === 1) return "silver";
  if (index === 2) return "bronze";
  return "";
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

async function selectStaff(staff: BossStaffQuality) {
  selectedStaff.value = staff;
  await loadStaffInsight(staff);
}

async function loadStaffInsight(staff: BossStaffQuality) {
  detailLoading.value = true;
  try {
    const res = await SmartQAAPI.improvements(20, staff.staff_id);
    staffInsight.value = res.data.data;
  } finally {
    detailLoading.value = false;
  }
}

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.bossWorkbench();
    workbench.value = res.data.data;
    const first = filteredStaff.value[0];
    if (first) {
      await selectStaff(first);
    }
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped>
.performance-page {
}

.page-head,
.head-actions,
.panel-head,
.profile {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.page-head h2,
.panel-head h3,
.profile h3 {
  margin: 0;
  color: #1f2a44;
  font-size: 20px;
  font-weight: 780;
}

.page-head p,
.panel-head p,
.profile p {
  margin: 4px 0 0;
  color: #667085;
}

.head-actions {
  align-items: center;
}

.head-actions :deep(.el-input) {
  width: 260px;
}

.dimension-strip {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
}

.dimension-card,
.summary-card,
.panel {
  border: 1px solid rgba(51, 84, 128, 0.1);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 26px rgba(29, 59, 103, 0.06);
}

.dimension-card {
  display: grid;
  gap: 4px;
  min-height: 82px;
  padding: 12px;
  color: #344054;
  text-align: left;
  cursor: pointer;
  transition: all 0.16s ease;
}

.dimension-card:hover,
.dimension-card.active {
  color: #fff;
  background: #2f80ed;
  box-shadow: 0 10px 22px rgba(47, 128, 237, 0.22);
}

.dimension-card span,
.dimension-card em {
  overflow: hidden;
  font-size: 12px;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dimension-card strong {
  overflow: hidden;
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
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

.content-grid {
  display: grid;
  grid-template-columns: minmax(680px, 1fr) 360px;
  gap: 12px;
}

.panel {
  min-width: 0;
  padding: 14px;
}

.panel-head.compact {
  align-items: center;
}

.panel-head h4,
.insight-block h4 {
  margin: 0 0 10px;
  color: #1f2a44;
  font-size: 15px;
}

.ranking-table {
  overflow: hidden;
  margin-top: 12px;
  border: 1px solid #edf1f7;
  border-radius: 8px;
}

.ranking-head,
.ranking-row {
  display: grid;
  grid-template-columns: 62px minmax(160px, 1.15fr) 100px 100px 86px 110px minmax(180px, 1fr) 86px;
  align-items: center;
  gap: 8px;
}

.ranking-head {
  height: 40px;
  padding: 0 12px;
  color: #667085;
  font-size: 12px;
  background: #f7f9fd;
}

.ranking-row {
  width: 100%;
  min-height: 54px;
  padding: 0 12px;
  border: 0;
  border-bottom: 1px solid #eef2f7;
  color: #26344d;
  text-align: left;
  background: #fff;
  cursor: pointer;
}

.ranking-row:hover,
.ranking-row.selected {
  background: #f0f7ff;
  box-shadow: inset 3px 0 0 #2f80ed;
}

.rank-badge {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  color: #53627c;
  font-weight: 800;
  background: #edf2f7;
}

.rank-badge.gold,
.rank-badge.silver,
.rank-badge.bronze {
  color: #fff;
}

.rank-badge.gold {
  background: #f5a400;
}

.rank-badge.silver {
  background: #a7b0c1;
}

.rank-badge.bronze {
  background: #e87933;
}

.staff-cell,
.profile {
  display: flex;
  align-items: center;
}

.staff-cell {
  gap: 9px;
  min-width: 0;
}

.staff-cell img,
.profile img {
  width: 34px;
  height: 34px;
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
  font-weight: 800;
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

.detail-panel {
  display: grid;
  align-content: start;
  gap: 14px;
}

.profile {
  justify-content: flex-start;
}

.profile img {
  width: 58px;
  height: 58px;
}

.profile strong {
  margin-left: auto;
  color: #14a85b;
  font-size: 34px;
}

.bar-list,
.count-grid,
.issue-list,
.reply-list {
  display: grid;
  gap: 10px;
}

.bar-row {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr) 42px;
  align-items: center;
  gap: 8px;
  color: #42526d;
  font-size: 13px;
}

.bar-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf2f7;
}

.bar-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2f80ed, #16b364);
}

.count-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.count-grid div,
.issue-list article,
.reply-list article {
  padding: 10px;
  border-radius: 7px;
  background: #f7f9fd;
}

.count-grid span,
.issue-list em {
  display: block;
  color: #667085;
  font-size: 12px;
  font-style: normal;
}

.count-grid strong {
  display: block;
  margin-top: 4px;
  color: #1f2a44;
  font-size: 22px;
}

.issue-list strong,
.reply-list strong {
  display: block;
  margin-bottom: 5px;
}

.issue-list p,
.reply-list p {
  margin: 0 0 5px;
  color: #667085;
  line-height: 1.6;
}

@media (max-width: 1180px) {
  .page-head,
  .content-grid {
    display: grid;
    grid-template-columns: 1fr;
  }

  .dimension-strip,
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
