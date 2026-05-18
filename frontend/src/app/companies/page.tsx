'use client'

import { useEffect, useState } from 'react'
import { companiesApi } from '@/lib/api'
import { Company } from '@/types'
import { formatRelative, PROVIDER_LABELS } from '@/lib/utils'
import {
  Plus, Pause, Play, Trash2, RefreshCw, X,
  CheckCircle, AlertCircle, Wand2
} from 'lucide-react'

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading]      = useState(true)
  const [showForm, setShowForm]    = useState(false)
  const [detecting, setDetecting]  = useState(false)

  // Form state
  const [form, setForm] = useState({
    name: '', careers_url: '', ats_provider: 'unknown',
    ats_slug: '', priority: 'medium', notes: '', category_ids: [] as string[],
  })
  const [detectResult, setDetectResult] = useState<any>(null)

  useEffect(() => {
    Promise.all([
      companiesApi.list() as Promise<Company[]>,
      companiesApi.categories() as Promise<any[]>,
    ]).then(([c, cats]) => {
      setCompanies(c)
      setCategories(cats)
    }).finally(() => setLoading(false))
  }, [])

  async function detectAts() {
    if (!form.careers_url) return
    setDetecting(true)
    try {
      const result = await companiesApi.detectAts({
        careers_url: form.careers_url,
        company_name: form.name,
      }) as any
      setDetectResult(result)
      setForm(f => ({
        ...f,
        ats_provider: result.provider_name,
        ats_slug: result.required_slug_or_token ?? f.ats_slug,
      }))
    } finally { setDetecting(false) }
  }

  async function createCompany() {
    const company = await companiesApi.create(form) as Company
    setCompanies(prev => [company, ...prev])
    setShowForm(false)
    setForm({ name: '', careers_url: '', ats_provider: 'unknown',
              ats_slug: '', priority: 'medium', notes: '', category_ids: [] })
    setDetectResult(null)
  }

  async function toggleActive(company: Company) {
    if (company.is_active) {
      await companiesApi.pause(company.id)
    } else {
      await companiesApi.activate(company.id)
    }
    setCompanies(prev => prev.map(c =>
      c.id === company.id ? { ...c, is_active: !c.is_active } : c
    ))
  }

  async function deleteCompany(id: string) {
    if (!confirm('Delete this company and all its job data?')) return
    await companiesApi.delete(id)
    setCompanies(prev => prev.filter(c => c.id !== id))
  }

  const PRIORITY_PILL: Record<string, string> = {
    high: 'pill-red', medium: 'pill-amber', low: 'pill-muted',
  }

  return (
    <div className="flex flex-col h-full">
      <div className="section-header">
        <h1 className="page-title">Companies <span className="text-text-3 font-normal text-sm ml-1">({companies.length})</span></h1>
        <button onClick={() => setShowForm(true)} className="btn-primary">
          <Plus className="w-3.5 h-3.5" /> Add Company
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <div className="border-b border-surface-4 bg-surface-2 p-5">
          <div className="max-w-2xl space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-text-3 mb-1 block">Company Name *</label>
                <input className="input" placeholder="Stripe" value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-text-3 mb-1 block">Priority</label>
                <select className="input" value={form.priority}
                  onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
                  {['high', 'medium', 'low'].map(p => (
                    <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-2">
              <input className="input flex-1" placeholder="https://stripe.com/jobs"
                value={form.careers_url}
                onChange={e => setForm(f => ({ ...f, careers_url: e.target.value }))} />
              <button onClick={detectAts} disabled={detecting || !form.careers_url} className="btn-ghost">
                {detecting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
                Detect ATS
              </button>
            </div>

            {detectResult && (
              <div className={`flex items-start gap-2 p-3 rounded border text-xs
                ${detectResult.provider_name !== 'unknown'
                  ? 'bg-green-500/5 border-green-500/20 text-green-400'
                  : 'bg-amber-500/5 border-amber-500/20 text-amber-400'}`}>
                {detectResult.provider_name !== 'unknown'
                  ? <CheckCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  : <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />}
                <div>
                  <p>
                    Detected: <strong>{PROVIDER_LABELS[detectResult.provider_name]}</strong>
                    {detectResult.required_slug_or_token && ` · slug: ${detectResult.required_slug_or_token}`}
                    {` · ${Math.round(detectResult.confidence_score * 100)}% confidence`}
                  </p>
                  {detectResult.warning_message && (
                    <p className="text-text-3 mt-0.5">{detectResult.warning_message}</p>
                  )}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-text-3 mb-1 block">ATS Provider</label>
                <select className="input" value={form.ats_provider}
                  onChange={e => setForm(f => ({ ...f, ats_provider: e.target.value }))}>
                  {Object.entries(PROVIDER_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-text-3 mb-1 block">Board Token / Slug</label>
                <input className="input font-mono" placeholder="e.g. stripe"
                  value={form.ats_slug}
                  onChange={e => setForm(f => ({ ...f, ats_slug: e.target.value }))} />
              </div>
            </div>

            {/* Category multiselect */}
            <div>
              <label className="text-xs text-text-3 mb-1.5 block">Categories</label>
              <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto p-2 bg-surface-3 border border-surface-4 rounded">
                {categories.map(cat => {
                  const selected = form.category_ids.includes(cat.id)
                  return (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => setForm(f => ({
                        ...f,
                        category_ids: selected
                          ? f.category_ids.filter(id => id !== cat.id)
                          : [...f.category_ids, cat.id],
                      }))}
                      className={`pill cursor-pointer transition-colors ${selected ? 'pill-blue' : 'pill-muted'}`}
                    >
                      {cat.name}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="flex gap-2 pt-1">
              <button onClick={createCompany} disabled={!form.name} className="btn-primary">
                Add Company
              </button>
              <button onClick={() => { setShowForm(false); setDetectResult(null) }} className="btn-ghost">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-6 space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="skeleton h-14 w-full" />
            ))}
          </div>
        ) : companies.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <p className="text-text-2">No companies yet.</p>
            <p className="text-text-3 text-sm">Add companies to start monitoring their job boards.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead className="sticky top-0 bg-surface-1 z-10">
              <tr>
                <th>Company</th>
                <th>ATS</th>
                <th>Categories</th>
                <th>Priority</th>
                <th>Jobs</th>
                <th>Last Check</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {companies.map(c => (
                <tr key={c.id}>
                  <td>
                    <p className="text-text-1 font-medium text-sm">{c.name}</p>
                    {c.consecutive_errors > 0 && (
                      <p className="text-red-400 text-2xs mt-0.5 font-mono">
                        {c.consecutive_errors} errors · {c.last_error?.slice(0, 40)}
                      </p>
                    )}
                  </td>
                  <td>
                    <span className="pill-muted font-mono text-2xs">
                      {PROVIDER_LABELS[c.ats_provider]}
                    </span>
                  </td>
                  <td>
                    <div className="flex flex-wrap gap-1">
                      {c.categories.slice(0, 2).map(cat => (
                        <span key={cat.id} className="pill-muted text-2xs">{cat.name}</span>
                      ))}
                      {c.categories.length > 2 && (
                        <span className="pill-muted text-2xs">+{c.categories.length - 2}</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className={PRIORITY_PILL[c.priority]}>{c.priority}</span>
                  </td>
                  <td className="font-mono text-xs">
                    <span className="text-text-1">{c.total_jobs_found}</span>
                    <span className="text-text-3"> / {c.total_matching_jobs} matched</span>
                  </td>
                  <td className="text-text-3 text-xs font-mono">
                    {c.last_checked_at ? formatRelative(c.last_checked_at) : '—'}
                  </td>
                  <td>
                    <div className={`w-2 h-2 rounded-full ${c.is_active ? 'bg-green-400' : 'bg-surface-5'}`} />
                  </td>
                  <td>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => toggleActive(c)}
                        className="p-1 rounded hover:bg-surface-4 transition-colors"
                        title={c.is_active ? 'Pause' : 'Activate'}
                      >
                        {c.is_active
                          ? <Pause className="w-3.5 h-3.5 text-text-3 hover:text-amber-400" />
                          : <Play className="w-3.5 h-3.5 text-text-3 hover:text-green-400" />}
                      </button>
                      <button
                        onClick={() => deleteCompany(c.id)}
                        className="p-1 rounded hover:bg-surface-4 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-text-3 hover:text-red-400" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
