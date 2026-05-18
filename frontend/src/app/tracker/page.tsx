// src/app/tracker/page.tsx
'use client'
import { useEffect, useState } from 'react'
import { jobsApi } from '@/lib/api'
import { TrackedApplication, ApplicationStatus } from '@/types'
import { formatRelative, STATUS_LABELS, STATUS_PILL } from '@/lib/utils'
import { ExternalLink } from 'lucide-react'

const COLUMNS: ApplicationStatus[] = ['saved', 'applied', 'interview', 'offer', 'rejected']

export default function TrackerPage() {
  const [apps, setApps] = useState<TrackedApplication[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    jobsApi.tracker().then((d: any) => setApps(d)).finally(() => setLoading(false))
  }, [])

  async function updateStatus(app: TrackedApplication, newStatus: ApplicationStatus) {
    await jobsApi.upsertApp(app.job_id, { status: newStatus })
    setApps(prev => prev.map(a => a.id === app.id ? { ...a, status: newStatus } : a))
  }

  const filtered = filter === 'all' ? apps : apps.filter(a => a.status === filter)
  const countFor = (s: string) => apps.filter(a => a.status === s).length

  return (
    <div className="flex flex-col h-full">
      <div className="section-header">
        <h1 className="page-title">Application Tracker</h1>
        <div className="flex gap-1">
          {['all', ...COLUMNS].map(s => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-1 rounded text-xs transition-colors ${
                filter === s
                  ? 'bg-accent-blue/10 text-accent-blue border border-accent-blue/30'
                  : 'text-text-3 hover:text-text-1 hover:bg-surface-3'
              }`}
            >
              {STATUS_LABELS[s] ?? 'All'}
              {s !== 'all' && <span className="ml-1 font-mono text-text-3">({countFor(s)})</span>}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-6 space-y-2">
            {Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton h-14 w-full" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-text-3 text-sm">No applications in this stage.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead className="sticky top-0 bg-surface-1 z-10">
              <tr>
                <th>Role</th>
                <th>Status</th>
                <th>Applied</th>
                <th>Follow-up</th>
                <th>Notes</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(app => (
                <tr key={app.id}>
                  <td>
                    <p className="text-text-1 font-medium text-sm">{app.title}</p>
                    <p className="text-text-3 text-2xs font-mono">{app.company_name}</p>
                  </td>
                  <td>
                    <select
                      value={app.status}
                      onChange={e => updateStatus(app, e.target.value as ApplicationStatus)}
                      className="bg-surface-3 border border-surface-4 rounded px-2 py-0.5 text-xs text-text-1"
                    >
                      {COLUMNS.map(s => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
                    </select>
                  </td>
                  <td className="text-text-3 text-xs font-mono">
                    {app.applied_at ? formatRelative(app.applied_at) : '—'}
                  </td>
                  <td className="text-text-3 text-xs font-mono">{app.follow_up_date ?? '—'}</td>
                  <td className="max-w-[200px]">
                    <p className="text-text-3 text-xs truncate">{app.notes ?? '—'}</p>
                  </td>
                  <td>
                    <a href={app.application_url} target="_blank" rel="noopener noreferrer"
                      className="text-accent-blue hover:text-blue-400">
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
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
