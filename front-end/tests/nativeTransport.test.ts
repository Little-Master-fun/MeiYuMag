import assert from 'node:assert/strict'
import test from 'node:test'
import axios from 'axios'

// Exercise the real Axios fetch adapter and Tauri JS bridge without contacting
// a real server, uploading documents, or triggering SMS / AI / email work.
const storage = new Map([['meiyu.server-address.v1', 'https://meiyu.example.test']])
const requests: Array<{ url: string; method: string; headers: string[][]; data: number[]; maxRedirections: number }> = []
const consumed = new Set<number>()
Object.defineProperty(globalThis, 'localStorage', { value: { getItem: (key: string) => storage.get(key) || null }, configurable: true })
Object.defineProperty(globalThis, 'window', {
  configurable: true,
  value: { __TAURI_INTERNALS__: { invoke: async (command: string, args: any) => {
    if (command === 'plugin:http|fetch') { requests.push(args.clientConfig); return requests.length }
    if (command === 'plugin:http|fetch_send') return {
      status: 200, statusText: 'OK', url: requests[args.rid - 1]!.url,
      headers: [['content-type', 'application/json']], rid: args.rid,
    }
    if (command === 'plugin:http|fetch_read_body') {
      if (consumed.has(args.rid)) return [1]
      consumed.add(args.rid)
      return [...new TextEncoder().encode('{"ok":true}'), 0]
    }
    throw new Error(`Unexpected native command: ${command}`)
  } } },
})
const { configureApi } = await import('../src/platform/native.ts')
configureApi()

test('native transport preserves JSON payload and authentication on the configured origin', async () => {
  const response = await axios.post('/api/v1/mock', { sample: true }, { headers: { Authorization: 'Bearer test-only-token' } })
  assert.deepEqual(response.data, { ok: true })
  const request = requests.at(-1)!
  assert.equal(request.url, 'https://meiyu.example.test/api/v1/mock')
  assert.equal(new TextDecoder().decode(new Uint8Array(request.data)), '{"sample":true}')
  assert.ok(request.headers.some(([name, value]) => name === 'authorization' && value === 'Bearer test-only-token'))
  assert.equal(request.maxRedirections, 0)
})

test('native multipart submission keeps all filenames and fields; downloads stay blobs', async () => {
  const form = new FormData()
  form.append('file', new Blob(['sample-document']), 'example.docx')
  form.append('venue_id', '7')
  await axios.post('/api/v1/mock-upload', form)
  const request = requests.at(-1)!
  assert.ok(request.headers.some(([name, value]) => name === 'content-type' && value.includes('multipart/form-data; boundary=')))
  const body = new TextDecoder().decode(new Uint8Array(request.data))
  assert.ok(body.includes('filename="example.docx"'))
  assert.ok(body.includes('sample-document'))
  assert.ok(body.includes('name="venue_id"'))
  const response = await axios.get('/api/v1/mock-template', { responseType: 'blob' })
  assert.ok(response.data instanceof Blob)
})

test('native transport blocks other origins and requests before configuring a server', async () => {
  const count = requests.length
  await assert.rejects(axios.get('https://untrusted.example/api'), /已阻止/)
  await assert.rejects(axios.get('/api', { baseURL: 'https://untrusted.example' }), /已阻止/)
  assert.equal(requests.length, count)
  axios.defaults.baseURL = ''
  await assert.rejects(axios.get('/api/v1/mock'), /请先设置/)
  assert.equal(requests.length, count)
})
