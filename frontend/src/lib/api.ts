import type { AuthStatus, ObjectMetadata, ObjectName, RecordPage, SfRecord } from '../types'

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options?.headers ?? {}) },
  })
  if (!response.ok) {
    let body: unknown = undefined
    try { body = await response.json() } catch { body = undefined }
    const detail = typeof body === 'object' && body && 'detail' in body ? (body as { detail: unknown }).detail : body
    const message = typeof detail === 'string'
      ? detail
      : typeof detail === 'object' && detail && 'message' in detail
        ? String((detail as { message: unknown }).message)
        : `Request failed (${response.status})`
    throw new ApiError(response.status, message, detail)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  authStatus: () => request<AuthStatus>('/api/auth/status'),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
  metadata: (objectName: ObjectName) => request<ObjectMetadata>(`/api/objects/${objectName}/metadata`),
  records: (objectName: ObjectName, fields: string[], cursor?: string | null) => {
    const query = new URLSearchParams({ fields: fields.join(',') })
    if (cursor) query.set('cursor', cursor)
    return request<RecordPage>(`/api/objects/${objectName}/records?${query}`)
  },
  record: (objectName: ObjectName, id: string, fields: string[]) => {
    const query = new URLSearchParams({ fields: fields.join(',') })
    return request<SfRecord>(`/api/objects/${objectName}/records/${id}?${query}`)
  },
  create: (objectName: ObjectName, values: Record<string, unknown>) =>
    request<{ id: string; success: boolean }>(`/api/objects/${objectName}/records`, { method: 'POST', body: JSON.stringify({ values }) }),
  update: (objectName: ObjectName, id: string, values: Record<string, unknown>) =>
    request<{ id: string; success: boolean }>(`/api/objects/${objectName}/records/${id}`, { method: 'PATCH', body: JSON.stringify({ values }) }),
  delete: (objectName: ObjectName, id: string) =>
    request<{ id: string; success: boolean }>(`/api/objects/${objectName}/records/${id}`, { method: 'DELETE' }),
}
