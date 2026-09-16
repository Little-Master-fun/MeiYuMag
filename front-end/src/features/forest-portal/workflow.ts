import axios from 'axios'
import { saveDownloadedBlob } from '../../platform/native.ts'
import type { ApplicationNavigationTarget, PersonalApplicationApi } from './types'

export const applicationStatusLabels: Record<string, string> = {
  draft: '草稿',
  ai_reviewing: '初审中',
  ai_rejected: '初审未通过',
  pending_signed_files: '待签章材料',
  pending_admin_submit: '待管理员审核',
  supplement_required: '待补交材料',
  submitted: '已审核确认',
  completed: '已完成',
  rejected: '审核未通过',
  cancelled: '已取消',
  pending_admin_pre_review: '待人工初审',
}
export const fileLabels: Record<string, string> = {
  pre_review_word: '初审申请文件',
  supporting_material: '证明或说明材料',
  meiyu_signed_application_form: '签字盖章申请表',
  yueyuan_plan_file: '活动策划书',
  yueyuan_plan_signed_scan: '策划书签章扫描件',
  safety_responsibility_file: '安全责任书',
  safety_responsibility_signed_scan: '安全责任书签章扫描件',
  work_checklist_file: '工作检查清单',
  work_checklist_signed_scan: '检查清单签章扫描件',
  electricity_commitment_file: '用电承诺书',
  electricity_commitment_signed_scan: '用电承诺书签章扫描件',
  key_borrow_application: '钥匙借用申请表',
}
export const fileStatusLabels: Record<string, string> = {
  passed: '已通过',
  failed: '初审未通过',
  rejected: '待修正',
  pending: '待处理',
  pending_admin_review: '待审核',
}
export interface ApplicationFileItem {
  id: number
  file_type: string
  version: number
  original_filename: string
  review_status: string
  reject_reason: string | null
  download_url: string
  created_at: string
}
export function signedTypes(type: string) {
  if (type === 'meiyu_venue') return ['meiyu_signed_application_form']
  if (type === 'key_borrow') return ['key_borrow_application']
  return Object.keys(fileLabels).filter((key) => /^(yueyuan_|safety_|work_|electricity_)/.test(key))
}
export function targetForApplication(
  application: PersonalApplicationApi,
  venueName: string,
): ApplicationNavigationTarget {
  return {
    venueId: application.venue_id ?? 0,
    venueName,
    date: '',
    applicationId: application.id,
    applicationType: application.application_type,
    requiredFiles: application.required_files,
    reviewReason: application.review_reason,
    mode:
      application.status === 'pending_signed_files'
        ? 'signed'
        : application.status === 'ai_rejected'
          ? 'resubmit'
          : 'supplement',
  }
}
export async function downloadMaterial(url: string, filename: string) {
  const { data } = await axios.get(url, { responseType: 'blob' })
  await saveDownloadedBlob(data, filename)
}
