const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1'

async function getToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null
  try {
    const projectRef = process.env.NEXT_PUBLIC_SUPABASE_URL?.split('//')[1]?.split('.')[0]
    if (projectRef) {
      const raw = localStorage.getItem(`sb-${projectRef}-auth-token`)
      if (raw) {
        const session = JSON.parse(raw)
        if (session?.access_token) return session.access_token
      }
    }
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && (key.includes('auth-token') || key.includes('supabase'))) {
        const raw = localStorage.getItem(key)
        if (raw) {
          const parsed = JSON.parse(raw)
          const token = parsed?.access_token
            ?? parsed?.session?.access_token
            ?? parsed?.data?.session?.access_token
          if (token) return token
        }
      }
    }
  } catch { }
  return null
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return null as T
  }
  const text = await res.text()
  if (!text) return null as T
  return JSON.parse(text)
}

async function upload<T>(path: string, file: File, params?: Record<string, string>): Promise<T> {
  const token = await getToken()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return null as T
  }
  const text = await res.text()
  if (!text) return null as T
  return JSON.parse(text)
}

export const companiesApi = {
  list:       (p?: Record<string, unknown>) => request<any>(`/companies?${new URLSearchParams((p ?? {}) as Record<string, string>)}`),
  get:        (id: string)                  => request<any>(`/companies/${id}`),
  create:     (data: unknown)               => request<any>('/companies', { method: 'POST', body: JSON.stringify(data) }),
  update:     (id: string, data: unknown)   => request<any>(`/companies/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete:     (id: string)                  => request<any>(`/companies/${id}`, { method: 'DELETE' }),
  categories: ()                            => request<any[]>('/companies/categories/all'),
  detectAts:  (data: unknown)               => request<any>('/companies/detect-ats', { method: 'POST', body: JSON.stringify(data) }),
  pause:      (id: string)                  => request<any>(`/companies/${id}/pause`, { method: 'POST' }),
  activate:   (id: string)                  => request<any>(`/companies/${id}/activate`, { method: 'POST' }),
  scan:       (id: string)                  => request<any>(`/companies/${id}/scan`, { method: 'POST' }),
}

export const profilesApi = {
  list:      (p?: Record<string, unknown>) => request<any[]>(`/target-profiles?${new URLSearchParams((p ?? {}) as Record<string, string>)}`),
  get:       (id: string)                => request<any>(`/target-profiles/${id}`),
  create:    (data: unknown)             => request<any>('/target-profiles', { method: 'POST', body: JSON.stringify(data) }),
  update:    (id: string, data: unknown) => request<any>(`/target-profiles/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete:    (id: string)                => request<any>(`/target-profiles/${id}`, { method: 'DELETE' }),
  duplicate: (id: string)                => request<any>(`/target-profiles/${id}/duplicate`, { method: 'POST' }),
}

export const jobsApi = {
  matches:   (p?: Record<string, unknown>) => request<any[]>(`/jobs/matches?${new URLSearchParams((p ?? {}) as Record<string, string>)}`),
  stats:     ()                            => request<any>('/jobs/matches/stats'),
  tracker:   (p?: Record<string, unknown>) => request<any[]>(`/jobs/tracker?${new URLSearchParams((p ?? {}) as Record<string, string>)}`),
  save:      (id: string)                  => request<any>(`/jobs/matches/${id}/save`, { method: 'POST' }),
  unsave:    (id: string)                  => request<any>(`/jobs/matches/${id}/save`, { method: 'DELETE' }),
  dismiss:   (id: string)                  => request<any>(`/jobs/matches/${id}/dismiss`, { method: 'POST' }),
  upsertApp: (jobId: string, data: unknown)=> request<any>(`/jobs/${jobId}/application`, { method: 'PUT', body: JSON.stringify(data) }),
}

export const ingestionApi = {
  run:        ()           => request<any>('/ingestion/run', { method: 'POST' }),
  triggerRun: ()           => request<any>('/ingestion/run', { method: 'POST' }),
  runs:       (limit = 20) => request<any[]>(`/ingestion/runs?limit=${limit}`),
  logs:       (limit = 20) => request<any[]>(`/ingestion/runs?limit=${limit}`),
  errors:     (limit = 30) => request<any[]>(`/ingestion/errors?limit=${limit}`),
  getRun:     (id: string) => request<any>(`/ingestion/runs/${id}`),
}

export const alertsApi = {
  list: () => request<any[]>('/alerts'),
}

export const resumesApi = {
  list:     ()                                => request<any[]>('/resumes'),
  upload:   (file: File, name?: string, isBase?: boolean) => upload<any>('/resumes/upload', file, name ? { name, is_base: String(isBase ?? false) } : undefined),
  analyze:  (resumeId: string, data: unknown) => request<any>(`/resumes/${resumeId}/analyze`, { method: 'POST', body: JSON.stringify(data) }),
  optimize: (resumeId: string, analysisId: string, name?: string) => request<any>(`/resumes/${resumeId}/optimize`, { method: 'POST', body: JSON.stringify({ analysis_id: analysisId, name }) }),
}

export const usersApi = {
  me:     ()              => request<any>('/users/me'),
  update: (data: unknown) => request<any>('/users/me', { method: 'PATCH', body: JSON.stringify(data) }),
}
