<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { VenueUsageBoard } from '@/assets/textures/parchmentPage'
import { applicationStatusLabels } from '../workflow'
import { calendarDays } from '../mobileLayout'

const props = defineProps<{
  page: 'profile' | 'calendar'
  profileBoard: VenueUsageBoard | null
  calendarBoard: VenueUsageBoard | null
  selectedVenueId: number | null
}>()
const emit = defineEmits<{
  page: [page: 'profile' | 'calendar']
  venue: [id: number]
  detail: [id: number]
  apply: [date?: string, venueId?: number]
  reload: []
}>()
const selectedDate = ref('')
const scroll = ref<HTMLElement | null>(null)
const board = computed(() => (props.page === 'profile' ? props.profileBoard : props.calendarBoard))
const venue = computed(
  () =>
    props.calendarBoard?.venues.find((item) => item.id === props.selectedVenueId) ||
    props.calendarBoard?.venues[0],
)
const days = computed(() =>
  calendarDays(
    props.calendarBoard?.rangeStart || '',
    props.calendarBoard?.rangeEnd || '',
    venue.value?.events || [],
  ),
)
const selectedDay = computed(() => days.value.find((day) => day.key === selectedDate.value))
const applications = computed(() => props.profileBoard?.applications || [])
const current = computed(() =>
  applications.value.filter(
    (item) => !['completed', 'cancelled', 'rejected'].includes(item.status),
  ),
)
const history = computed(() =>
  applications.value.filter((item) => ['completed', 'cancelled', 'rejected'].includes(item.status)),
)
const pending = computed(() =>
  current.value.filter((item) =>
    ['ai_rejected', 'pending_signed_files', 'supplement_required'].includes(item.status),
  ),
)
const statusLabel = (status: string) => applicationStatusLabels[status] || status
const eventLabel = (status: string) =>
  ({
    confirmed: '已确认',
    reserved: '已预约',
    pre_reserved: '预占用',
    supplement_required: '待补充',
    pending_admin_pre_review: '待人工初审',
  })[status] || '审核中'
const time = (date: string) =>
  new Date(date).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
const chooseVenue = (id: number) => {
  selectedDate.value = ''
  emit('venue', id)
}
watch(
  () => props.page,
  () => {
    if (scroll.value) scroll.value.scrollTop = 0
  },
)
</script>

<template>
  <section class="mobile-folder" aria-label="手机文件夹" @pointerdown.stop @click.stop @wheel.stop>
    <header class="mobile-folder-heading">
      <small>MEIYU · PERSONAL DESK</small>
      <nav aria-label="文件夹页面">
        <button :aria-pressed="page === 'profile'" @click="emit('page', 'profile')">个人首页</button
        ><button :aria-pressed="page === 'calendar'" @click="emit('page', 'calendar')">
          场地日历
        </button>
      </nav>
    </header>
    <div ref="scroll" class="mobile-paper-scroll">
      <Transition name="paper-content" mode="out-in">
        <div :key="page">
          <h1>{{ page === 'profile' ? '我的首页' : venue?.name || '场地日历' }}</h1>
          <p class="paper-subtitle">
            {{ page === 'profile' ? '个人信息、申请进度与历史记录' : '前后半月的场地使用记录' }}
          </p>
          <p v-if="!board || board.state === 'loading'" class="paper-empty" role="status">
            正在翻阅记录…
          </p>
          <div v-else-if="board.state === 'error'" class="paper-empty" role="alert">
            <p>暂时没能取得记录，请检查网络后重试。</p>
            <button @click="emit('reload')">重新翻阅</button>
          </div>
          <template v-else-if="page === 'profile'">
            <section class="mobile-profile">
              <span class="profile-monogram" aria-hidden="true">{{
                profileBoard?.profile?.email.charAt(0).toUpperCase()
              }}</span>
              <div>
                <strong>{{ profileBoard?.profile?.email }}</strong>
                <p>{{ profileBoard?.profile?.organization }}</p>
                <small>{{
                  profileBoard?.profile?.verified ? '手机身份已认证' : '尚未完成手机认证'
                }}</small>
              </div>
            </section>
            <div class="mobile-stats">
              <span
                ><strong>{{ applications.length }}</strong
                >全部申请</span
              ><span
                ><strong>{{ current.length }}</strong
                >进行中</span
              ><span
                ><strong>{{ pending.length }}</strong
                >待处理</span
              >
            </div>
            <h2>当前申请</h2>
            <p v-if="!current.length" class="paper-empty">
              还没有进行中的申请，从下方书签寄出第一份申请吧。
            </p>
            <button
              v-for="item in current"
              :key="item.id"
              class="mobile-application"
              @click="emit('detail', item.id)"
            >
              <span
                ><strong>{{ item.venueName }}</strong
                ><small>{{ item.purpose || '场地使用申请' }}</small
                ><small v-if="item.reviewReason" class="reason">{{
                  item.reviewReason
                }}</small></span
              ><em
                :class="{
                  attention: [
                    'ai_rejected',
                    'pending_signed_files',
                    'supplement_required',
                  ].includes(item.status),
                }"
                >{{ statusLabel(item.status) }} ›</em
              >
            </button>
            <h2>历史申请</h2>
            <p v-if="!history.length" class="paper-empty">完成、取消或未通过的申请会保存在这里。</p>
            <button
              v-for="item in history"
              :key="item.id"
              class="mobile-application"
              @click="emit('detail', item.id)"
            >
              <span
                ><strong>{{ item.venueName }}</strong
                ><small>{{ item.createdAt.slice(0, 10) }}</small></span
              ><em>{{ statusLabel(item.status) }} ›</em>
            </button>
          </template>
          <template v-else>
            <nav class="mobile-venue-tabs" aria-label="选择场地">
              <button
                v-for="item in calendarBoard?.venues"
                :key="item.id"
                :aria-pressed="venue?.id === item.id"
                @click="chooseVenue(item.id)"
              >
                {{ item.name }}
              </button>
            </nav>
            <Transition name="paper-content" mode="out-in"
              ><div :key="venue?.id">
                <p class="calendar-range">
                  {{ calendarBoard?.rangeStart }} — {{ calendarBoard?.rangeEnd }}
                </p>
                <div class="calendar-legend">
                  <span class="confirmed">已确认</span><span class="pre_reserved">预占用</span
                  ><span class="pending_admin_pre_review">审核中</span
                  ><span class="supplement_required">待补充</span>
                </div>
                <div class="mobile-calendar" aria-label="场地使用日历">
                  <span
                    v-for="day in ['日', '一', '二', '三', '四', '五', '六']"
                    :key="day"
                    class="weekday"
                    >{{ day }}</span
                  ><span v-for="i in days[0]?.weekday || 0" :key="`pad${i}`" />
                  <button
                    v-for="day in days"
                    :key="day.key"
                    :aria-label="`${day.key} ${day.events.length ? `${day.events.length}项占用` : '空闲'}${day.key === calendarBoard?.date ? ' 今天' : ''}`"
                    :aria-pressed="selectedDate === day.key"
                    :class="{
                      today: day.key === calendarBoard?.date,
                      past: day.key < (calendarBoard?.date || ''),
                    }"
                    @click="selectedDate = day.key"
                  >
                    <span
                      >{{ day.day === 1 || day.key === days[0]?.key ? `${day.month}/` : ''
                      }}{{ day.day }}</span
                    ><i
                      v-for="event in day.events.slice(0, 3)"
                      :key="event.id"
                      :class="event.status"
                    /><small v-if="day.events.length > 3">+{{ day.events.length - 3 }}</small>
                  </button>
                </div>
                <section v-if="selectedDay" class="day-note" aria-live="polite">
                  <h2>
                    {{ selectedDay.key
                    }}<small>{{ selectedDay.events.length ? '占用时段' : '暂无占用' }}</small>
                  </h2>
                  <p v-for="event in selectedDay.events" :key="event.id">
                    <i :class="event.status" /><span
                      >{{ time(event.startAt) }} — {{ time(event.endAt)
                      }}<small>{{ eventLabel(event.status) }}</small></span
                    >
                  </p>
                  <button
                    v-if="selectedDay.key > (calendarBoard?.date || '') && venue"
                    class="day-apply"
                    @click="emit('apply', selectedDay.key, venue.id)"
                  >
                    {{ selectedDay.events.length ? '申请该日空闲时段' : '申请这一天' }} ↗
                  </button>
                  <p v-else class="past-note">历史与今日记录仅供查看，请选择之后的日期发起申请。</p>
                  <small v-if="selectedDay.key > (calendarBoard?.date || '')"
                    >以申请文件中的具体时间为准，提交时仍会检查占用冲突。</small
                  >
                </section>
                <p v-else class="paper-empty">轻点日期查看时段，再选择空闲时间申请。</p>
              </div></Transition
            >
          </template>
        </div>
      </Transition>
    </div>
    <footer>
      <span>把申请寄进森林信箱</span
      ><button @click="emit('apply')"><span aria-hidden="true">✉</span> 场地申请 ↗</button>
    </footer>
  </section>
</template>

<style scoped>
.mobile-folder {
  position: absolute;
  inset: calc(76px + env(safe-area-inset-top)) 14px calc(16px + env(safe-area-inset-bottom));
  z-index: 6;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid #c4ad76;
  border-radius: 5px 8px 16px 4px;
  padding: 20px 18px 0;
  color: #614a2c;
  background: linear-gradient(110deg, #eee1b8, #e2cb91);
  box-shadow:
    0 10px 30px #33251140,
    inset 5px 0 #fbefd330;
  font-family: 'Songti SC', 'STSong', serif;
}
button {
  font: inherit;
  touch-action: manipulation;
  cursor: pointer;
}
button:focus-visible {
  outline: 2px solid #61754f;
  outline-offset: 2px;
}
.mobile-folder-heading {
  flex-shrink: 0;
  border-bottom: 1px solid #b39b6866;
  padding-bottom: 12px;
}
.mobile-folder-heading > small {
  font:
    10px Georgia,
    serif;
  letter-spacing: 0.12em;
  color: #9c8658;
}
.mobile-folder-heading nav {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}
.mobile-folder-heading button {
  min-height: 44px;
  flex: 1;
  color: #82704a;
  border: 1px solid #b8aa7b55;
  border-radius: 3px 12px 4px 10px;
  background: #f6ecd244;
  font-size: 14px;
}
.mobile-folder-heading button[aria-pressed='true'] {
  background: #718056;
  color: #f5ecd1;
}
.mobile-paper-scroll {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  touch-action: pan-y;
  padding: 18px 2px 28px;
  scrollbar-width: thin;
  scrollbar-color: #b2a177 transparent;
}
h1 {
  font-size: 29px;
  font-weight: 500;
  margin: 0 0 6px;
}
h2 {
  font-size: 19px;
  font-weight: 500;
  margin: 24px 0 12px;
}
.paper-subtitle,
.paper-empty {
  font-size: 13px;
  color: #927c51;
  line-height: 1.8;
}
.paper-subtitle {
  margin: 0 0 20px;
}
.paper-empty {
  padding: 14px 0;
}
.paper-empty button,
.day-apply {
  border: 0;
  border-bottom: 1px dashed #6c795b;
  min-height: 44px;
  background: none;
  color: #596e4d;
}
.mobile-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 12px;
  background: #f7efd04d;
  border: 1px solid #bdad7f66;
  border-radius: 14px 4px 12px 5px;
}
.mobile-profile > div {
  min-width: 0;
}
.mobile-profile strong {
  font-size: 15px;
  overflow-wrap: anywhere;
  font-weight: 500;
}
.mobile-profile p {
  font-size: 13px;
  margin: 5px 0;
}
.mobile-profile small {
  color: #7d845b;
  font-size: 11px;
}
.profile-monogram {
  display: grid;
  place-items: center;
  flex: 0 0 38px;
  height: 42px;
  color: #f2e9cc;
  background: #788459;
  border-radius: 50%;
  font:
    22px Georgia,
    serif;
}
.mobile-stats {
  display: flex;
  gap: 7px;
  margin: 18px 0;
}
.mobile-stats > span {
  flex: 1;
  padding: 12px 3px;
  text-align: center;
  font-size: 11px;
  color: #9a8152;
  border: 1px solid #bdad7f66;
  background: #f7efd04d;
  border-radius: 9px;
}
.mobile-stats strong {
  display: block;
  font:
    27px Georgia,
    serif;
  color: #6b512d;
  margin-bottom: 5px;
}
.mobile-application {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: space-between;
  width: 100%;
  padding: 14px 12px;
  margin-bottom: 10px;
  text-align: left;
  color: #614a2c;
  border: 1px solid #bdad7f66;
  background: #f7efd04d;
  border-radius: 10px 4px 10px 4px;
}
.mobile-application > span {
  min-width: 0;
}
.mobile-application strong {
  font-size: 16px;
  font-weight: 500;
}
.mobile-application small {
  display: block;
  font-size: 12px;
  color: #9a8152;
  line-height: 1.6;
  margin-top: 5px;
  overflow-wrap: anywhere;
}
.mobile-application em {
  flex-shrink: 0;
  max-width: 90px;
  font:
    12px/1.6 'Songti SC',
    serif;
  color: #72765c;
}
.mobile-application em.attention,
.mobile-application small.reason {
  color: #a56547;
}
.mobile-venue-tabs {
  display: flex;
  gap: 7px;
  overflow-x: auto;
  padding-bottom: 10px;
  touch-action: pan-x;
  scrollbar-width: thin;
  scrollbar-color: #a8af87 transparent;
}
.mobile-venue-tabs button {
  flex-shrink: 0;
  min-height: 44px;
  padding: 9px 13px;
  border: 1px solid #aab291;
  border-radius: 3px 12px 12px 3px;
  background: #f3edd4;
  color: #667153;
  font-size: 13px;
}
.mobile-venue-tabs button[aria-pressed='true'] {
  background: #60765a;
  color: #f7efd8;
}
.calendar-range {
  font-size: 11px;
  color: #927d54;
  margin: 12px 0;
}
.calendar-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 13px;
  font-size: 10px;
  color: #8f805c;
  margin-bottom: 12px;
}
.calendar-legend span::before {
  content: '';
  display: inline-block;
  width: 9px;
  height: 5px;
  border-radius: 3px;
  background: var(--occupancy, #85847b);
  margin-right: 4px;
}
.confirmed,
.reserved {
  --occupancy: #647b58;
}
.pre_reserved {
  --occupancy: #b68c40;
}
.pending_admin_pre_review {
  --occupancy: #89867c;
}
.supplement_required {
  --occupancy: #ac6d4b;
}
.mobile-calendar {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
}
.weekday {
  text-align: center;
  font-size: 12px;
  color: #9c875b;
  padding: 8px 0;
}
.mobile-calendar button {
  min-width: 0;
  height: 58px;
  padding: 7px 4px;
  border: 1px solid #bba77755;
  border-radius: 8px;
  background: #f7edd035;
  color: #68522d;
  font:
    13px Georgia,
    serif;
  text-align: left;
  position: relative;
}
.mobile-calendar button.past {
  color: #9e8e6b;
  background: #d6c69520;
}
.mobile-calendar button.today {
  border-color: #9eab78;
}
.mobile-calendar button[aria-pressed='true'] {
  background: #fcf3d480;
  border-color: #69805c;
  box-shadow: inset 0 0 0 1px #69805c;
}
.mobile-calendar i {
  display: block;
  height: 4px;
  margin-top: 4px;
  border-radius: 3px;
  background: var(--occupancy, #85847b);
}
.mobile-calendar button > small {
  position: absolute;
  bottom: 3px;
  right: 3px;
  font-size: 8px;
}
.day-note {
  padding-top: 4px;
}
.day-note h2 {
  font-size: 18px;
}
.day-note h2 small {
  font-size: 12px;
  margin-left: 12px;
  color: #8d815c;
}
.day-note > p {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #786443;
  font-size: 14px;
}
.day-note i {
  width: 9px;
  height: 7px;
  background: var(--occupancy, #85847b);
  border-radius: 4px;
}
.day-note p small {
  margin-left: 14px;
  font-size: 11px;
  color: #91805d;
}
.day-note > small {
  display: block;
  margin-top: 10px;
  color: #93805c;
  font-size: 11px;
  line-height: 1.8;
}
.day-note p.past-note {
  font-size: 12px;
  line-height: 1.8;
}
footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 7px;
  padding: 12px 0;
  border-top: 1px solid #bba77766;
}
footer > span {
  color: #9a8458;
  font-size: 11px;
}
footer button {
  min-height: 44px;
  padding: 9px 13px;
  border: 1px solid #b4a174;
  border-radius: 3px 14px 14px 3px;
  color: #745838;
  background: #f1e7c7;
  box-shadow: 0 3px 9px #88704420;
}
footer button > span {
  color: #a4674c;
}
.paper-content-enter-active,
.paper-content-leave-active {
  transition: opacity 0.18s;
}
.paper-content-enter-from,
.paper-content-leave-to {
  opacity: 0;
}
@media (max-height: 540px) {
  .mobile-folder {
    inset: 62px 16px 12px;
  }
  .mobile-folder-heading {
    display: flex;
    align-items: center;
    gap: 20px;
    padding-bottom: 6px;
  }
  .mobile-folder-heading nav {
    flex: 1;
    margin: 0;
  }
  .mobile-paper-scroll {
    padding-top: 12px;
  }
  footer {
    padding: 5px 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
  }
}
</style>
