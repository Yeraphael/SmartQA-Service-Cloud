<template>
  <div class="smartqa-page">
    <div class="smartqa-toolbar">
      <ElSwitch v-model="boundOnly" active-text="仅已绑定" @change="loadData" />
      <ElButton :loading="seeding" type="primary" icon="UserFilled" @click="seedUsers">
        初始化客服账号
      </ElButton>
      <ElButton :loading="loading" icon="Refresh" @click="loadData">刷新</ElButton>
    </div>

    <ElCard shadow="never">
      <ElTable :loading="loading" :data="rows" row-key="staff_id" height="650">
        <ElTableColumn prop="staff_id" label="ID" width="80" />
        <ElTableColumn prop="staff_name" label="客服" width="120" show-overflow-tooltip />
        <ElTableColumn prop="primary_account" label="千牛账号" min-width="180" show-overflow-tooltip />
        <ElTableColumn prop="username" label="登录账号" min-width="160" show-overflow-tooltip />
        <ElTableColumn prop="nickname" label="系统昵称" width="140" show-overflow-tooltip />
        <ElTableColumn prop="status" label="客服状态" width="110" />
        <ElTableColumn prop="user_status" label="账号状态" width="110">
          <template #default="{ row }">
            <ElTag v-if="row.sys_user_id" :type="row.user_status === 0 ? 'success' : 'warning'">
              {{ row.user_status === 0 ? "启用" : "停用" }}
            </ElTag>
            <ElTag v-else type="info">未绑定</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <ElButton v-if="!row.sys_user_id" link type="primary" @click="ensureUser(row)">创建账号</ElButton>
            <template v-else>
              <ElButton link type="primary" @click="resetPassword(row)">重置密码</ElButton>
              <ElButton link :type="row.user_status === 0 ? 'warning' : 'success'" @click="toggleStatus(row)">
                {{ row.user_status === 0 ? "停用" : "启用" }}
              </ElButton>
            </template>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, ref } from "vue";
import SmartQAAPI, { type StaffUser } from "@/api/module_smartqa";

const loading = ref(false);
const seeding = ref(false);
const boundOnly = ref(false);
const rows = ref<StaffUser[]>([]);

async function loadData() {
  loading.value = true;
  try {
    const res = await SmartQAAPI.staffUsers(boundOnly.value);
    rows.value = res.data.data || [];
  } finally {
    loading.value = false;
  }
}

async function seedUsers() {
  seeding.value = true;
  try {
    await SmartQAAPI.seedStaffUsers(false);
    await loadData();
  } finally {
    seeding.value = false;
  }
}

async function ensureUser(row: StaffUser) {
  await SmartQAAPI.ensureStaffUser(row.staff_id);
  ElMessage.success("账号已创建");
  await loadData();
}

async function resetPassword(row: StaffUser) {
  await ElMessageBox.confirm(`确认重置 ${row.staff_name} 的登录密码？`, "重置确认", { type: "warning" });
  await SmartQAAPI.resetStaffPassword(row.staff_id);
  ElMessage.success("密码已重置");
}

async function toggleStatus(row: StaffUser) {
  const nextStatus = row.user_status === 0 ? 1 : 0;
  await SmartQAAPI.setStaffUserStatus(row.staff_id, nextStatus);
  await loadData();
}

onMounted(loadData);
</script>

<style scoped>
.smartqa-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  padding: 12px;
}

.smartqa-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
