import axios from 'axios'
import type { ApplicationNavigationTarget, StagedSubmissionFile } from './types'

export interface SubmissionRequirement {
  fileType?: string
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
  if (target.mode === 'signed' || target.mode === 'supplement') {
    return {
      kicker:
        target.mode === 'signed' ? 'APPLICATION · SIGNED MATERIALS' : 'APPLICATION · SUPPLEMENT',
      step: target.mode === 'signed' ? '签章材料' : '补交材料',
      title: target.mode === 'signed' ? '递交签章材料' : '补齐这份申请',
      requirements: (target.requiredFiles ?? []).map((item) => ({
        label: item.label,
        fileType: item.file_type,
        extension: '文档 / 图片',
        kind: 'any',
      })),
      description:
        target.reviewReason || '请为信封里的每份文件选择对应材料，清单齐全后即可封缄送出。',
    }
  }
  if (target.mode === 'key')
    return {
      kicker: 'KEY BORROW · APPLICATION',
      step: '钥匙借用',
      title: '递交钥匙借用申请',
      requirements: [{ label: '钥匙借用申请表', extension: '.pdf', kind: 'primary' }],
      description: '请上传一份 PDF，写明钥匙名称、借用组织、借用时间和预计归还时间。',
    }
  if (target.mode === 'resubmit') {
    return {
      kicker: 'AI REVIEW · RETRY',
      step: '重新提交',
      title: '修正后重新初审',
      requirements: [
        {
          label:
            target.applicationType === 'yueyuan_third_floor'
              ? '修改后的活动策划书'
              : '修改后的场地申请表',
          extension: '.docx',
          kind: 'primary',
        },
      ],
      description: '新文件会保存为当前申请的新版本，并立即重新进入 AI 初审。',
    }
  }

  return {
    kicker: 'AI REVIEW · FIRST SUBMISSION',
    step: 'AI 初审',
    title: '提交场地申请',
    requirements: [
      {
        label:
          target.applicationType === 'yueyuan_third_floor' || target.venueName.includes('悦园三楼')
            ? '活动策划书'
            : '场地申请表',
        extension: '.docx',
        kind: 'primary',
      },
      { label: '证明或说明材料', extension: '可选 · 可多份', kind: 'optional' },
    ],
    description: `所选日期：${target.date}。文件中的场地和日期需与本次选择一致，系统将检查占用冲突。`,
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

export function mergeSubmissionFiles(current: StagedSubmissionFile[], incoming: File[]) {
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
    if (
      file.size === 0 ||
      [...current, ...accepted].reduce((sum, item) => sum + item.file.size, file.size) >
        100 * 1024 * 1024
    ) {
      errors.push('不支持空文件，且每次材料总大小不能超过 100MB')
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
  if (!axios.isAxiosError(error))
    return error instanceof Error ? error.message : '文件提交失败，请稍后重试'
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
  const validation = validateSubmission(target, stagedFiles)
  if (validation) throw new Error(validation)

  if (target.mode === 'key') {
    const form = new FormData()
    form.append('file', stagedFiles[0]!.file)
    await axios.post('/api/v1/keys/borrow', form)
    return { mode: 'success', message: '钥匙借用申请已送达，等待管理员审核' }
  }

  if (target.mode === 'signed' && target.applicationId) {
    const form = new FormData()
    stagedFiles.forEach((item) => form.append(item.fileType!, item.file))
    await axios.post(`/api/v1/applications/${target.applicationId}/signed-files`, form)
    return { mode: 'success', message: '签章材料已送达，等待管理员审核' }
  }

  if (target.mode === 'supplement' && target.applicationId) {
    const formData = new FormData()
    stagedFiles.forEach(({ file, fileType }) => {
      formData.append('files', file)
      formData.append('file_types', fileType!)
    })
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
        ? '重新初审通过，请回到申请档案继续递交签章材料'
        : '重新初审未通过，请在个人首页查看原因',
    }
  }

  formData.append(
    'application_type',
    target.venueName.includes('悦园三楼') ? 'yueyuan_third_floor' : 'meiyu_venue',
  )
  formData.append('venue_id', String(target.venueId))
  formData.append('expected_date', target.date)
  const { data } = await axios.post('/api/v1/applications/pre-review', formData)
  return {
    mode: data?.passed ? 'success' : 'error',
    message: data?.passed
      ? '初审通过，请回到申请档案继续递交签章材料'
      : '初审未通过，请在个人首页查看原因并重新提交',
  }
}

export function validateSubmission(
  target: ApplicationNavigationTarget,
  files: StagedSubmissionFile[],
): string | null {
  if (!files.length) return '请先将材料放入信封'
  if (target.mode === 'key')
    return files.length === 1 && files[0]!.file.name.toLowerCase().endsWith('.pdf')
      ? null
      : '钥匙借用请提交一份 PDF'
  if (target.mode === 'signed' || target.mode === 'supplement') {
    const required = target.requiredFiles ?? []
    if (!required.length) return '材料清单未加载，请返回档案重新打开'
    if (
      files.length !== required.length ||
      required.some((r) => files.filter((f) => f.fileType === r.file_type).length !== 1)
    )
      return '请将每份文件对应到材料清单，每项一份，全部齐全后再提交'
    return null
  }
  return files.some((f) => f.file.name.toLowerCase().endsWith('.docx'))
    ? null
    : '初审需要一份 .docx 格式的申请文件'
}
