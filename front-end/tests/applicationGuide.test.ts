import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const guide = readFileSync(new URL('../src/features/forest-portal/components/ApplicationGuide.vue', import.meta.url), 'utf8')

test('application guide explains user actions without internal review implementation', () => {
  assert.doesNotMatch(guide, /\bAI\b|请求失败|通知管理员|不接入|不调用/)
  for (const action of ['查看空闲', '提交材料', '预审核通过', '提交签字盖章材料', '重新提交', '已审核确认']) {
    assert.ok(guide.includes(action), `Missing user action: ${action}`)
  }
})

test('application guide retains document, scan and staging requirements', () => {
  for (const requirement of ['一份 DOCX', '一份 PDF', '不接受普通拍照照片', '签字盖章页', '不会保留未上传文件', '不能原样提交']) {
    assert.ok(guide.includes(requirement), `Missing requirement: ${requirement}`)
  }
})
