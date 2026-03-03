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
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new ApiError(res.status, `${res.status} ${text}`)
  }
  return res.json() as Promise<T>
}