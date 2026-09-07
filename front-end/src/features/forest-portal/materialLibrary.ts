import axios from 'axios'
import { downloadMaterial } from './workflow.ts'
import type { ApplicationNavigationTarget } from './types'
import type { SubmissionRequirement } from './submission'

export interface MaterialTemplate {
  id: string
  name: string
  application_type: string
  file_type: string
  aliases?: string[]
  kind?: 'template' | 'example'
  description?: string
  download_url: string
}

export function materialType(target: ApplicationNavigationTarget) {
  if (target.mode === 'key' || target.applicationType === 'key_borrow') return 'key_borrow'
  return target.applicationType === 'yueyuan_third_floor' || target.venueName.includes('悦园三楼')
    ? 'yueyuan_third_floor'
    : 'meiyu_venue'
}

export function findMaterialTemplate(
  templates: MaterialTemplate[],
  requirement: SubmissionRequirement,
  target: ApplicationNavigationTarget,
) {
  const type = materialType(target)
  const fileType =
    requirement.fileType ||
    (requirement.kind === 'optional'
      ? 'supporting_material'
      : type === 'key_borrow'
        ? 'key_borrow_application'
        : 'pre_review_word')
  return templates.find(
    (item) =>
      (item.application_type === type || item.application_type === 'all') &&
      (item.file_type === fileType || item.aliases?.includes(fileType)),
  )
}

let catalogRequest: Promise<MaterialTemplate[]> | undefined
export function loadMaterialLibrary() {
  // Share one successful catalog request; a failed request can always be retried.
  return (catalogRequest ??= axios
    .get<MaterialTemplate[]>('/api/v1/templates')
    .then(({ data }) => data)
    .catch((error) => {
      catalogRequest = undefined
      throw error
    }))
}

export async function downloadRequirement(
  requirement: SubmissionRequirement,
  target: ApplicationNavigationTarget,
) {
  const item = findMaterialTemplate(await loadMaterialLibrary(), requirement, target)
  if (!item) throw new Error('这项材料暂未提供示例，请按管理员要求准备，不要使用其他材料代替。')
  await downloadMaterial(item.download_url, item.name)
  return item
}
