<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import axios from 'axios'
import { ChevronLeft, ChevronRight, Building2, Calendar, Circle } from 'lucide-vue-next'

const venues = ref<any[]>([])
const selectedVenueId = ref<number | null>(null)
const calendar = ref<Record<string, any[]>>({})
const loading = ref(false)

const today = new Date()
const currentYear  = ref(today.getFullYear())
const currentMonth = ref(today.getMonth() + 1)

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/v1/venues')
    venues.value = data
    if (data.length > 0) {
      selectedVenueId.value = data[0].id
    }
  } catch { /* ignore */ }
})

watch([selectedVenueId, currentYear, currentMonth], loadCalendar, { immediate: false })
watch(selectedVenueId, (v) => { if (v) loadCalendar() })

async function loadCalendar() {
  if (!selectedVenueId.value) return
  loading.value = true
  try {
    const { data } = await axios.get(
      `/api/v1/venues/${selectedVenueId.value}/calendar`,
      { params: { year: currentYear.value, month: currentMonth.value } }
    )
    calendar.value = data
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

// Calendar grid computation
const monthName = computed(() => {
  return new Date(currentYear.value, currentMonth.value - 1).toLocaleString('zh-CN', { year: 'numeric', month: 'long' })
})

const days = computed(() => {
  const firstDay = new Date(currentYear.value, currentMonth.value - 1, 1).getDay()
  const daysInMonth = new Date(currentYear.value, currentMonth.value, 0).getDate()
  const grid: (number | null)[] = []

  for (let i = 0; i < firstDay; i++) grid.push(null)
  for (let d = 1; d <= daysInMonth; d++) grid.push(d)

  // Pad to full weeks
  while (grid.length % 7 !== 0) grid.push(null)

  return grid
})

function prevMonth() {
  if (currentMonth.value === 1) { currentMonth.value = 12; currentYear.value-- }
  else currentMonth.value--
}

function nextMonth() {
  if (currentMonth.value === 12) { currentMonth.value = 1; currentYear.value++ }
  else currentMonth.value++
}

function getDayKey(d: number) {
  return `${currentYear.value}-${String(currentMonth.value).padStart(2,'0')}-${String(d).padStart(2,'0')}`
}

function getDayReservations(d: number) {
  return calendar.value[getDayKey(d)] || []
}

function isToday(d: number) {
  return d === today.getDate() && currentMonth.value === today.getMonth() + 1 && currentYear.value === today.getFullYear()
}

const statusDot: Record<string, string> = {
  pre_reserved:          'dot-amber',
  confirmed:             'dot-teal',
  supplement_required:   'dot-orange',
  pending_admin_pre_review: 'dot-blue',
}

const weekdays = ['日', '一', '二', '三', '四', '五', '六']

const selectedVenue = computed(() => venues.value.find(v => v.id === selectedVenueId.value))
</script>

<template>
  <AppLayout>
    <div class="calendar-page">

      <!-- Header -->
      <div class="page-header">
        <div>
          <h1>场地日历</h1>
          <p>查看各场地的预约使用情况</p>
        </div>
      </div>

      <!-- Venue selector -->
      <div class="venue-tabs">
        <button
          v-for="v in venues"
          :key="v.id"
          class="venue-tab"
          :class="{ active: selectedVenueId === v.id }"
          @click="selectedVenueId = v.id"
        >
          <Building2 :size="15" />
          {{ v.name }}
        </button>
      </div>

      <div v-if="venues.length === 0" class="empty-venues">
        <Building2 :size="32" class="opacity-30" />
        <p>暂无场地数据</p>
      </div>

      <div v-else class="calendar-section">
        <!-- Month navigation -->
        <div class="month-nav">
          <button class="nav-btn" @click="prevMonth">
            <ChevronLeft :size="18" />
          </button>
          <h2>{{ monthName }}</h2>
          <button class="nav-btn" @click="nextMonth">
            <ChevronRight :size="18" />
          </button>
        </div>

        <!-- Loading overlay -->
        <div v-if="loading" class="cal-loading">
          <div class="loading-spinner" />
        </div>

        <div v-else>
          <!-- Weekday headers -->
          <div class="weekdays">
            <div v-for="w in weekdays" :key="w" class="weekday">{{ w }}</div>
          </div>

          <!-- Day grid -->
          <div class="day-grid">
            <div
              v-for="(d, i) in days"
              :key="i"
              class="day-cell"
              :class="{
                empty: !d,
                today: d && isToday(d),
                'has-events': d && getDayReservations(d).length > 0,
              }"
            >
              <span v-if="d" class="day-num">{{ d }}</span>
              <div v-if="d" class="day-dots">
                <span
                  v-for="(r, ri) in getDayReservations(d).slice(0, 3)"
                  :key="ri"
                  class="event-dot"
                  :class="statusDot[r.status] ?? 'dot-teal'"
                  :title="r.organization"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Legend -->
        <div class="legend">
          <div class="legend-item">
            <span class="event-dot dot-amber" />
            <span>预约待确认</span>
          </div>
          <div class="legend-item">
            <span class="event-dot dot-teal" />
            <span>已确认</span>
          </div>
          <div class="legend-item">
            <span class="event-dot dot-blue" />
            <span>审核中</span>
          </div>
          <div class="legend-item">
            <span class="event-dot dot-orange" />
            <span>需补充</span>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.calendar-page { display: flex; flex-direction: column; gap: 20px; }

.page-header h1 {
  margin: 0 0 4px;
  font-size: 22px; font-weight: 800; color: #e8f5f0;
  animation: float-up 0.4s ease both;
}
.page-header p {
  margin: 0;
  font-size: 13px; color: rgba(232,245,240,0.5);
  animation: float-up 0.4s ease both 0.04s;
}

/* Venue tabs */
.venue-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  animation: float-up 0.4s ease both 0.08s;
}

.venue-tab {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 18px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  color: rgba(232,245,240,0.6);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.venue-tab:hover { background: rgba(255,255,255,0.08); }
.venue-tab.active {
  background: rgba(61,217,172,0.12);
  border-color: rgba(61,217,172,0.35);
  color: #3DD9AC;
}

/* Calendar section */
.calendar-section {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 24px;
  animation: float-up 0.4s ease both 0.12s;
  position: relative;
}

.month-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-bottom: 20px;
}

.month-nav h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #e8f5f0;
  min-width: 160px;
  text-align: center;
}

.nav-btn {
  width: 34px; height: 34px;
  border-radius: 9px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  color: rgba(232,245,240,0.6);
  display: grid; place-items: center;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.nav-btn:hover { background: rgba(255,255,255,0.12); color: #e8f5f0; }

/* Calendar loading */
.cal-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
}

.loading-spinner {
  width: 36px; height: 36px;
  border-radius: 50%;
  border: 2.5px solid rgba(61,217,172,0.2);
  border-top-color: #3DD9AC;
  animation: spin-slow 0.8s linear infinite;
}

/* Weekdays */
.weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  margin-bottom: 4px;
}

.weekday {
  text-align: center;
  padding: 8px 0;
  font-size: 12px;
  font-weight: 600;
  color: rgba(232,245,240,0.35);
  text-transform: uppercase;
}

/* Day grid */
.day-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.day-cell {
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 4px 4px;
  border-radius: 10px;
  border: 1px solid transparent;
  transition: background 0.15s, border-color 0.15s;
  min-height: 64px;
  gap: 4px;
}

.day-cell:not(.empty):hover {
  background: rgba(255,255,255,0.05);
  border-color: rgba(255,255,255,0.1);
}

.day-cell.today {
  background: rgba(61,217,172,0.1);
  border-color: rgba(61,217,172,0.35);
}

.day-cell.has-events {
  background: rgba(255,255,255,0.03);
}

.day-num {
  font-size: 14px;
  font-weight: 600;
  color: rgba(232,245,240,0.7);
  line-height: 1;
}

.day-cell.today .day-num {
  color: #3DD9AC;
}

.day-dots {
  display: flex;
  gap: 3px;
  flex-wrap: wrap;
  justify-content: center;
}

.event-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-teal   { background: #3DD9AC; }
.dot-amber  { background: #F7CA75; }
.dot-blue   { background: #60a5fa; }
.dot-orange { background: #fb923c; }

/* Legend */
.legend {
  display: flex;
  gap: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.07);
  margin-top: 16px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(232,245,240,0.5);
}

.empty-venues {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 60px; color: rgba(232,245,240,0.4);
}

.empty-venues p { margin: 0; font-size: 14px; }
</style>
