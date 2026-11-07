/**
 * 後端 API 用戶端（microservice/backend，規格書 docs/backend-spec.md §7）。
 *
 * - 網址：環境變數 VITE_API_BASE；沒有設定時用「目前網頁的主機:8000」，
 *   所以電腦瀏覽器（localhost:5173）連 localhost:8000、模擬器（10.0.2.2:5173）連 10.0.2.2:8000。
 * - 長者、家屬、救護人員各自有自己的登入憑證，存在 localStorage，重新整理後仍可使用。
 */

export type Role = 'elder' | 'family' | 'rescue'

function defaultBase(): string {
  const host = typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : 'localhost'
  return `http://${host}:8000/api/v1`
}

export const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined) || defaultBase()

const TOKEN_KEY = 'chiah-ioh-lo-tokens'

/** 後端回傳的業務錯誤（{ error: { code, message } }），或連不到後端 */
export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message)
  }
}

function readTokens(): Partial<Record<Role, string>> {
  try {
    return JSON.parse(window.localStorage.getItem(TOKEN_KEY) ?? '{}') as Partial<Record<Role, string>>
  } catch {
    return {}
  }
}

export function getToken(role: Role): string | undefined {
  return readTokens()[role]
}

export function setToken(role: Role, token: string | null): void {
  const tokens = readTokens()
  if (token) tokens[role] = token
  else delete tokens[role]
  try {
    window.localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens))
  } catch {
    /* 無痕模式或儲存被封鎖時忽略：只是重新整理後要重新登入 */
  }
}

interface RequestOptions {
  role?: Role
  signal?: AbortSignal
  body?: unknown
  query?: Record<string, string | undefined>
}

export async function api<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(`${API_BASE}${path}`)
  Object.entries(options.query ?? {}).forEach(([k, v]) => {
    if (v !== undefined) url.searchParams.set(k, v)
  })
  const headers: Record<string, string> = {}
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  const token = options.role ? getToken(options.role) : undefined
  if (token) headers.Authorization = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers,
      signal: options.signal,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
  } catch (e) {
    if (options.signal?.aborted) throw e
    throw new ApiError('NETWORK', '連不到伺服器，請確認後端已啟動、網路正常', 0)
  }
  if (res.status === 204) return undefined as T
  const data = (await res.json().catch(() => null)) as { error?: { code: string; message: string } } | null
  if (!res.ok) {
    if (res.status === 401 && options.role) setToken(options.role, null)
    throw new ApiError(data?.error?.code ?? 'HTTP_ERROR', data?.error?.message ?? `伺服器錯誤（${res.status}）`, res.status)
  }
  return data as T
}

export const get = <T>(path: string, options?: RequestOptions) => api<T>('GET', path, options)
export const post = <T>(path: string, body?: unknown, options?: RequestOptions) =>
  api<T>('POST', path, { ...options, body: body ?? {} })
export const put = <T>(path: string, body: unknown, options?: RequestOptions) => api<T>('PUT', path, { ...options, body })
export const patch = <T>(path: string, body: unknown, options?: RequestOptions) =>
  api<T>('PATCH', path, { ...options, body })
export const del = <T>(path: string, options?: RequestOptions) => api<T>('DELETE', path, options)
