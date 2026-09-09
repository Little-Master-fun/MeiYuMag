<script setup lang="ts">
import { ref } from 'vue'
import { allowLanHttp, serverAddress, serverFetch } from './native'
import { SERVER_ADDRESS_KEY, normalizeServerAddress } from './serverAddress'

const current = serverAddress()
const open = ref(!current)
const address = ref(current)
const message = ref('')
const testing = ref(false)
function save() {
  try {
    const next = normalizeServerAddress(address.value, allowLanHttp)
    if (next !== current) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
    localStorage.setItem(SERVER_ADDRESS_KEY, next)
    window.location.reload()
  } catch (error) { message.value = (error as Error).message }
}
async function testConnection() {
  testing.value = true
  message.value = '正在寻找信箱的地址…'
  try {
    const next = normalizeServerAddress(address.value, allowLanHttp)
    const response = await serverFetch(`${next}/api/v1/health`, { signal: AbortSignal.timeout(8000), credentials: 'omit' })
    const data = await response.json()
    if (!response.ok || data.status !== 'ok') throw new Error('服务器未返回有效的健康检查结果')
    message.value = '连接成功，可以保存并进入。'
  } catch (error) { message.value = `未能连接：${(error as Error).message}。请确认地址、网络和后端 CORS 配置。` }
  finally { testing.value = false }
}
</script>

<template>
  <button class="server-tab" @click="open = true">服务器</button>
  <div v-if="open" class="server-veil" @click.self="current && (open = false)">
    <section role="dialog" aria-modal="true" aria-labelledby="server-title" class="server-paper">
      <small>MEIYU · ANDROID</small>
      <h1 id="server-title">为信件填写地址</h1>
      <p>小屋和场景已保存在 App 内，登录、场地记录和文件审核需要连接你的美育服务器。</p>
      <label for="server-address">服务器地址</label>
      <input id="server-address" v-model="address" type="url" inputmode="url" placeholder="https://你的服务器地址" autocomplete="url" autocapitalize="none" spellcheck="false" />
      <p v-if="allowLanHttp" class="hint">局域网测试可填 http://电脑局域网IP:8000。手机上的 localhost 指手机本身，不是电脑。请勿通过 HTTP 提交真实敏感材料。</p>
      <p class="hint">填写根地址即可，不必加 /api/v1。更换服务器将清除本机登录状态，未确认的暂存文件不会保留。</p>
      <p v-if="message" role="status">{{ message }}</p>
      <footer>
        <button v-if="current" @click="open = false">返回小屋</button>
        <button :disabled="testing" @click="testConnection">{{ testing ? '连接中…' : '测试连接' }}</button>
        <button class="save" :disabled="testing" @click="save">保存并进入 ↗</button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.server-tab { position: fixed; right: 12px; bottom: calc(12px + env(safe-area-inset-bottom)); z-index: 1100; border: 1px solid #a8ac90; background: #f0e7cf; color: #596e54; padding: 10px 14px; border-radius: 3px 13px 5px 7px; font: 12px 'Songti SC',serif; }
.server-veil { position: fixed; inset: 0; z-index: 1200; background: #23352b90; display: grid; place-items: center; padding: 20px; }
.server-paper { box-sizing: border-box; width: min(440px,100%); max-height: calc(100dvh - 40px); overflow: auto; padding: 26px; border: 1px solid #b4a77b; border-radius: 5px 20px 6px 13px; color: #635133; background: #f0e6c7; font: 14px/1.7 'Songti SC',serif; }
h1 { font-size: 25px; font-weight: 500; margin: 8px 0 16px; }
small,.hint { color: #827455; font-size: 12px; }
label { display: block; margin-top: 18px; }
input { box-sizing: border-box; width: 100%; padding: 12px 4px; border: 0; border-bottom: 1px dashed #8a936d; color: #465b48; background: transparent; font-size: 16px; }
footer { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
button { min-height: 44px; cursor: pointer; touch-action: manipulation; }
footer button { border: 1px solid #97a080; border-radius: 3px 11px 3px 6px; background: transparent; color: #54694d; padding: 8px 13px; font: inherit; }
footer .save { background: #607654; color: #f6edd2; }
button:disabled { opacity: .5; }
</style>
