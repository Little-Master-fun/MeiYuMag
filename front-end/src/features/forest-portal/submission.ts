import axios from 'axios'
import type { ApplicationNavigationTarget, StagedSubmissionFile } from './types'

export interface SubmissionRequirement {
  label: string
  extension: string
  kind: 'primary' | 'optional' | 'any'
}

export interface SubmissionGuide {
  kicker: string
  step: string
  title: string
  requirements: SubmissionRequirement[]
  description: string
}

export interface SubmissionUploadResult {
  mode: 'success' | 'error'
  message: string
}

const allowedExtensions = new Set(['.doc', '.docx', '.pdf', '.jpg', '.jpeg', '.png'])
const maxFileSize = 30 * 1024 * 1024
const maxFileCount = 10

export function getSubmissionGuide(target: ApplicationNavigationTarget): SubmissionGuide {
  if (target.mode === 'resubmit') {
    return {
      kicker: 'AI REVIEW · RETRY',
      step: '重新提交',
      title: '修正后重新初审',
      requirements: [
        { label: '修改后的场地申请表', extension: '.docx', kind: 'primary' },
      ],
      description: '新文件会保存为当前申请的新版本，并立即重新进入 AI 初审。',
    }
  }

  if (target.mode === 'supplement') {
    return {
      kicker: 'APPLICATION · SUPPLEMENT',
      step: '补交材料',
      title: '补充申请材料',
      requirements: [
        { label: '管理员指定的补交材料', extension: '文档 / 图片', kind: 'any' },
      ],
      description: '材料送达后，申请会回到管理员审核流程继续处理。',
    }
  }

  return {
    kicker: 'AI REVIEW · FIRST SUBMISSION',
    step: 'AI 初审',
    title: '提交场地申请',
    requirements: [
      { label: '场地申请表', extension: '.docx', kind: 'primary' },
      { label: '证明或说明材料', extension: '可选 · 可多份', kind: 'optional' },
    ],
    description: '系统将读取申请信息、使用时间，并自动检查场地占用冲突。',
  }
}

export function getSubmissionFileExtension(filename: string) {
  const dotIndex = filename.lastIndexOf('.')
  return dotIndex >= 0 ? filename.slice(dotIndex).toLowerCase() : ''
}

export function formatSubmissionFileSize(size: number) {
  if (size === 0) return '0 KB'
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`
  return `${(size / 1024 / 1024).toFixed(size >= 10 * 1024 * 1024 ? 0 : 1)} MB`
}

export function mergeSubmissionFiles(
  current: StagedSubmissionFile[],
  incoming: File[],
) {
  const existing = new Set(
    current.map(({ file }) => `${file.name}:${file.size}:${file.lastModified}`),
  )
  const accepted: StagedSubmissionFile[] = []
  const errors: string[] = []

  for (const file of incoming) {
    const identity = `${file.name}:${file.size}:${file.lastModified}`
    if (existing.has(identity)) continue
    const extension = getSubmissionFileExtension(file.name)
    if (!allowedExtensions.has(extension)) {
      errors.push(`“${file.name}”的格式暂不支持`)
      continue
    }
    if (file.size > maxFileSize) {
      errors.push(`“${file.name}”超过 30MB`)
      continue
    }
    if (current.length + accepted.length >= maxFileCount) {
      errors.push('一次最多暂存 10 个文件')
      break
    }
    existing.add(identity)
    accepted.push({
      id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`,
      file,
    })
  }

  return { files: [...current, ...accepted], acceptedCount: accepted.length, errors }
}

export function getSubmissionErrorMessage(error: unknown) {
  if (!axios.isAxiosError(error)) return '文件提交失败，请稍后重试'
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (typeof item?.msg === 'string' ? item.msg : ''))
      .filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return error.message || '文件提交失败，请稍后重试'
}

export async function uploadApplicationFiles(
  target: ApplicationNavigationTarget,
  stagedFiles: StagedSubmissionFile[],
): Promise<SubmissionUploadResult> {
  const primaryItem = stagedFiles.find(({ file }) => file.name.toLowerCase().endsWith('.docx'))
  const fileCount = stagedFiles.length

  if (target.mode === 'supplement' && target.applicationId) {
    const formData = new FormData()
    stagedFiles.forEach(({ file }) => formData.append('files', file))
    formData.append('file_type', 'supplement_file')
    await axios.post(`/api/v1/applications/${target.applicationId}/files/batch`, formData)
    return {
      mode: 'success',
      message: `${fileCount} 份补交材料已送达，申请重新进入审核流程`,
    }
  }

  if (!primaryItem) throw new Error('缺少 .docx 格式的场地申请表')
  const formData = new FormData()
  formData.append('file', primaryItem.file)
  stagedFiles
    .filter((item) => item.id !== primaryItem.id)
    .forEach(({ file }) => formData.append('additional_files', file))

  if (target.mode === 'resubmit' && target.applicationId) {
    const { data } = await axios.post(
      `/api/v1/applications/${target.applicationId}/pre-review`,
      formData,
    )
    return {
      mode: data?.passed ? 'success' : 'error',
      message: data?.passed
        ? '重新初审通过，申请已预占用'
        : '重新初审未通过，请在个人首页查看原因',
    }
  }

  formData.append(
    'application_type',
    target.venueName.includes('悦园三楼') ? 'yueyuan_third_floor' : 'meiyu_venue',
  )
  formData.append('venue_id', String(target.venueId))
  const { data } = await axios.post('/api/v1/applications/pre-review', formData)
  return {
    mode: data?.passed ? 'success' : 'error',
    message: data?.passed
      ? '初审通过，申请已预占用'
      : '初审未通过，请在个人首页查看原因并重新提交',
  }
}
