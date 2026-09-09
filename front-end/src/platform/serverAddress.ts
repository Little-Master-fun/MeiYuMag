export const SERVER_ADDRESS_KEY = 'meiyu.server-address.v1'

export function normalizeServerAddress(input: string, allowLanHttp = false): string {
  let url: URL
  try { url = new URL(input.trim()) } catch { throw new Error('请填写完整服务器地址，例如 https://meiyu.example.edu.cn') }
  if (url.username || url.password || url.search || url.hash) throw new Error('服务器地址不能包含账号、密码、查询参数或锚点')
  const host = url.hostname.toLowerCase()
  const octets = host.split('.').map(Number)
  const ipv4 = /^\d+\.\d+\.\d+\.\d+$/.test(host) && octets.every(part => part >= 0 && part <= 255)
  const privateHost = host === 'localhost' || host === '[::1]' ||
    (ipv4 && (octets[0] === 127 || octets[0] === 10 || (octets[0] === 192 && octets[1] === 168) ||
      (octets[0] === 172 && octets[1]! >= 16 && octets[1]! <= 31)))
  if (url.protocol !== 'https:' && !(allowLanHttp && url.protocol === 'http:' && privateHost)) {
    throw new Error(allowLanHttp ? '请使用 HTTPS；测试版只允许局域网或本机地址使用 HTTP' : '请使用安全的 HTTPS 服务器地址')
  }
  url.pathname = url.pathname.replace(/\/api\/v1\/?$/, '').replace(/\/+$/, '') || '/'
  return url.toString().replace(/\/$/, '')
}
