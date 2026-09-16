import { test } from 'node:test'
import assert from 'node:assert/strict'
import axios from 'axios'
import {
  getSubmissionGuide,
  mergeSubmissionFiles,
  uploadApplicationFiles,
  validateSubmission,
} from '../src/features/forest-portal/submission.ts'
import type {
  ApplicationNavigationTarget,
  StagedSubmissionFile,
} from '../src/features/forest-portal/types.ts'

const target: ApplicationNavigationTarget = {
  venueId: 1,
  venueName: '会议室',
  date: '2035-12-20',
  applicationId: 91,
  mode: 'supplement',
  requiredFiles: [
    { file_type: 'meiyu_signed_application_form', label: '签章申请表' },
    { file_type: 'supporting_material', label: '说明材料' },
  ],
}
const makeFile = (id: string, fileType?: string): StagedSubmissionFile => ({
  id,
  fileType,
  file: new File(['%PDF-1.7'], `${id}.pdf`),
})

test('supplements require exactly one file for every requested type', () => {
  assert.ok(validateSubmission(target, [makeFile('one')]))
  assert.ok(validateSubmission(target, [makeFile('one', 'meiyu_signed_application_form')]))
  assert.ok(
    validateSubmission(target, [
      makeFile('one', 'meiyu_signed_application_form'),
      makeFile('two', 'meiyu_signed_application_form'),
    ]),
  )
  assert.equal(
    validateSubmission(target, [
      makeFile('one', 'meiyu_signed_application_form'),
      makeFile('two', 'supporting_material'),
    ]),
    null,
  )
})

test('file staging deduplicates and rejects unsupported and empty files', () => {
  const file = new File(['data'], 'application.pdf', { lastModified: 1 })
  const result = mergeSubmissionFiles(
    [],
    [file, file, new File(['data'], 'file.exe'), new File([], 'empty.pdf')],
  )
  assert.equal(result.files.length, 1)
  assert.equal(result.errors.length, 2)
})

test('key borrowing accepts only one PDF and Yueyuan uses a planning document', () => {
  assert.equal(validateSubmission({ ...target, mode: 'key' }, [makeFile('key')]), null)
  assert.ok(validateSubmission({ ...target, mode: 'key' }, [makeFile('key'), makeFile('extra')]))
  assert.match(
    getSubmissionGuide({ ...target, mode: 'new', applicationType: 'yueyuan_third_floor' })
      .requirements[0]!.label,
    /策划书/,
  )
})

test('upload payloads preserve typed follow-ups but new applications use document recognition', async () => {
  const original = axios.defaults.adapter
  const sent: Array<{ url: string; data: FormData }> = []
  axios.defaults.adapter = async (config) => {
    sent.push({ url: config.url!, data: config.data })
    return { data: { passed: true }, status: 200, statusText: 'OK', headers: {}, config }
  }
  try {
    await uploadApplicationFiles(target, [
      makeFile('one', 'meiyu_signed_application_form'),
      makeFile('two', 'supporting_material'),
    ])
    assert.match(sent[0]!.url, /\/files\/batch$/)
    assert.deepEqual(sent[0]!.data.getAll('file_types'), [
      'meiyu_signed_application_form',
      'supporting_material',
    ])
    await uploadApplicationFiles(
      { ...target, mode: 'signed', requiredFiles: target.requiredFiles!.slice(0, 1) },
      [makeFile('signed', 'meiyu_signed_application_form')],
    )
    assert.match(sent[1]!.url, /\/signed-files$/)
    assert.ok(sent[1]!.data.get('meiyu_signed_application_form') instanceof File)
    await uploadApplicationFiles({ ...target, mode: 'new' }, [
      { id: 'primary', file: new File(['word'], 'application.docx') },
    ])
    assert.equal(sent[2]!.data.get('expected_date'), null)
    assert.equal(sent[2]!.data.get('venue_id'), null)
    assert.equal(sent[2]!.data.get('application_type'), 'auto')
    assert.equal(sent[2]!.data.has('additional_files'), false)
  } finally {
    axios.defaults.adapter = original
  }
})

test('initial submission has only one required Word file and no optional proof material', () => {
  const initial = { ...target, mode: 'new' as const, venueId: 0, date: '', applicationType: 'auto' }
  const primary = { id: 'primary', file: new File(['word'], 'application.docx') }
  assert.equal(validateSubmission(initial, [primary]), null)
  assert.ok(validateSubmission(initial, [primary, makeFile('proof')]))
  assert.ok(validateSubmission(initial, [makeFile('proof')]))
  assert.equal(getSubmissionGuide(initial).requirements.length, 1)
  assert(!getSubmissionGuide(initial).requirements.some(item => item.kind === 'optional'))
  assert.match(getSubmissionGuide(initial).description, /无需另选/)
})

test('signed and supplementary guides explain manual review and Word support', () => {
  for (const mode of ['signed', 'supplement'] as const) {
    const guide = getSubmissionGuide({ ...target, mode })
    assert.match(guide.description, /管理员人工核对/)
    assert.match(guide.description, /支持 Word 或 PDF 扫描件/)
    assert.match(guide.description, /littlemasterfun@gmail\.com/)
  }
})

test('AI service fallback is an accepted upload, not a material rejection', async () => {
  const original = axios.defaults.adapter
  axios.defaults.adapter = async config => ({ data: { passed: false, next_status: 'pending_admin_pre_review' }, status: 200, statusText: 'OK', headers: {}, config })
  try {
    for (const mode of ['new', 'resubmit'] as const) {
      const result = await uploadApplicationFiles({ ...target, mode, venueId: 0 }, [{id: 'word', file: new File(['word'], 'test.docx')}])
      assert.equal(result.mode, 'success')
      assert.match(result.message, /人工初审/)
    }
    assert.match(getSubmissionGuide({...target, mode:'key'}).description, /无需 OCR/)
    assert.match(getSubmissionGuide({...target, mode:'key'}).description, /不调用 AI/)
  } finally { axios.defaults.adapter = original }
})
