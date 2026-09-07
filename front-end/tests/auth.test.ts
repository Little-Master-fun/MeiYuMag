import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '../src/stores/auth.ts'

const user = {id: 1, email: 'test@invalid.test', role: 'user', department: '测试', is_sdu_verified: true, is_application_allowed: true}
const response = (config: InternalAxiosRequestConfig, data: unknown, status = 200) => ({config, data, status, statusText: 'OK', headers: {}})
function setup() {
  const cache = new Map<string, string>()
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: {
    getItem: (key: string) => cache.get(key) ?? null,
    setItem: (key: string, value: string) => cache.set(key, value),
    removeItem: (key: string) => cache.delete(key),
  }})
  axios.interceptors.request.clear(); axios.interceptors.response.clear()
  setActivePinia(createPinia())
  return useAuthStore()
}

test('parallel expired requests share one refresh and retry with the new token', async () => {
  const auth = setup(), original = axios.defaults.adapter
  let refreshes = 0
  axios.defaults.adapter = async config => {
    if (config.url?.endsWith('/login')) return response(config, {access_token:'old',refresh_token:'refresh',user})
    if (config.url?.endsWith('/refresh')) {
      refreshes++
      await new Promise(resolve => setTimeout(resolve, 10))
      return response(config, {access_token:'new',refresh_token:'new-refresh'})
    }
    if (config.headers.Authorization === 'Bearer old') throw new AxiosError('expired', 'ERR_BAD_REQUEST', config, undefined, response(config, {}, 401))
    return response(config, {ok:true})
  }
  try {
    await auth.login('test', 'password')
    const results = await Promise.all([axios.get('/first'), axios.get('/second')])
    assert.equal(refreshes, 1)
    assert.equal(auth.token, 'new')
    assert.ok(results.every(item => item.data.ok))
  } finally {axios.defaults.adapter = original}
})

test('a refresh finishing after logout cannot restore the session', async () => {
  const auth = setup(), original = axios.defaults.adapter
  let release!: () => void, started!: () => void
  const refreshing = new Promise<void>(resolve => { started = resolve })
  const pending = new Promise<void>(resolve => { release = resolve })
  axios.defaults.adapter = async config => {
    if (config.url?.endsWith('/login')) return response(config, {access_token:'old',refresh_token:'refresh',user})
    if (config.url?.endsWith('/refresh')) {
      started(); await pending
      return response(config, {access_token:'new',refresh_token:'new-refresh'})
    }
    throw new AxiosError('expired', 'ERR_BAD_REQUEST', config, undefined, response(config, {}, 401))
  }
  try {
    await auth.login('test','password')
    const request = axios.get('/private').catch(error => error)
    await refreshing; auth.logout(); release(); await request
    assert.equal(auth.token, null)
    assert.equal(auth.user, null)
    assert.equal(localStorage.getItem('access_token'), null)
  } finally {axios.defaults.adapter = original}
})
