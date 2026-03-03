// services/frontend/src/api/client.ts
// Базовий fetch wrapper. Всі запити йдуть через /api → проксується vite → localhost:8000.

const BASE = '/api'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, options)
  } catch (err) {
    // Network failure (no connection, DNS, CORS preflight)
    throw new ApiError(0, err instanceof Error ? err.message : 'Network error')
  }

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new ApiError(res.status, `${res.status} ${text}`)
  }

  // 204 No Content або порожнє тіло — повертаємо undefined
  const contentLength = res.headers.get('content-length')
  const contentType = res.headers.get('content-type') ?? ''
  if (res.status === 204 || contentLength === '0' || !contentType.includes('application/json')) {
    return undefined as unknown as T
  }

  return res.json() as Promise<T>
}