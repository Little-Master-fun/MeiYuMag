<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import { useNotificationsStore } from '@/stores/notifications'
import axios from 'axios'
import {
  Search, Shield, UserCheck, UserX, ChevronDown,
  Loader2, Users, X, CheckCircle, Lock
} from 'lucide-vue-next'

const notify = useNotificationsStore()
const users  = ref<any[]>([])
const loading = ref(true)
const searchText = ref('')
const filterRole = ref('')
const editModal = ref(false)
const selectedUser = ref<any>(null)
const editForm = ref({ role: '', can_apply: false })
const saving = ref(false)

onMounted(async () => { await loadUsers() })

async function loadUsers() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/v1/admin/users')
    users.value = data
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  return users.value.filter(u => {
    const search = !searchText.value || u.email.includes(searchText.value) || (u.organization ?? '').includes(searchText.value)
    const role   = !filterRole.value || u.role === filterRole.value
    return search && role
  })
})

function openEdit(user: any) {
  selectedUser.value = user
  editForm.value = { role: user.role, can_apply: user.can_apply }
  editModal.value = true
}

async function saveUser() {
  if (!selectedUser.value) return
  saving.value = true
  try {
    await axios.patch(`/api/v1/admin/users/${selectedUser.value.id}`, editForm.value)
    notify.success('用户更新成功')
    editModal.value = false
    await loadUsers()
  } catch (e: any) {
    notify.error('更新失败', e.response?.data?.detail)
  } finally {
    saving.value = false
  }
}

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
}

const roleOptions = [
  { value: '',      label: '全部角色' },
  { value: 'user',  label: '普通用户' },
  { value: 'admin', label: '管理员' },
]

const userCount  = computed(() => users.value.filter(u => u.role === 'user').length)
const adminCount = computed(() => users.value.filter(u => u.role === 'admin').length)
const canApplyCount = computed(() => users.value.filter(u => u.can_apply).length)
</script>

<template>
  <AppLayout>
    <div class="admin-users">

      <!-- Header -->
      <div class="page-header">
        <div>
          <h1>用户管理</h1>
          <p>共 <span class="accent">{{ users.length }}</span> 位注册用户</p>
        </div>
      </div>

      <!-- Stats row -->
      <div class="stats-row">
        <div class="stat-mini stat-blue">
          <Users :size="18" />
          <div>
            <span class="stat-val">{{ userCount }}</span>
            <span class="stat-lbl">普通用户</span>
          </div>
        </div>
        <div class="stat-mini stat-purple">
          <Shield :size="18" />
          <div>
            <span class="stat-val">{{ adminCount }}</span>
            <span class="stat-lbl">管理员</span>
          </div>
        </div>
        <div class="stat-mini stat-teal">
          <UserCheck :size="18" />
          <div>
            <span class="stat-val">{{ canApplyCount }}</span>
            <span class="stat-lbl">有申请权限</span>
          </div>
        </div>
      </div>

      <!-- Filter bar -->
      <div class="filter-bar">
        <div class="search-wrap">
          <Search :size="15" class="search-icon" />
          <input v-model="searchText" placeholder="搜索邮箱、组织名称..." class="search-input" />
        </div>
        <select v-model="filterRole" class="filter-select">
          <option v-for="o in roleOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </div>

      <!-- Table -->
      <div class="table-wrap">
        <div class="table-header">
          <span>用户信息</span>
          <span>角色</span>
          <span>申请权限</span>
          <span>注册时间</span>
          <span>操作</span>
        </div>

        <div v-if="loading" class="skeleton-list">
          <div v-for="i in 5" :key="i" class="skeleton-row-full">
            <div class="skeleton-line w-1/3" />
            <div class="skeleton-line w-1/5" />
            <div class="skeleton-line w-1/5" />
            <div class="skeleton-line w-1/6" />
          </div>
        </div>

        <TransitionGroup v-else name="row-list" tag="div">
          <div
            v-for="user in filtered"
            :key="user.id"
            class="table-row"
          >
            <!-- User info -->
            <div class="row-info">
              <div class="user-avatar">{{ user.email[0].toUpperCase() }}</div>
              <div>
                <p class="row-email">{{ user.email }}</p>
                <p class="row-org">{{ user.organization || '未设置组织' }}</p>
              </div>
            </div>

            <!-- Role -->
            <div>
              <span class="role-badge" :class="user.role === 'admin' ? 'role-admin' : 'role-user'">
                <component :is="user.role === 'admin' ? Shield : Users" :size="11" />
                {{ user.role === 'admin' ? '管理员' : '普通用户' }}
              </span>
            </div>

            <!-- Can apply -->
            <div>
              <span class="apply-badge" :class="user.can_apply ? 'apply-yes' : 'apply-no'">
                <component :is="user.can_apply ? CheckCircle : Lock" :size="11" />
                {{ user.can_apply ? '有权限' : '无权限' }}
              </span>
            </div>

            <!-- Date -->
            <div class="row-date">{{ formatDate(user.created_at) }}</div>

            <!-- Actions -->
            <button class="edit-btn" @click="openEdit(user)">编辑</button>
          </div>
        </TransitionGroup>

        <div v-if="!loading && filtered.length === 0" class="empty-state">
          <Users :size="28" class="opacity-30" />
          <p>没有匹配的用户</p>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="editModal" class="modal-overlay" @click.self="editModal = false">
          <div class="modal">
            <div class="modal-head">
              <div>
                <h3>编辑用户</h3>
                <p class="modal-sub">{{ selectedUser?.email }}</p>
              </div>
              <button class="modal-close" @click="editModal = false"><X :size="18" /></button>
            </div>

            <div class="modal-body">
              <div class="field">
                <label class="field-label">用户角色</label>
                <div class="role-options">
                  <button
                    v-for="r in [{ value: 'user', label: '普通用户' }, { value: 'admin', label: '管理员' }]"
                    :key="r.value"
                    class="role-opt"
                    :class="{ selected: editForm.role === r.value }"
                    @click="editForm.role = r.value"
                  >
                    {{ r.label }}
                  </button>
                </div>
              </div>

              <div class="field">
                <label class="field-label">申请权限</label>
                <button
                  class="toggle-btn"
                  :class="{ 'toggle-on': editForm.can_apply }"
                  @click="editForm.can_apply = !editForm.can_apply"
                >
                  <div class="toggle-thumb" />
                </button>
                <span class="toggle-label">{{ editForm.can_apply ? '允许提交申请' : '不允许提交申请' }}</span>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-cancel" @click="editModal = false">取消</button>
              <button class="btn-save" :disabled="saving" @click="saveUser">
                <Loader2 v-if="saving" :size="15" class="animate-spin" />
                <span v-else>保存更改</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </AppLayout>
</template>

<style scoped>
.admin-users { display: flex; flex-direction: column; gap: 20px; }

.page-header h1 { margin: 0 0 4px; font-size: 22px; font-weight: 800; color: #e8f5f0; animation: float-up 0.4s ease both; }
.page-header p  { margin: 0; font-size: 13px; color: rgba(232,245,240,0.5); }
.accent { color: #3DD9AC; font-weight: 700; }

/* Stats row */
.stats-row {
  display: flex; gap: 12px; flex-wrap: wrap;
  animation: float-up 0.4s ease both 0.05s;
}

.stat-mini {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 18px; border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  min-width: 140px;
}

.stat-blue   { background: rgba(96,165,250,0.08);  border-color: rgba(96,165,250,0.15);  color: #60a5fa; }
.stat-purple { background: rgba(167,139,250,0.08); border-color: rgba(167,139,250,0.15); color: #a78bfa; }
.stat-teal   { background: rgba(61,217,172,0.08);  border-color: rgba(61,217,172,0.15);  color: #3DD9AC; }

.stat-mini div { display: flex; flex-direction: column; gap: 1px; }
.stat-val { font-size: 22px; font-weight: 800; color: #e8f5f0; }
.stat-lbl { font-size: 11px; font-weight: 600; opacity: 0.7; }

/* Filter bar */
.filter-bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 12px 16px;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px;
  animation: float-up 0.4s ease both 0.08s;
}
.search-wrap { flex: 1; min-width: 200px; position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 11px; color: rgba(232,245,240,0.35); }
.search-input {
  width: 100%; padding: 9px 12px 9px 34px;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px; color: #e8f5f0; font-size: 13px; transition: border-color 0.2s;
}
.search-input::placeholder { color: rgba(232,245,240,0.3); }
.search-input:focus { outline: none; border-color: rgba(61,217,172,0.4); }
.filter-select {
  padding: 8px 12px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px; color: rgba(232,245,240,0.8); font-size: 13px; cursor: pointer;
}
.filter-select:focus { outline: none; }
.filter-select option { background: #0d1f1c; }

/* Table */
.table-wrap {
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; overflow: hidden;
  animation: float-up 0.4s ease both 0.1s;
}
.table-header {
  display: grid; grid-template-columns: 1fr 130px 120px 130px 80px;
  padding: 11px 18px;
  background: rgba(255,255,255,0.03); border-bottom: 1px solid rgba(255,255,255,0.07);
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: rgba(232,245,240,0.35);
}
.table-row {
  display: grid; grid-template-columns: 1fr 130px 120px 130px 80px;
  align-items: center; padding: 13px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 13px; color: rgba(232,245,240,0.7);
  transition: background 0.18s;
}
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: rgba(255,255,255,0.04); }

.row-info { display: flex; align-items: center; gap: 10px; }
.user-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, rgba(61,217,172,0.4), rgba(247,202,117,0.3));
  display: grid; place-items: center;
  font-size: 13px; font-weight: 700; color: #e8f5f0; flex-shrink: 0;
}
.row-email { margin: 0 0 1px; font-size: 13px; font-weight: 600; color: rgba(232,245,240,0.85); }
.row-org   { margin: 0; font-size: 11px; color: rgba(232,245,240,0.4); }
.row-date  { font-size: 12px; color: rgba(232,245,240,0.4); }

.role-badge, .apply-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 99px;
}
.role-admin  { background: rgba(167,139,250,0.12); color: #a78bfa; border: 1px solid rgba(167,139,250,0.2); }
.role-user   { background: rgba(96,165,250,0.12);  color: #60a5fa; border: 1px solid rgba(96,165,250,0.2); }
.apply-yes   { background: rgba(61,217,172,0.12);  color: #3DD9AC; border: 1px solid rgba(61,217,172,0.2); }
.apply-no    { background: rgba(148,163,184,0.1);  color: #94a3b8; border: 1px solid rgba(148,163,184,0.15); }

.edit-btn {
  padding: 6px 14px; background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1); border-radius: 7px;
  color: rgba(232,245,240,0.65); font-size: 12px; font-weight: 600; cursor: pointer;
  transition: all 0.2s;
}
.edit-btn:hover { background: rgba(61,217,172,0.12); border-color: rgba(61,217,172,0.25); color: #3DD9AC; }

/* Skeleton */
.skeleton-list { padding: 8px 0; }
.skeleton-row-full { display: flex; align-items: center; gap: 16px; padding: 14px 18px; border-bottom: 1px solid rgba(255,255,255,0.04); }
.skeleton-line { height: 13px; border-radius: 6px; background-image: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.04) 75%); background-size: 200% 100%; animation: shimmer 1.5s ease infinite; }
.w-1\/3 { width: 33%; } .w-1\/5 { width: 20%; } .w-1\/6 { width: 16%; }

/* Empty */
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 40px; color: rgba(232,245,240,0.4); font-size: 13px; }

/* Row transitions */
.row-list-enter-active { transition: all 0.3s ease; }
.row-list-leave-active { transition: all 0.2s ease; }
.row-list-enter-from   { opacity: 0; transform: translateY(8px); }
.row-list-leave-to     { opacity: 0; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; padding: 20px;
}
.modal {
  width: min(440px, 100%); background: #0d1f1c;
  border: 1px solid rgba(255,255,255,0.12); border-radius: 18px; overflow: hidden;
  box-shadow: 0 30px 80px rgba(0,0,0,0.5);
  animation: bounce-in 0.3s ease both;
}
.modal-head {
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 18px 22px; border-bottom: 1px solid rgba(255,255,255,0.08);
}
.modal-head h3 { margin: 0 0 3px; font-size: 16px; font-weight: 700; color: #e8f5f0; }
.modal-sub { margin: 0; font-size: 12px; color: rgba(232,245,240,0.45); }
.modal-close { background: transparent; border: 0; color: rgba(232,245,240,0.5); cursor: pointer; padding: 4px; border-radius: 6px; }
.modal-close:hover { color: #e8f5f0; }

.modal-body { padding: 20px 22px; display: flex; flex-direction: column; gap: 20px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 13px; font-weight: 600; color: rgba(232,245,240,0.65); }

.role-options { display: flex; gap: 8px; }
.role-opt {
  flex: 1; padding: 10px; border-radius: 9px;
  background: rgba(255,255,255,0.04); border: 1.5px solid rgba(255,255,255,0.1);
  color: rgba(232,245,240,0.6); font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;
}
.role-opt.selected { background: rgba(61,217,172,0.15); border-color: rgba(61,217,172,0.45); color: #3DD9AC; }
.role-opt:hover:not(.selected) { background: rgba(255,255,255,0.07); }

/* Toggle */
.field { flex-direction: row; align-items: center; }
.field .field-label { flex: none; margin-right: auto; }

.toggle-btn {
  width: 44px; height: 24px; border-radius: 12px; border: 0;
  background: rgba(255,255,255,0.1); cursor: pointer;
  position: relative; transition: background 0.25s;
  flex-shrink: 0;
}
.toggle-btn.toggle-on { background: #3DD9AC; }
.toggle-thumb {
  position: absolute; top: 3px; left: 3px;
  width: 18px; height: 18px; border-radius: 50%;
  background: #fff; transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.toggle-btn.toggle-on .toggle-thumb { transform: translateX(20px); }
.toggle-label { font-size: 13px; color: rgba(232,245,240,0.6); margin-left: 8px; }

.modal-footer {
  display: flex; justify-content: flex-end; gap: 10px;
  padding: 16px 22px; border-top: 1px solid rgba(255,255,255,0.07);
}
.btn-cancel {
  padding: 10px 20px; background: transparent; border: 1px solid rgba(255,255,255,0.12);
  border-radius: 9px; color: rgba(232,245,240,0.6); font-size: 13px; font-weight: 600; cursor: pointer;
}
.btn-cancel:hover { background: rgba(255,255,255,0.06); }
.btn-save {
  padding: 10px 24px; background: linear-gradient(90deg, #3DD9AC, #5FCBB8); border: 0;
  border-radius: 9px; color: #060e0c; font-size: 13px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; gap: 6px; transition: opacity 0.2s;
}
.btn-save:disabled { opacity: 0.5; pointer-events: none; }
.btn-save:hover { transform: translateY(-1px); }

@media (max-width: 900px) {
  .table-header,
  .table-row { grid-template-columns: 1fr 120px 80px; }
  .table-header span:nth-child(3),
  .table-row > div:nth-child(3),
  .table-header span:nth-child(4),
  .table-row .row-date { display: none; }
}
</style>
