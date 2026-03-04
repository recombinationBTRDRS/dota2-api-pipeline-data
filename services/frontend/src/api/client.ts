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
    throw new ApiError(0, err instanceof Error ? err.message : 'Network error')
  }

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new ApiError(res.status, `${res.status} ${text}`)
  }

  // Читаємо тіло як текст — безпечно для будь-якого status/content-type
  const body = await res.text()

  // Порожнє тіло (204 або 200 з empty body без content-length)
  if (!body.trim()) {
    return undefined as unknown as T
  }

  // Non-JSON content-type з непорожнім тілом — помилка, не маскуємо як успіх
  const contentType = res.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    throw new ApiError(res.status, `Unexpected content-type: ${contentType}`)
  }

  return JSON.parse(body) as T
}