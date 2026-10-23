/** Client for the backend's /api/auth endpoints. The session lives in an HttpOnly cookie. */

export type User = { id: number; first_name: string; last_name: string; email: string; is_admin: boolean }

export type RegisterInput = { first_name: string; last_name: string; email: string; password: string }

export class ApiError extends Error {
  status: number
  fields: Record<string, string>

  constructor(status: number, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fields = fields
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    throw new ApiError(0, 'Can’t reach the shop server. Is the backend running?')
  }
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Something went wrong. Please try again.'
    throw new ApiError(res.status, res.status >= 500 ? 'The shop server had a problem. Please try again.' : detail, data.fields)
  }
  return data as T
}

export const authApi = {
  me: () => request<User>('/api/auth/me'),
  login: (email: string, password: string) =>
    request<User>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (input: RegisterInput) =>
    request<User>('/api/auth/register', { method: 'POST', body: JSON.stringify(input) }),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
}
