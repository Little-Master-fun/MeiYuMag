<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  personalStatusStyles,
  type PersonalApplicationItem,
  type VenueUsageBoard,
} from '@/assets/textures/parchmentPage'
import { calendarDays } from '../mobileLayout'

const props = defineProps<{
  page: 'profile' | 'calendar'
  personal: VenueUsageBoard | null
  calendar: VenueUsageBoard | null
  selectedVenueId: number | null
}>()
const emit = defineEmits<{
  switch: [page: 'profile' | 'calendar']
  detail: [application: PersonalApplicationItem]
  venue: [id: number]
  apply: [venueName?: string]
  keyApply: []
  retry: []
}>()
const scroller = ref<HTMLElement | null>(null)
const selectedDay = ref('')
const historyOpen = ref(false)
const applications = computed(() => props.personal?.applications ?? [])
const historical = (item: PersonalApplicationItem) =>
  ['completed', 'cancelled', 'rejected'].includes(item.status)
const active = computed(() => applications.value.filter((item) => !historical(item)))
const history = computed(() => applications.value.filter(historical))
const needsAction = (item: PersonalApplicationItem) =>
  ['ai_rejected', 'supplement_required', 'pending_signed_files'].includes(item.status)
const pending = computed(() => applications.value.filter(needsAction).length)
const board = computed(() => (props.page === 'profile' ? props.personal : props.calendar))
const venue = computed(
  () =>
    props.calendar?.venues.find((item) => item.id === props.selectedVenueId) ??
    props.calendar?.venues[0],
)
const days = computed(() =>
  props.calendar
    ? calendarDays(
        props.calendar.rangeStart || props.calendar.date,
        props.calendar.rangeEnd || props.calendar.date,
        venue.value?.events ?? [],
      )
    : [],
)
const leading = computed(() => ((days.value[0]?.weekday ?? 1) + 6) % 7)
const dayEvents = computed(
  () => days.value.find((day) => day.key === selectedDay.value)?.events ?? [],
)
const status = (item: PersonalApplicationItem) =>
  personalStatusStyles[item.status]?.label ?? '处理中'
const action = (item: PersonalApplicationItem) =>
  item.status === 'ai_rejected'
    ? '重新提交'
    : item.status === 'pending_signed_files'
      ? '提交签章材料'
      : '补交材料'
const date = (value: string | null) =>
  value ? new Date(value).toLocaleDateString('zh-CN') : '日期待确认'
const time = (value: string) =>
  new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
const eventColor = (value: string) =>
  ({
    confirmed: '#60745f',
    reserved: '#60745f',
    pre_reserved: '#ad8248',
    supplement_required: '#9a6152',
  })[value] ?? '#737583'
watch(
  () => [props.page, props.selectedVenueId],
  () => {
    selectedDay.value = ''
    scroller.value?.scrollTo({ top: 0 })
  },
)
</script>

<template>
  <section
    class="mobile-folder-reader"
    aria-label="文件夹内容"
    @pointerdown.stop
    @pointermove.stop
    @pointerup.stop
    @click.stop
    @wheel.stop
  >
    <nav class="page-tabs" aria-label="文件夹页面">
      <button :aria-pressed="page === 'profile'" @click="emit('switch', 'profile')">
        个人首页
      </button>
      <button :aria-pressed="page === 'calendar'" @click="emit('switch', 'calendar')">
        场地日历
      </button>
    </nav>
    <div ref="scroller" class="reader-scroll" tabindex="0" aria-label="上下滑动阅读文件夹">
      <Transition name="page-ink" mode="out-in">
        <div :key="page" class="reader-page">
          <header>
            <small>MEIYU · {{ page === 'profile' ? 'PERSONAL DESK' : 'VENUE CALENDAR' }}</small>
            <h1>{{ page === 'profile' ? '我的首页' : '场地日历' }}</h1>
          </header>
          <p v-if="!board || board.state === 'loading'" role="status">正在整理档案…</p>
          <div v-else-if="board.state === 'error'" role="alert">
            <p>暂时无法读取档案，请稍后再试。</p>
            <button class="text-action" @click="emit('retry')">重新读取 ↻</button>
          </div>
          <template v-else-if="page === 'profile'">
            <section class="identity" aria-label="个人信息">
              <strong>{{ personal?.profile?.email }}</strong>
              <span>{{ personal?.profile?.organization }}</span>
              <small
                >{{ personal?.profile?.verified ? '身份已认证' : '身份待认证' }} ·
                {{ personal?.profile?.applicationAllowed ? '可申请场地' : '申请权限待开通' }}</small
              >
            </section>
            <dl class="counts">
              <div>
                <dt>全部申请</dt>
                <dd>{{ applications.length }}</dd>
              </div>
              <div>
                <dt>进行中</dt>
                <dd>{{ active.length }}</dd>
              </div>
              <div>
                <dt>待处理</dt>
                <dd>{{ pending }}</dd>
              </div>
            </dl>
            <h2>
              当前申请 <small>{{ active.length }} 份</small>
            </h2>
            <p v-if="!active.length" class="empty">
              还没有进行中的申请。<br />点击纸页下方的「场地申请」开始。
            </p>
            <button
              v-for="item in active"
              :key="item.id"
              class="application-leaf"
              @click="emit('detail', item)"
            >
              <strong>{{ item.venueName }}</strong>
              <span class="status" :style="{ color: personalStatusStyles[item.status]?.text }">{{
                status(item)
              }}</span>
              <span class="summary"
                >{{ date(item.startAt || item.createdAt) }} ·
                {{ item.purpose || '场地使用申请' }}</span
              >
              <span v-if="item.reviewReason && needsAction(item)" class="reason">{{
                item.reviewReason
              }}</span>
              <span class="leaf-action" :class="{ required: needsAction(item) }"
                >{{ needsAction(item) ? action(item) : '查看申请' }} ↗</span
              >
            </button>
            <button
              class="history-toggle"
              :aria-expanded="historyOpen"
              @click="historyOpen = !historyOpen"
            >
              历史申请 <small>{{ history.length }} 份</small
              ><span>{{ historyOpen ? '−' : '+' }}</span>
            </button>
            <template v-if="historyOpen"
              ><p v-if="!history.length" class="empty">完成或取消的申请会保存在这里。</p>
              <button
                v-for="item in history"
                :key="item.id"
                class="application-leaf"
                @click="emit('detail', item)"
              >
                <strong>{{ item.venueName }}</strong
                ><span class="status">{{ status(item) }}</span
                ><span class="summary">{{ date(item.startAt || item.createdAt) }}</span
                ><span class="leaf-action">查看记录 ↗</span>
              </button></template
            >
          </template>
          <template v-else>
            <label class="venue-picker"
              >选择场地<select
                :value="venue?.id"
                @change="emit('venue', Number(($event.target as HTMLSelectElement).value))"
              >
                <option v-for="item in calendar?.venues" :key="item.id" :value="item.id">
                  {{ item.name }}
                </option>
              </select></label
            >
            <p v-if="!venue" class="empty">暂无可展示的场地。</p>
            <template v-else>
              <p class="calendar-caption">
                {{ days[0]?.key.slice(5).replace('-', '/') }} —
                {{ days.at(-1)?.key.slice(5).replace('-', '/') }} <small>点击日期查看</small>
              </p>
              <div class="legend">
                <span><i style="background: #60745f" />已确认</span
                ><span><i style="background: #ad8248" />预占用</span
                ><span><i style="background: #737583" />审核中</span
                ><span><i style="background: #9a6152" />待补充</span>
              </div>
              <div class="calendar-grid">
                <span
                  v-for="day in ['一', '二', '三', '四', '五', '六', '日']"
                  :key="day"
                  class="weekday"
                  >{{ day }}</span
                ><span v-for="n in leading" :key="`blank-${n}`" />
                <button
                  v-for="day in days"
                  :key="day.key"
                  :class="{ today: day.key === calendar?.date, chosen: day.key === selectedDay }"
                  :disabled="!day.events.length && day.key <= (calendar?.date ?? '')"
                  :aria-label="`${day.key}，${day.events.length ? '有占用，查看时段' : '空闲，可申请'}`"
                  @click="selectedDay = day.key"
                >
                  <span>{{ day.day === 1 ? `${day.month}/1` : day.day }}</span
                  ><span class="day-bars"
                    ><i
                      v-for="event in day.events.slice(0, 3)"
                      :key="event.id"
                      :style="{ background: eventColor(event.status) }"
                  /></span>
                </button>
              </div>
              <section v-if="selectedDay" class="day-detail" aria-live="polite">
                <strong>{{ selectedDay }} {{ dayEvents.length ? '占用时段' : '暂无占用' }}</strong>
                <p v-for="event in dayEvents" :key="event.id">
                  {{ time(event.startAt) }}–{{ time(event.endAt) }}<br />{{ event.organization }}
                </p>
                <button
                  v-if="selectedDay > (calendar?.date ?? '')"
                  class="text-action"
                  @click="emit('apply', venue?.name)"
                >
                  准备申请材料 ↗
                </button>
              </section>
            </template>
          </template>
        </div>
      </Transition>
    </div>
    <footer class="paper-bookmarks">
      <button @click="emit('keyApply')">钥匙申请 <span>↗</span></button
      ><button @click="emit('apply', venue?.name)">场地申请 <span>↗</span></button>
    </footer>
  </section>
</template>

<style scoped>
.mobile-folder-reader {
  position: absolute;
  z-index: 5;
  display: flex;
  flex-direction: column;
  min-height: 0;
  color: #503e29;
  font:
    16px/1.55 'Songti SC',
    'STSong',
    serif;
  pointer-events: auto;
  touch-action: pan-y;
}
button,
select {
  font: inherit;
  color: inherit;
}
button {
  cursor: pointer;
}
button:focus-visible,
select:focus-visible {
  outline: 2px solid #60745f;
  outline-offset: 2px;
}
.page-tabs {
  display: flex;
  gap: 6px;
  padding-bottom: 10px;
  flex-shrink: 0;
}
.page-tabs button {
  flex: 1;
  min-height: 44px;
  border: 1px solid #8d815052;
  border-radius: 9px 9px 3px 3px;
  background: #faf2d849;
}
.page-tabs button[aria-pressed='true'] {
  background: #667554;
  color: #fff4d6;
  border-color: #667554;
}
.reader-scroll {
  overflow: auto;
  min-height: 0;
  flex: 1;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: #9c9064 transparent;
  touch-action: pan-y;
  padding: 0 3px 12px;
}
.reader-page {
  padding-bottom: 12px;
}
header {
  padding: 0 0 8px;
}
header small {
  font:
    10px/1.4 Georgia,
    serif;
  letter-spacing: 1px;
  color: #796a4d;
}
h1 {
  font-size: 26px;
  line-height: 1.3;
  margin: 2px 0 0;
}
h2 {
  font-size: 19px;
  margin: 10px 0 8px;
}
h2 small,
.history-toggle small {
  font-size: 13px;
  font-weight: 400;
  color: #776c4f;
  margin-left: 6px;
}
.identity {
  display: flex;
  flex-direction: column;
  gap: 1px;
  border-top: 1px solid #8c78484d;
  border-bottom: 1px solid #8c78484d;
  padding: 8px 0;
  overflow-wrap: anywhere;
}
.identity strong {
  font-size: 16px;
}
.identity span {
  font-size: 15px;
}
.identity small {
  font-size: 13px;
  color: #576347;
}
.counts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 10px 0;
  gap: 6px;
}
.counts div {
  display: flex;
  flex-direction: column-reverse;
  align-items: center;
  background: #f7efd54a;
  border-radius: 9px;
  padding: 6px 2px;
}
.counts dt {
  font-size: 13px;
}
.counts dd {
  margin: 0;
  font:
    600 25px/1.3 Georgia,
    serif;
}
.application-leaf {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 5px;
  width: 100%;
  text-align: left;
  border: 1px solid #9c885647;
  border-radius: 10px 3px 10px 3px;
  background: #f7efd55c;
  padding: 12px;
  margin-bottom: 10px;
  overflow-wrap: anywhere;
}
.application-leaf strong {
  font-size: 18px;
}
.status {
  font-size: 14px;
}
.summary {
  font-size: 14px;
  color: #726346;
}
.reason {
  font-size: 14px;
  color: #875440;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.leaf-action {
  justify-self: end;
  font-size: 15px;
  color: #516545;
  padding-top: 4px;
}
.leaf-action.required {
  color: #8b4e36;
  font-weight: 600;
}
.history-toggle {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 48px;
  border: 0;
  border-top: 1px solid #8c78484d;
  background: none;
  text-align: left;
  font-size: 19px;
}
.history-toggle > span {
  margin-left: auto;
}
.empty {
  font-size: 15px;
  color: #75674e;
}
.paper-bookmarks {
  display: flex;
  gap: 10px;
  border-top: 1px solid #8c784852;
  padding-top: 10px;
  flex-shrink: 0;
}
.paper-bookmarks button {
  flex: 1;
  min-height: 44px;
  text-align: left;
  padding: 8px 12px;
  border: 1px solid #97845666;
  border-radius: 3px 13px 13px 3px;
  background: #efe4be;
  box-shadow: 0 2px 2px #66533716;
  font-weight: 600;
}
.paper-bookmarks button:last-child {
  background: #667554;
  color: #fff3d4;
}
.paper-bookmarks span {
  float: right;
}
.venue-picker {
  display: flex;
  flex-direction: column;
  font-size: 13px;
  color: #73654c;
  gap: 5px;
}
.venue-picker select {
  font-size: 16px;
  min-height: 44px;
  width: 100%;
  border: 1px solid #8e7d535f;
  border-radius: 4px;
  background: #f4e8c1;
  padding: 6px;
  color: #503e29;
}
.calendar-caption {
  font-size: 16px;
  margin: 14px 0 6px;
}
.calendar-caption small {
  font-size: 12px;
  float: right;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 9px;
  font-size: 11px;
  margin-bottom: 10px;
}
.legend i {
  display: inline-block;
  width: 9px;
  height: 4px;
  border-radius: 2px;
  margin-right: 3px;
}
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 3px;
}
.weekday {
  text-align: center;
  font-size: 13px;
  padding-bottom: 5px;
}
.calendar-grid button {
  min-width: 0;
  min-height: 48px;
  border: 1px solid #ac986145;
  border-radius: 5px;
  background: #f8efd449;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  font-size: 16px;
  padding: 3px 0;
}
.calendar-grid button:disabled {
  color: #8b7c59;
  background: transparent;
}
.calendar-grid button.today {
  border-color: #677451;
}
.calendar-grid button.chosen {
  background: #667554;
  color: #fff5d9;
}
.day-bars {
  display: flex;
  gap: 2px;
  margin-top: 4px;
  height: 4px;
  width: 75%;
}
.day-bars i {
  height: 4px;
  flex: 1;
  border-radius: 2px;
}
.day-detail {
  font-size: 15px;
  margin: 14px 0;
  padding: 12px 0;
  border-top: 1px solid #8c78484d;
}
.day-detail p {
  margin: 7px 0;
}
.text-action {
  border: 0;
  background: none;
  min-height: 44px;
  padding: 6px 0;
  color: #566b48;
}
.page-ink-enter-active,
.page-ink-leave-active {
  transition: opacity 0.18s;
}
.page-ink-enter-from,
.page-ink-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .page-ink-enter-active,
  .page-ink-leave-active {
    transition: none;
  }
}
</style>
