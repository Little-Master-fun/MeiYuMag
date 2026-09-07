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

test('upload payloads preserve supplement types, signed field names and selected date', async () => {
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
    assert.equal(sent[2]!.data.get('expected_date'), '2035-12-20')
    assert.equal(sent[2]!.data.get('venue_id'), '1')
  } finally {
    axios.defaults.adapter = original
  }
})
