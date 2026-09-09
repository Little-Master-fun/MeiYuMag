import assert from 'node:assert/strict'
import { test } from 'node:test'
import { normalizeServerAddress } from '../src/platform/serverAddress.ts'

test('server root normalizes API suffix and preserves reverse proxy path', () => {
  assert.equal(normalizeServerAddress(' https://example.edu.cn/api/v1/ '), 'https://example.edu.cn')
  assert.equal(normalizeServerAddress('https://example.edu.cn/meiyu/'), 'https://example.edu.cn/meiyu')
})
test('only debug builds may use private HTTP addresses', () => {
  for (const address of ['http://192.168.1.8:8000', 'http://10.0.2.2:8000', 'http://127.0.0.1:8000']) {
    assert.throws(() => normalizeServerAddress(address))
    assert.equal(normalizeServerAddress(address, true), address)
  }
  assert.throws(() => normalizeServerAddress('http://example.com', true))
  assert.throws(() => normalizeServerAddress('http://192.168.example.com', true))
})
test('credentials, fragments and non-HTTP schemes cannot become a server address', () => {
  for (const address of ['https://user:password@example.com', 'https://example.com?token=123', 'https://example.com/#abc', 'javascript:alert(1)', '//example.com', 'file:///tmp/test']) {
    assert.throws(() => normalizeServerAddress(address, true))
  }
})
