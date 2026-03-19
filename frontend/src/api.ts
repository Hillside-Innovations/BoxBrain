export type CaptureDiagnostics = {
  frame_count: number
  brightness: number
  blur_score: number
}

export type BoxResponse = {
  id: number
  label: string
  location: string | null
  location_id: number | null
  location_color: string | null
  created_at: string
  updated_at: string
  has_video: boolean
  contents: string[]
  diagnostics?: CaptureDiagnostics | null
}

export type LocationResponse = {
  id: number
  name: string
  color: string
  created_at: string
}

/** URL for the box scan image (first frame). Append cache-buster if needed. */
export function getBoxImageUrl(boxId: number): string {
  const base =
    (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
    (typeof window !== 'undefined'
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : 'http://127.0.0.1:8000')
  return `${base}/boxes/${boxId}/image`
}

export type SearchHit = {
  box_id: number
  box_label: string
  score: number
}

export type SearchResponse = {
  query: string
  results: SearchHit[]
}

export class ApiError extends Error {
  status: number
  payload: unknown

  constructor(message: string, status: number, payload: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

// Use same host as the page so phone (http://<LAN_IP>:5173) calls backend at http://<LAN_IP>:8000
const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  (typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : 'http://127.0.0.1:8000')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, init)
  if (res.status === 204) return undefined as T
  const contentType = res.headers.get('content-type') ?? ''
  const isJson = contentType.includes('application/json')
  const payload = isJson ? await res.json().catch(() => null) : await res.text().catch(() => null)

  if (!res.ok) {
    const detail =
      typeof payload === 'object' && payload && 'detail' in payload
        ? (payload as { detail?: unknown }).detail
        : null
    const message =
      typeof detail === 'string'
        ? detail
        : `Request failed (${res.status} ${res.statusText})`
    throw new ApiError(message, res.status, payload)
  }

  if (res.status === 204) return undefined as T
  return payload as T
}

export async function listBoxes(): Promise<BoxResponse[]> {
  return await request<BoxResponse[]>('/boxes')
}

export async function createBox(body: { label: string; location_id?: number | null }): Promise<BoxResponse> {
  return await request<BoxResponse>('/boxes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function updateBox(
  boxId: number,
  body: { location_id?: number | null; label?: string },
): Promise<BoxResponse> {
  return await request<BoxResponse>(`/boxes/${boxId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function listLocations(): Promise<LocationResponse[]> {
  return await request<LocationResponse[]>('/locations')
}

export async function createLocation(body: { name: string; color: string }): Promise<LocationResponse> {
  return await request<LocationResponse>('/locations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deleteLocation(locationId: number): Promise<void> {
  await request<void>(`/locations/${locationId}`, { method: 'DELETE' })
}

export async function deleteBox(boxId: number): Promise<void> {
  await request<void>(`/boxes/${boxId}`, { method: 'DELETE' })
}

/** Video processing (frames + vision + embed) can take 1–2+ minutes; use a long timeout. */
const UPLOAD_TIMEOUT_MS = 5 * 60 * 1000

export async function uploadBoxVideo(boxId: number, file: File): Promise<BoxResponse> {
  const fd = new FormData()
  fd.append('video', file, file.name)
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS)
  try {
    return await request<BoxResponse>(`/boxes/${boxId}/video`, {
      method: 'POST',
      body: fd,
      signal: controller.signal,
    })
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function searchBoxes(q: string): Promise<SearchResponse> {
  const qs = new URLSearchParams({ q })
  return await request<SearchResponse>(`/search?${qs.toString()}`)
}

export type LanIpv4Response = { lan_ipv4: string | null }

export async function getLanIpv4(): Promise<string | null> {
  const data = await request<LanIpv4Response>('/meta/lan-ipv4')
  return data.lan_ipv4 ?? null
}

/** Web app URL reachable on the LAN, using this machine’s IPv4 and the current page port/path. */
export function webappUrlForLanHost(lanIpv4: string): string {
  const { protocol, pathname, search, port } = window.location
  const host = port ? `${lanIpv4}:${port}` : lanIpv4
  return `${protocol}//${host}${pathname}${search}`
}

