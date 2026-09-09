import axios from 'axios'
import { SERVER_ADDRESS_KEY, normalizeServerAddress } from './serverAddress.ts'

export const nativeApp = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
export const allowLanHttp = import.meta.env?.VITE_ANDROID_ALLOW_HTTP === 'true'
export function serverAddress() {
  return localStorage.getItem(SERVER_ADDRESS_KEY) || import.meta.env.VITE_API_BASE_URL || ''
}
export const serverFetch: typeof fetch = async (input, init) => {
  if (!nativeApp) return fetch(input, init)
  const { fetch: nativeFetch } = await import('@tauri-apps/plugin-http')
  // Keep authentication and registration cookies on the chosen server only.
  // Do not follow a redirect to another origin with an upload or session data.
  const signal = init?.signal ?? (input instanceof Request ? input.signal : undefined)
  return nativeFetch(input, { ...init, signal, maxRedirections: 0 })
}
export function configureApi() {
  if (!nativeApp) {
    if (import.meta.env.VITE_API_BASE_URL) axios.defaults.baseURL = normalizeServerAddress(import.meta.env.VITE_API_BASE_URL, import.meta.env.DEV)
    return
  }
  axios.defaults.adapter = 'fetch'
  axios.defaults.env = { ...axios.defaults.env, fetch: serverFetch }
  const address = serverAddress()
  try { axios.defaults.baseURL = address ? normalizeServerAddress(address, allowLanHttp) : '' } catch { axios.defaults.baseURL = '' }
  axios.interceptors.request.use(config => {
    if (!axios.defaults.baseURL) throw new Error('请先设置 App 要连接的服务器地址')
    // Do not send authentication headers to arbitrary links supplied by an API.
    const target = new URL(axios.getUri(config), axios.defaults.baseURL)
    if (target.origin !== new URL(axios.defaults.baseURL).origin) throw new Error('已阻止向其他服务器发送请求')
    // Let the Request constructor generate a matching multipart boundary.
    if (config.data instanceof FormData) config.headers.setContentType(false)
    return config
  })
}

export async function saveDownloadedBlob(blob: Blob, filename: string) {
  if (nativeApp) {
    const [{ save }, { writeFile }] = await Promise.all([
      import('@tauri-apps/plugin-dialog'), import('@tauri-apps/plugin-fs'),
    ])
    const destination = await save({ defaultPath: filename.replace(/[\\/]/g, '_'), title: '保存申请材料' })
    if (!destination) throw new Error('已取消保存文件')
    await writeFile(destination, new Uint8Array(await blob.arrayBuffer()))
    return
  }
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}
