export type Role = 'user' | 'admin'
export type Mode = 'train' | 'dev' | 'cpu'

export interface AppConfig {
  max_booking_days: number
}

export interface User {
  id: number
  display_name: string
  email: string
  role: Role
  approved: boolean
  active: boolean
  color: string
  created_at: string
}

export type UserDirectoryEntry = Pick<User, 'id' | 'display_name' | 'color'>

export interface Gpu {
  id: number
  server_id: number
  name: string
  memory_mb: number | null
  active: boolean
}

export interface Server {
  id: number
  name: string
  hostname: string | null
  active: boolean
  gpus: Gpu[]
}

export interface ProjectMember {
  id: number
  display_name: string
  color: string
}

export interface Project {
  id: number
  name: string
  description: string | null
  owner_id: number
  active: boolean
  members: ProjectMember[]
  created_at: string
}

export interface BookingGpu {
  id: number
  server_id: number
  name: string
  memory_mb: number | null
  active: boolean
}

export interface Booking {
  id: number
  user: Pick<User, 'id' | 'display_name' | 'color' | 'role'>
  project: { id: number; name: string; members: number[] }
  gpus: BookingGpu[]
  server_id: number | null
  mode: Mode
  start_at: string
  end_at: string
  series_id: string | null
  series_start_at: string | null
  series_end_at: string | null
  daily_start_hour: number | null
  daily_end_hour: number | null
  description: string | null
}

export interface ProjectCreate {
  name: string
  description?: string
  member_ids: number[]
}

export interface ApiError {
  status: number
  detail: string | ApiErrorDetail
}

export interface ApiErrorDetail {
  code?: string
  message?: string
  [key: string]: unknown
}

export interface BookingConflictDetail extends ApiErrorDetail {
  code: 'booking_conflict'
  message: string
  start_at: string
  end_at: string
}
