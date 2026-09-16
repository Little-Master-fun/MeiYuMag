import type * as THREE from 'three'

export interface VenueApiItem {
  id: number
  name: string
}

export interface VenueCalendarEventApi {
  id: string
  title: string
  organization: string | null
  borrow_organization: string | null
  purpose_summary: string | null
  start_at: string
  end_at: string
  status: string
}

export interface VenueUsageRangeApi {
  start_date: string
  end_date: string
  venues: Array<{
    venue: VenueApiItem
    events: VenueCalendarEventApi[]
  }>
}

export interface PersonalApplicationApi {
  id: number
  secondary_reviewer_id?: number | null
  organization?: string | null
  borrow_organization?: string | null
  applicant_name?: string | null
  borrowed_key_name?: string | null
  applicant_department?: string | null
  application_type: string
  venue_id: number | null
  purpose_summary: string | null
  status: string
  start_at: string | null
  end_at: string | null
  review_reason: string | null
  required_files: Array<{ file_type: string; label: string }>
  requested_file_types: string[] | null
  created_at: string
}

export interface CameraFlight {
  startTarget: THREE.Vector3
  endTarget: THREE.Vector3
  currentTarget: THREE.Vector3
  startAngle: number
  angleDelta: number
  startRadius: number
  finalRadius: number
  startHeight: number
  finalHeight: number
  moveDuration: number
  rotationDuration: number
  totalDuration: number
  startedAt: number
}

export interface PostLoginFlight {
  startPosition: THREE.Vector3
  endPosition: THREE.Vector3
  startTarget: THREE.Vector3
  endTarget: THREE.Vector3
  currentTarget: THREE.Vector3
  startClipboardPosition: THREE.Vector3
  endClipboardPosition: THREE.Vector3
  startClipboardQuaternion: THREE.Quaternion
  endClipboardQuaternion: THREE.Quaternion
  startClipboardScale: number
  endClipboardScale: number
  cameraDuration: number
  clipboardDuration: number
  overlapDuration: number
  startedAt: number
}

export interface ApplicationNavigationTarget {
  venueId: number
  venueName: string
  date: string
  mode?: 'new' | 'resubmit' | 'supplement' | 'signed' | 'key'
  applicationId?: number
  applicationType?: string
  requiredFiles?: Array<{ file_type: string; label: string }>
  reviewReason?: string | null
}

export interface StagedSubmissionFile {
  id: string
  file: File
  fileType?: string
}

export interface ApplicationFlight {
  startPosition: THREE.Vector3
  endPosition: THREE.Vector3
  startTarget: THREE.Vector3
  endTarget: THREE.Vector3
  currentTarget: THREE.Vector3
  startClipboardPosition: THREE.Vector3
  endClipboardPosition: THREE.Vector3
  startClipboardQuaternion: THREE.Quaternion
  endClipboardQuaternion: THREE.Quaternion
  startClipboardScale: number
  endClipboardScale: number
  cameraDelay: number
  cameraDuration: number
  clipboardDelay: number
  clipboardDuration: number
  totalDuration: number
  envelopeStarted: boolean
  startedAt: number
}

export type SubmissionEnvelopeState =
  | 'hidden'
  | 'ready'
  | 'drag'
  | 'uploading'
  | 'success'
  | 'error'

export interface SubmissionEnvelopeVisual {
  object: THREE.Object3D
  homeParent: THREE.Object3D
  homePosition: THREE.Vector3
  homeQuaternion: THREE.Quaternion
  homeScale: THREE.Vector3
}

export type SubmissionEnvelopeFlapState = 'closed' | 'opening' | 'open' | 'closing'

export interface SubmissionEnvelopeFlapVisual {
  pivot: THREE.Group
  flap: THREE.Mesh
  underside: THREE.Mesh
  interior: THREE.Mesh
}
