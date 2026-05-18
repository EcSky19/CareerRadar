/**
 * API client for Personal Job Hunter backend.
 * All requests are authenticated via Supabase JWT from localStorage.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1'

async function getToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null
  // Supabase stores the session in localStorage
  const raw = localStorage.getItem(
    `sb-${process.env.NEXT_PUBLIC_SUPABASE_URL?.split('//')[1]?.split('.')[0]}-auth-token`
  )
  if (!raw) return null
  try {
    const session = JSON.parse(raw)
    return session?.access_token ?? null
  } catch {
    return null
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = await getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  })

  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const err = await res.json()
      message = err.detail ?? message
    } catch {}
    throw new Error(message)
  }

  if (res.status === 204) return undefined as unknown as T
  return res.json()
}

// ── Typed helpers ──────────────────────────────────────────────────────────────

const get  = <T>(path: string)                      => request<T>(path)
const post = <T>(path: string, body?: unknown)       => request<T>(path, { method: 'POST',  body: body ? JSON.stringify(body) : undefined })
const patch = <T>(path: string, body?: unknown)      => request<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined })
const put  = <T>(path: string, body?: unknown)       => request<T>(path, { method: 'PUT',   body: body ? JSON.stringify(body) : undefined })
const del  = <T>(path: string)                      => request<T>(path, { method: 'DELETE' })


// ── Users ──────────────────────────────────────────────────────────────────────
export const usersApi = {
  me:     ()      => get('/users/me'),
  update: (body: unknown) => patch('/users/me', body),
}


// ── Companies ─────────────────────────────────────────────────────────────────
export const companiesApi = {
  list:       (activeOnly = false) => get(`/companies?active_only=${activeOnly}`),
  get:        (id: string)         => get(`/companies/${id}`),
  create:     (body: unknown)      => post('/companies', body),
  update:     (id: string, body: unknown) => patch(`/companies/${id}`, body),
  delete:     (id: string)         => del(`/companies/${id}`),
  pause:      (id: string)         => post(`/companies/${id}/pause`),
  activate:   (id: string)         => post(`/companies/${id}/activate`),
  test:       (id: string)         => post(`/companies/${id}/test`),
  detectAts:  (body: unknown)      => post('/companies/detect-ats', body),
  categories: ()                   => get('/companies/categories/all'),
}


// ── Target Profiles ────────────────────────────────────────────────────────────
export const profilesApi = {
  list:      (activeOnly = true) => get(`/target-profiles?active_only=${activeOnly}`),
  get:       (id: string)        => get(`/target-profiles/${id}`),
  create:    (body: unknown)     => post('/target-profiles', body),
  update:    (id: string, body: unknown) => patch(`/target-profiles/${id}`, body),
  delete:    (id: string)        => del(`/target-profiles/${id}`),
  duplicate: (id: string)        => post(`/target-profiles/${id}/duplicate`),
}


// ── Jobs ───────────────────────────────────────────────────────────────────────
export const jobsApi = {
  matches:   (params?: Record<string, unknown>) => {
    const qs = params ? '?' + new URLSearchParams(params as any).toString() : ''
    return get(`/jobs/matches${qs}`)
  },
  stats:     ()                 => get('/jobs/matches/stats'),
  getJob:    (id: string)       => get(`/jobs/${id}`),
  save:      (matchId: string)  => post(`/jobs/matches/${matchId}/save`),
  dismiss:   (matchId: string)  => post(`/jobs/matches/${matchId}/dismiss`),
  unsave:    (matchId: string)  => post(`/jobs/matches/${matchId}/unsave`),
  upsertApp: (jobId: string, body: unknown) => put(`/jobs/${jobId}/application`, body),
  tracker:   (statusFilter?: string) => {
    const qs = statusFilter ? `?status_filter=${statusFilter}` : ''
    return get(`/jobs/tracker/all${qs}`)
  },
}


// ── Ingestion ─────────────────────────────────────────────────────────────────
export const ingestionApi = {
  triggerRun:     ()           => post('/ingestion/run'),
  triggerCompany: (id: string) => post(`/ingestion/run/company/${id}`),
  runs:           (limit = 20) => get(`/ingestion/runs?limit=${limit}`),
  getRun:         (id: string) => get(`/ingestion/runs/${id}`),
  errors:         (limit = 50) => get(`/ingestion/errors?limit=${limit}`),
}


// ── Alerts ────────────────────────────────────────────────────────────────────
export const alertsApi = {
  list:  (limit = 50) => get(`/alerts?limit=${limit}`),
  stats: ()           => get('/alerts/stats'),
}


// ── Resumes ───────────────────────────────────────────────────────────────────
export const resumesApi = {
  list:      ()                  => get('/resumes'),
  get:       (id: string)        => get(`/resumes/${id}`),
  analyses:  (id: string)        => get(`/resumes/${id}/analyses`),
  versions:  (id: string)        => get(`/resumes/${id}/versions`),
  analyze:   (id: string, body: unknown) => post(`/resumes/${id}/analyze`, body),
  optimize:  (resumeId: string, analysisId: string, versionName?: string) =>
    post(`/resumes/${resumeId}/optimize/${analysisId}?version_name=${encodeURIComponent(versionName ?? 'Optimized Version')}`),

  upload: async (file: File, name: string, isBase: boolean) => {
    const token = await getToken()
    const form = new FormData()
    form.append('file', file)
    form.append('name', name)
    form.append('is_base', String(isBase))

    const res = await fetch(`${API_BASE}/resumes/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    })
    if (!res.ok) throw new Error(`Upload failed: HTTP ${res.status}`)
    return res.json()
  },
}
