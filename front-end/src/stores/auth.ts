import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'

export interface User {
  id: number
  email: string
  role: 'user' | 'admin'
  department: string | null
  is_sdu_verified: boolean
  is_application_allowed: boolean
}

interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  user: User
}

const API = '/api/v1'

async function getRequestErrorMessage(requestError: any, fallback: string): Promise<string> {
  let responseData = requestError.response?.data
  if (responseData instanceof Blob) {
    try {
      responseData = JSON.parse(await responseData.text())
    } catch {
      return requestError.message || fallback
    }
  }

  const detail = responseData?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (typeof item?.msg === 'string' ? item.msg : ''))
      .filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return requestError.message || fallback
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isLoggedIn = computed(() => Boolean(token.value && user.value))
  const isAdmin = computed(() => user.value?.role === 'admin')

  axios.interceptors.request.use((config) => {
    if (token.value) config.headers.Authorization = `Bearer ${token.value}`
    return config
  })

  function saveAuth(data: AuthResponse) {
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
  }

  async function login(account: string, password: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const { data } = await axios.post<AuthResponse>(`${API}/auth/login`, {
        account,
        password,
      })
      saveAuth(data)
      return true
    } catch (requestError: any) {
      error.value = await getRequestErrorMessage(requestError, '登录失败')
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(
    email: string,
    password: string,
    organization: string,
    mobile: string,
    smsCode: string,
  ): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const { data } = await axios.post<AuthResponse>(
        `${API}/auth/register`,
        {
          email,
          password,
          organization,
          mobile,
          sms_code: smsCode,
        },
        { withCredentials: true },
      )
      saveAuth(data)
      return true
    } catch (requestError: any) {
      error.value = await getRequestErrorMessage(requestError, '注册失败')
      return false
    } finally {
      loading.value = false
    }
  }

  async function requestRegistrationCaptcha(): Promise<Blob | null> {
    error.value = null

    try {
      const { data } = await axios.post<Blob>(`${API}/auth/register/code`, null, {
        responseType: 'blob',
        withCredentials: true,
      })
      return data
    } catch (requestError: any) {
      error.value = await getRequestErrorMessage(requestError, '图片验证码加载失败')
      return null
    }
  }

  async function sendRegistrationSms(
    mobile: string,
    imageCode: string,
  ): Promise<boolean> {
    error.value = null

    try {
      await axios.post(
        `${API}/auth/register/sms`,
        {
          mobile,
          image_code: imageCode,
        },
        { withCredentials: true },
      )
      return true
    } catch (requestError: any) {
      error.value = await getRequestErrorMessage(requestError, '短信验证码发送失败')
      return false
    }
  }

  async function fetchMe(): Promise<boolean> {
    if (!token.value) return false
    loading.value = true
    error.value = null

    try {
      const { data } = await axios.get<User>(`${API}/auth/me`)
      user.value = data
      return true
    } catch (requestError: any) {
      error.value = await getRequestErrorMessage(requestError, '令牌验证失败')
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    error.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  if (token.value) void fetchMe()

  return {
    token,
    refreshToken,
    user,
    loading,
    error,
    isLoggedIn,
    isAdmin,
    login,
    register,
    requestRegistrationCaptcha,
    sendRegistrationSms,
    fetchMe,
    logout,
  }
})
