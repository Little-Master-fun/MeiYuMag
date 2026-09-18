import { ref, shallowRef, type Ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type {
  PersonalApplicationItem,
  ParchmentPageCanvas,
  VenueUsageBoard,
  VenueUsageItem,
} from '@/assets/textures/parchmentPage'
import {
  fetchPersonalApplications,
  fetchVenues,
  fetchVenueUsageRange,
} from '../api'
import type { VenueApiItem } from '../types'
import { cleanPurposeSummary, getLocalDateKey, offsetDate } from '../utils'

interface VenueBoardOptions {
  folderPage: Ref<'profile' | 'calendar'>
  getCanvas: () => ParchmentPageCanvas | null
}

export function useVenueBoards({ folderPage, getCanvas }: VenueBoardOptions) {
  const auth = useAuthStore()
  const venueOptions = ref<VenueApiItem[]>([])
  const selectedVenueId = ref<number | null>(null)
  const venueSelectorReady = ref(false)
  const personalHomeBoard = shallowRef<VenueUsageBoard | null>(null)
  const venueUsageBoard = shallowRef<VenueUsageBoard | null>(null)

  async function loadVenueUsageBoard() {
    const canvas = getCanvas()
    if (!canvas) return
    const today = new Date()
    const dateKey = getLocalDateKey(today)
    const mode = 'user-detail'
    const rangeStart = getLocalDateKey(offsetDate(today, -15))
    const rangeEnd = getLocalDateKey(offsetDate(today, 15))
    venueSelectorReady.value = false
    const loadingBoard: VenueUsageBoard = {
      mode,
      date: dateKey,
      rangeStart,
      rangeEnd,
      state: 'loading',
      venues: [],
    }
    venueUsageBoard.value = loadingBoard
    if (folderPage.value === 'calendar') canvas.updateUsageBoard(loadingBoard)

    try {
      const data = await fetchVenueUsageRange(rangeStart, rangeEnd)
      const usageItems: VenueUsageItem[] = data.venues.map(({ venue, events }) => ({
        id: venue.id,
        name: venue.name,
        events: events
          .sort(
            (first, second) => new Date(first.start_at).getTime()
              - new Date(second.start_at).getTime(),
          )
          .map((event) => ({
            id: event.id,
            organization: event.borrow_organization
              || event.organization
              || event.title
              || '场地申请',
            purpose: cleanPurposeSummary(event.purpose_summary),
            startAt: event.start_at,
            endAt: event.end_at,
            status: event.status,
          })),
      }))

      venueUsageBoard.value = {
        mode,
        date: dateKey,
        rangeStart: data.start_date,
        rangeEnd: data.end_date,
        state: 'ready',
        venues: usageItems,
      }
      if (folderPage.value === 'calendar') canvas.updateUsageBoard(venueUsageBoard.value)
      venueOptions.value = data.venues.map(({ venue }) => venue)
      selectedVenueId.value = venueOptions.value[0]?.id ?? null
      venueSelectorReady.value = venueOptions.value.length > 0
    } catch (error) {
      console.error('[场地使用看板] 数据加载失败', error)
      venueUsageBoard.value = {
        mode,
        date: dateKey,
        rangeStart,
        rangeEnd,
        state: 'error',
        venues: [],
        error: '请确认本地后端服务已启动',
      }
      if (folderPage.value === 'calendar') canvas.updateUsageBoard(venueUsageBoard.value)
      venueOptions.value = []
      selectedVenueId.value = null
      venueSelectorReady.value = false
    }
  }

  async function loadPersonalHome() {
    const canvas = getCanvas()
    if (!canvas) return
    const dateKey = getLocalDateKey(new Date())
    personalHomeBoard.value = {
      mode: 'profile',
      date: dateKey,
      state: 'loading',
      venues: [],
      applications: [],
    }
    if (folderPage.value === 'profile') canvas.updateUsageBoard(personalHomeBoard.value)

    try {
      if (!auth.user) await auth.fetchMe()
      const [applicationsData, venuesData] = await Promise.all([
        fetchPersonalApplications(),
        fetchVenues(),
      ])
      const user = auth.user
      if (!user) throw new Error('当前用户信息不可用')
      const venueNames = new Map(venuesData.map((venue) => [venue.id, venue.name]))
      const applications: PersonalApplicationItem[] = applicationsData.map((application) => ({
        id: application.id,
        applicationType: application.application_type,
        venueId: application.venue_id,
        venueName: application.venue_id
          ? venueNames.get(application.venue_id) ?? `场地 #${application.venue_id}`
          : application.application_type === 'key_borrow'
            ? '钥匙借用'
            : '综合申请',
        purpose: cleanPurposeSummary(application.purpose_summary),
        status: application.status,
        startAt: application.start_at,
        endAt: application.end_at,
        reviewReason: application.review_reason,
        createdAt: application.created_at,
      }))
      personalHomeBoard.value = {
        mode: 'profile',
        date: dateKey,
        state: 'ready',
        venues: [],
        profile: {
          email: user.email,
          organization: user.department || '未填写所属组织',
          role: user.role,
          verified: user.is_sdu_verified,
          applicationAllowed: user.is_application_allowed || user.is_sdu_verified,
        },
        applications,
      }
    } catch (error) {
      console.error('[个人首页] 数据加载失败', error)
      personalHomeBoard.value = {
        mode: 'profile',
        date: dateKey,
        state: 'error',
        venues: [],
        applications: [],
        error: '请确认本地后端服务已启动并重新登录',
      }
    }
    if (folderPage.value === 'profile') canvas.updateUsageBoard(personalHomeBoard.value)
  }

  function switchFolderPage(page: 'profile' | 'calendar') {
    if (folderPage.value === page) return
    folderPage.value = page
    const canvas = getCanvas()
    if (page === 'profile') {
      if (personalHomeBoard.value) canvas?.transitionUsageBoard(personalHomeBoard.value)
      else void loadPersonalHome()
      return
    }
    if (venueUsageBoard.value) canvas?.transitionUsageBoard(venueUsageBoard.value)
    else void loadVenueUsageBoard()
  }

  function selectUsageVenue(venueId: number) {
    if (venueId === selectedVenueId.value) return
    selectedVenueId.value = venueId
    getCanvas()?.selectVenue(venueId)
  }

  function resetVenueBoards() {
    venueOptions.value = []
    selectedVenueId.value = null
    venueSelectorReady.value = false
    personalHomeBoard.value = null
    venueUsageBoard.value = null
  }

  return {
    loadPersonalHome,
    loadVenueUsageBoard,
    personalHomeBoard,
    resetVenueBoards,
    selectedVenueId,
    selectUsageVenue,
    switchFolderPage,
    venueOptions,
    venueSelectorReady,
    venueUsageBoard,
  }
}
