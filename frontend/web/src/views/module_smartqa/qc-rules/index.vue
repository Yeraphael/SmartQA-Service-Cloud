<template>
  <div class="smartqa-page">
    <div class="smartqa-toolbar">
      <ElSelect v-model="ruleStatus" clearable placeholder="规则状态" class="status-select" @change="loadRules">
        <ElOption label="启用" value="active" />
        <ElOption label="停用" value="inactive" />
      </ElSelect>
      <ElButton type="primary" icon="Plus" @click="openRuleForm()">新增规则</ElButton>
      <ElButton icon="DocumentAdd" @click="openVersionDialog">发布版本</ElButton>
      <ElButton :loading="loading" icon="Refresh" @click="loadAll">刷新</ElButton>
    </div>

    <ElTabs v-model="activeTab">
      <ElTabPane label="规则" name="rules">
        <ElCard shadow="never">
          <ElTable :loading="loading" :data="rules" row-key="id" height="610">
            <ElTableColumn prop="rule_code" label="编码" min-width="150" show-overflow-tooltip />
            <ElTableColumn prop="rule_name" label="规则" min-width="160" show-overflow-tooltip />
            <ElTableColumn prop="category" label="分类" width="120" />
            <ElTableColumn prop="severity" label="等级" width="90" />
            <ElTableColumn prop="deduction_score" label="扣分" width="80" />
            <ElTableColumn prop="status" label="状态" width="90">
              <template #default="{ row }">
                <ElTag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status }}</ElTag>
              </template>
            </ElTableColumn>
            <ElTableColumn prop="judgment_standard" label="判断标准" min-width="260" show-overflow-tooltip />
            <ElTableColumn label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <ElButton link type="primary" @click="openRuleForm(row)">编辑</ElButton>
                <ElButton link type="danger" @click="removeRule(row)">删除</ElButton>
              </template>
            </ElTableColumn>
          </ElTable>
        </ElCard>
      </ElTabPane>

      <ElTabPane label="Prompt" name="prompts">
        <ElCard shadow="never">
          <div class="tab-actions">
            <ElButton type="primary" icon="Plus" @click="openPromptForm()">新增Prompt</ElButton>
          </div>
          <ElTable :loading="loading" :data="prompts" row-key="id" height="560">
            <ElTableColumn prop="prompt_version" label="版本" min-width="180" show-overflow-tooltip />
            <ElTableColumn prop="name" label="名称" min-width="160" show-overflow-tooltip />
            <ElTableColumn prop="output_schema_version" label="输出结构" width="130" />
            <ElTableColumn prop="status" label="状态" width="90" />
            <ElTableColumn prop="template_content" label="模板内容" min-width="360" show-overflow-tooltip />
            <ElTableColumn label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <ElButton link type="primary" @click="openPromptForm(row)">编辑</ElButton>
              </template>
            </ElTableColumn>
          </ElTable>
        </ElCard>
      </ElTabPane>

      <ElTabPane label="版本" name="versions">
        <ElCard shadow="never">
          <ElTable :loading="loading" :data="versions" row-key="id" height="610">
            <ElTableColumn prop="rule_version" label="规则版本" min-width="190" show-overflow-tooltip />
            <ElTableColumn prop="prompt_version" label="Prompt版本" min-width="190" show-overflow-tooltip />
            <ElTableColumn prop="status" label="状态" width="90" />
            <ElTableColumn prop="published_at" label="发布时间" min-width="170" show-overflow-tooltip />
            <ElTableColumn label="规则数" width="90">
              <template #default="{ row }">{{ row.rule_codes?.length || 0 }}</template>
            </ElTableColumn>
          </ElTable>
        </ElCard>
      </ElTabPane>
    </ElTabs>

    <ElDrawer v-model="ruleDrawerVisible" size="560px" :title="editingRule?.id ? '编辑规则' : '新增规则'">
      <ElForm label-width="88px" :model="ruleForm">
        <ElFormItem label="编码">
          <ElInput v-model="ruleForm.rule_code" :disabled="Boolean(editingRule)" />
        </ElFormItem>
        <ElFormItem label="名称">
          <ElInput v-model="ruleForm.rule_name" />
        </ElFormItem>
        <ElFormItem label="分类">
          <ElInput v-model="ruleForm.category" />
        </ElFormItem>
        <ElFormItem label="等级">
          <ElSelect v-model="ruleForm.severity">
            <ElOption label="低" value="low" />
            <ElOption label="中" value="medium" />
            <ElOption label="高" value="high" />
            <ElOption label="严重" value="critical" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="扣分">
          <ElInputNumber v-model="ruleForm.deduction_score" :min="0" :max="100" />
        </ElFormItem>
        <ElFormItem label="状态">
          <ElSelect v-model="ruleForm.status">
            <ElOption label="启用" value="active" />
            <ElOption label="停用" value="inactive" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="判断标准">
          <ElInput v-model="ruleForm.judgment_standard" type="textarea" :rows="8" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="ruleDrawerVisible = false">取消</ElButton>
        <ElButton :loading="saving" type="primary" @click="saveRule">保存</ElButton>
      </template>
    </ElDrawer>

    <ElDrawer v-model="promptDrawerVisible" size="640px" :title="editingPrompt?.id ? '编辑Prompt' : '新增Prompt'">
      <ElForm label-width="96px" :model="promptForm">
        <ElFormItem label="版本">
          <ElInput v-model="promptForm.prompt_version" :disabled="Boolean(editingPrompt)" />
        </ElFormItem>
        <ElFormItem label="名称">
          <ElInput v-model="promptForm.name" />
        </ElFormItem>
        <ElFormItem label="输出结构">
          <ElInput v-model="promptForm.output_schema_version" />
        </ElFormItem>
        <ElFormItem label="状态">
          <ElSelect v-model="promptForm.status">
            <ElOption label="启用" value="active" />
            <ElOption label="停用" value="inactive" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="模板内容">
          <ElInput v-model="promptForm.template_content" type="textarea" :rows="14" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="promptDrawerVisible = false">取消</ElButton>
        <ElButton :loading="saving" type="primary" @click="savePrompt">保存</ElButton>
      </template>
    </ElDrawer>

    <ElDialog v-model="versionDialogVisible" title="发布规则版本" width="520px">
      <ElForm label-width="96px" :model="versionForm">
        <ElFormItem label="规则版本">
          <ElInput v-model="versionForm.rule_version" />
        </ElFormItem>
        <ElFormItem label="Prompt版本">
          <ElSelect v-model="versionForm.prompt_version" filterable>
            <ElOption
              v-for="item in prompts"
              :key="item.prompt_version"
              :label="item.prompt_version"
              :value="item.prompt_version"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="规则">
          <ElSelect v-model="versionForm.rule_codes" multiple filterable>
            <ElOption v-for="item in rules" :key="item.rule_code" :label="item.rule_name" :value="item.rule_code" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="versionDialogVisible = false">取消</ElButton>
        <ElButton :loading="saving" type="primary" @click="publishVersion">发布</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import SmartQAAPI, {
  type QcPromptTemplate,
  type QcPromptTemplateForm,
  type QcRule,
  type QcRuleForm,
  type QcRuleVersion,
} from "@/api/module_smartqa";

const activeTab = ref("rules");
const loading = ref(false);
const saving = ref(false);
const ruleStatus = ref("");
const rules = ref<QcRule[]>([]);
const prompts = ref<QcPromptTemplate[]>([]);
const versions = ref<QcRuleVersion[]>([]);
const ruleDrawerVisible = ref(false);
const promptDrawerVisible = ref(false);
const versionDialogVisible = ref(false);
const editingRule = ref<QcRule>();
const editingPrompt = ref<QcPromptTemplate>();

const blankRule = (): QcRuleForm => ({
  rule_code: "",
  rule_name: "",
  category: "p0_service_quality",
  judgment_standard: "",
  deduction_score: 0,
  severity: "medium",
  status: "active",
});

const blankPrompt = (): QcPromptTemplateForm => ({
  prompt_version: "",
  name: "",
  template_content: "",
  output_schema_version: "smartqa-qc-v1",
  status: "active",
});

const ruleForm = reactive<QcRuleForm>(blankRule());
const promptForm = reactive<QcPromptTemplateForm>(blankPrompt());
const versionForm = reactive({
  rule_version: "",
  prompt_version: "",
  rule_codes: [] as string[],
});

function assign<T extends object>(target: T, source: T) {
  Object.assign(target, source);
}

async function loadRules() {
  const res = await SmartQAAPI.rules({ status: ruleStatus.value || undefined });
  rules.value = res.data.data || [];
}

async function loadPrompts() {
  const res = await SmartQAAPI.promptTemplates();
  prompts.value = res.data.data || [];
}

async function loadVersions() {
  const res = await SmartQAAPI.ruleVersions();
  versions.value = res.data.data || [];
}

async function loadAll() {
  loading.value = true;
  try {
    await Promise.all([loadRules(), loadPrompts(), loadVersions()]);
  } finally {
    loading.value = false;
  }
}

function openRuleForm(row?: QcRule) {
  editingRule.value = row;
  assign(ruleForm, row ? {
    rule_code: row.rule_code,
    rule_name: row.rule_name,
    category: row.category,
    judgment_standard: row.judgment_standard,
    deduction_score: row.deduction_score,
    severity: row.severity,
    status: row.status,
  } : blankRule());
  ruleDrawerVisible.value = true;
}

async function saveRule() {
  saving.value = true;
  try {
    if (editingRule.value) {
      await SmartQAAPI.updateRule(editingRule.value.id, ruleForm);
    } else {
      await SmartQAAPI.createRule(ruleForm);
    }
    ruleDrawerVisible.value = false;
    await loadRules();
  } finally {
    saving.value = false;
  }
}

async function removeRule(row: QcRule) {
  await ElMessageBox.confirm(`确认删除 ${row.rule_name}？`, "删除确认", { type: "warning" });
  await SmartQAAPI.deleteRule(row.id);
  ElMessage.success("已删除");
  await loadRules();
}

function openPromptForm(row?: QcPromptTemplate) {
  editingPrompt.value = row;
  assign(promptForm, row ? {
    prompt_version: row.prompt_version,
    name: row.name,
    template_content: row.template_content,
    output_schema_version: row.output_schema_version,
    status: row.status,
  } : blankPrompt());
  promptDrawerVisible.value = true;
}

async function savePrompt() {
  saving.value = true;
  try {
    if (editingPrompt.value) {
      await SmartQAAPI.updatePromptTemplate(editingPrompt.value.id, promptForm);
    } else {
      await SmartQAAPI.createPromptTemplate(promptForm);
    }
    promptDrawerVisible.value = false;
    await loadPrompts();
  } finally {
    saving.value = false;
  }
}

function openVersionDialog() {
  versionForm.rule_version = `smartqa-p0-${new Date().toISOString().slice(0, 10).replaceAll("-", "")}`;
  versionForm.prompt_version = prompts.value.find((item) => item.status === "active")?.prompt_version || prompts.value[0]?.prompt_version || "";
  versionForm.rule_codes = rules.value.filter((item) => item.status === "active").map((item) => item.rule_code);
  versionDialogVisible.value = true;
}

async function publishVersion() {
  saving.value = true;
  try {
    await SmartQAAPI.publishRuleVersion(versionForm);
    versionDialogVisible.value = false;
    await loadVersions();
  } finally {
    saving.value = false;
  }
}

onMounted(loadAll);
</script>

<style scoped>
.smartqa-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  padding: 12px;
}

.smartqa-toolbar,
.tab-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.status-select {
  width: 140px;
}

.tab-actions {
  margin-bottom: 10px;
}
</style>
