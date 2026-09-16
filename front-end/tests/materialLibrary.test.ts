import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  findMaterialTemplate,
  applicationDownloadRequirements,
  materialType,
  type MaterialTemplate,
} from '../src/features/forest-portal/materialLibrary.ts'
import { getSubmissionGuide } from '../src/features/forest-portal/submission.ts'
import type { ApplicationNavigationTarget } from '../src/features/forest-portal/types.ts'

const target: ApplicationNavigationTarget = { venueId: 1, venueName: '会议室', date: '2030-10-20' }
const catalog: MaterialTemplate[] = [
  {
    id: 'form',
    name: '原表.docx',
    application_type: 'meiyu_venue',
    file_type: 'meiyu_application_form',
    aliases: ['meiyu_signed_application_form'],
    download_url: '/form',
  },
  {
    id: 'example',
    name: '申请示例.docx',
    application_type: 'meiyu_venue',
    file_type: 'pre_review_word',
    download_url: '/example',
  },
  {
    id: 'plan',
    name: '策划示例.docx',
    application_type: 'yueyuan_third_floor',
    file_type: 'yueyuan_plan_file',
    aliases: ['pre_review_word', 'yueyuan_plan_signed_scan'],
    download_url: '/plan',
  },
  {
    id: 'key',
    name: '钥匙示例.png',
    application_type: 'key_borrow',
    file_type: 'key_borrow_application',
    download_url: '/key',
  },
  {
    id: 'support',
    name: '说明.docx',
    application_type: 'all',
    file_type: 'supporting_material',
    download_url: '/support',
  },
]
test('reference buttons separate three Yueyuan originals from the planning example', () => {
  const yueyuan = applicationDownloadRequirements('yueyuan_third_floor')
  assert.equal(yueyuan.length, 2)
  assert.equal(yueyuan[0]!.bundleId, 'yueyuan')
  assert.equal(yueyuan[1]!.templateId, 'yueyuan_plan_example')
  const meiyu = applicationDownloadRequirements('meiyu_venue')
  assert.deepEqual(meiyu.map(item => item.templateId), ['meiyu_activity_application', 'meiyu_application_example'])
  const example = { ...catalog[1]!, id: 'yueyuan_plan_example' }
  assert.equal(findMaterialTemplate([example], yueyuan[1]!, target), example)
  assert.equal(findMaterialTemplate(catalog, yueyuan[1]!, target), undefined)
  // Reference downloads must not turn the initial upload into a three-file requirement.
  assert.equal(getSubmissionGuide({ ...target, mode: 'new' }).requirements.length, 1)
})
test('initial and retry requirements select the example for the actual application type', () => {
  for (const mode of ['new', 'resubmit'] as const) {
    const plain = { ...target, mode }
    assert.equal(
      findMaterialTemplate(catalog, getSubmissionGuide(plain).requirements[0]!, plain)?.id,
      'example',
    )
    const yueyuan = { ...plain, applicationType: 'yueyuan_third_floor' }
    assert.equal(
      findMaterialTemplate(catalog, getSubmissionGuide(yueyuan).requirements[0]!, yueyuan)?.id,
      'plan',
    )
  }
  assert.equal(materialType({ ...target, venueName: '悦园三楼' }), 'yueyuan_third_floor')
})
test('scan requirements download the corresponding original, not another application type', () => {
  const requirement = {
    fileType: 'meiyu_signed_application_form',
    label: '签章申请表',
    kind: 'any' as const,
    extension: '扫描件',
  }
  assert.equal(findMaterialTemplate(catalog, requirement, target)?.id, 'form')
  assert.equal(
    findMaterialTemplate(catalog, requirement, {
      ...target,
      applicationType: 'yueyuan_third_floor',
    }),
    undefined,
  )
})
test('key and administrator-requested supporting references remain available', () => {
  const key = { ...target, mode: 'key' as const }
  assert.equal(
    findMaterialTemplate(catalog, getSubmissionGuide(key).requirements[0]!, key)?.id,
    'key',
  )
  assert.match(findMaterialTemplate(catalog, getSubmissionGuide(key).requirements[0]!, key)!.name, /\.png$/)
  assert.equal(getSubmissionGuide(key).requirements[0]!.extension, '.pdf')
  assert.match(getSubmissionGuide(key).description, /扫描.*OCR/)
  assert.equal(
    findMaterialTemplate(catalog, { label: '说明材料', fileType: 'supporting_material', kind: 'any', extension: '' }, target)?.id,
    'support',
  )
  assert.equal(
    findMaterialTemplate(
      catalog,
      { label: '未知材料', fileType: 'unknown', kind: 'any', extension: '' },
      target,
    ),
    undefined,
  )
})
