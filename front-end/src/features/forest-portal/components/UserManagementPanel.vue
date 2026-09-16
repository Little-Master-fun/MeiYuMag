<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import axios from 'axios'
import type { User } from '@/stores/auth'
import { getSubmissionErrorMessage } from '../submission'

const users = ref<User[]>([])
const loading = ref(false), saving = ref(false), error = ref(''), notice = ref('')
const search = ref(''), roleFilter = ref('')
const editing = ref<User | null>(null)
const assignmentNote = ref<HTMLElement | null>(null)
const selectedRole = ref<'user' | 'secondary_admin'>('user')
const allowed = ref(false)
const roleNames = { user: '普通用户', secondary_admin: '二级管理员', admin: '一级管理员' }
const visible = computed(() => users.value.filter(user =>
  (!roleFilter.value || user.role === roleFilter.value) &&
  `${user.email} ${user.department ?? ''}`.toLowerCase().includes(search.value.trim().toLowerCase()),
))
async function load() {
  loading.value = true; error.value = ''
  try { users.value = (await axios.get<User[]>('/api/v1/admin/users')).data }
  catch (e) { error.value = getSubmissionErrorMessage(e) }
  finally { loading.value = false }
}
async function edit(user: User) {
  editing.value = user
  selectedRole.value = user.role === 'secondary_admin' ? 'secondary_admin' : 'user'
  allowed.value = user.is_application_allowed
  notice.value = ''; error.value = ''
  await nextTick()
  assignmentNote.value?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  assignmentNote.value?.focus({ preventScroll: true })
}
async function save() {
  if (!editing.value || saving.value) return
  saving.value = true; error.value = ''
  try {
    const { data } = await axios.patch<User>(`/api/v1/admin/users/${editing.value.id}`, {
      ...(editing.value.role !== 'admin' ? {role: selectedRole.value} : {}),
      is_application_allowed: allowed.value,
    })
    users.value = users.value.map(user => user.id === data.id ? data : user)
    editing.value = null; notice.value = '身份与申请权限已更新。'
  } catch (e) { error.value = getSubmissionErrorMessage(e) }
  finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <section class="user-register" aria-label="用户管理">
    <p class="register-caption">名册 · {{ users.length }} 位用户</p>
    <p class="register-hint">二级管理员保留普通用户功能，仅增加美育场地签章审核与再次签章提交权限，不能查看用户名册。没有可用二级管理员时，由一级管理员处理。</p>
    <p v-if="error" role="alert" class="register-error">{{ error }} <button @click="load" :disabled="loading || saving">重试</button></p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <div class="register-filter">
      <label>查找用户<input v-model="search" type="search" placeholder="邮箱或所属组织" /></label>
      <label>身份<select v-model="roleFilter"><option value="">全部身份</option><option v-for="(label, role) in roleNames" :key="role" :value="role">{{ label }}</option></select></label>
    </div>
    <p v-if="loading">正在翻开名册…</p>
    <p v-else-if="!visible.length">没有符合条件的用户。</p>
    <article v-for="user in visible" :key="user.id" class="user-leaf">
      <div><strong>{{ user.email }}</strong><small>{{ user.department || '未填写组织' }}</small></div>
      <span class="role-stamp">{{ roleNames[user.role] }}</span>
      <p>{{ user.is_sdu_verified ? '身份已认证' : '未认证' }} · {{ user.is_application_allowed || user.is_sdu_verified ? '可申请' : '未开通申请' }}</p>
      <button :disabled="saving" @click="edit(user)">管理身份与权限 ↗</button>
    </article>
    <section v-if="editing" ref="assignmentNote" class="assignment-note" role="region" aria-label="身份指派" tabindex="-1">
      <h3>身份指派</h3><p>{{ editing.email }}</p>
      <fieldset :disabled="saving">
        <label v-if="editing.role !== 'admin'">用户身份<select v-model="selectedRole" aria-label="用户身份"><option value="user">普通用户</option><option value="secondary_admin">二级管理员 · 签章协办</option></select></label>
        <p v-else>一级管理员身份保持不变。</p>
        <label class="permission-check"><input v-model="allowed" type="checkbox" /> 开通申请权限</label>
        <small>已完成身份认证的用户仍可按现有规则申请，此选项不是封禁账号。</small>
        <p v-if="editing.role === 'secondary_admin' && selectedRole === 'user'">取消指派后，未完成的签章任务将转交其他二级管理员；没有其他人时交回一级管理员。</p>
        <div><button @click="save">确认保存</button><button @click="editing = null">暂不修改</button></div>
      </fieldset>
    </section>
  </section>
</template>

<style scoped>
.user-register { position: relative; }
.register-caption { font-size: 22px; margin-bottom: 10px; }
.register-hint, small { color: #877956; line-height: 1.7; }
.register-filter { display: flex; gap: 16px; margin: 24px 0; flex-wrap: wrap; }
label { display: grid; gap: 8px; flex: 1; }
input, select, button { font: inherit; color: inherit; border: 1px solid #a3956c80; border-radius: 3px 10px 4px 3px; padding: 9px 12px; background: #fffae744; min-width: 0; box-sizing: border-box; }
button { cursor: pointer; }
button:hover:not(:disabled) { background: #d9ddc0; }
button:disabled { opacity: .5; cursor: wait; }
button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid #617658; outline-offset: 3px; }
.user-leaf { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; padding: 18px 0; border-top: 1px solid #b8a87c66; }
.user-leaf strong, .assignment-note p { overflow-wrap: anywhere; }
.user-leaf small { display: block; margin-top: 6px; }
.user-leaf p { margin: 0; font-size: 13px; align-self: center; }
.role-stamp { color: #5e7359; font-size: 13px; align-self: start; }
.assignment-note { position: sticky; bottom: 0; border: 1px solid #a7976b; padding: 20px; border-radius: 3px 14px 4px 3px; background: #eee3bd; box-shadow: 0 -6px 22px #4f482524; max-height: 60dvh; overflow-y: auto; }
fieldset { padding: 0; border: 0; min-width: 0; display: grid; gap: 16px; }
fieldset div { display: flex; gap: 12px; }
.permission-check { display: flex; align-items: center; }
.register-error { color: #9e4f38; }
@media (max-width: 520px) { .user-leaf { grid-template-columns: minmax(0, 1fr); } .register-filter { flex-direction: column; } .assignment-note { padding: 14px; } }
</style>
