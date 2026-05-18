'use client'
import { useEffect, useState } from 'react'
import { ingestionApi } from '@/lib/api'
import { IngestionRun } from '@/types'
import { formatRelative } from '@/lib/utils'
import { RefreshCw, ChevronDown, ChevronRight, AlertCircle, CheckCircle, Clock } from 'lucide-react'

export default function LogsPage() {
  const [runs, setRuns]       = useState<IngestionRun[]>([])
  const [errors, setErrors]   = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [runDetails, setRunDetails] = useState<Record<string, any>>({})
  const [tab, setTab] = useState<'runs' | 'errors'>('runs')

  useEffect(() => {
    Promise.all([
      ingestionApi.runs(30) as Promise<IngestionRun[]>,
      ingestionApi.errors(30) as Promise<any[]>,
    ]).then(([r, e]) => {
      setRuns(r)
      setErrors(e)
    }).finally(() => setLoading(false))
  }, [])

  async function toggleExpand(runId: string) {
    if (expanded === runId) { setExpanded(null); return }
    setExpanded(runId)
    if (!runDetails[runId]) {
      const detail = await ingestionApi.getRun(runId) as any
      setRunDetails(prev => ({ ...prev, [runId]: detail }))
    }
  }

  const statusIcon: Record<string, React.ReactNode> = {
    completed: <CheckCircle className="w-3.5 h-3.5 text-green-400" />,
    completed_with_errors: <AlertCircle className="w-3.5 h-3.5 text-amber-400" />,
    failed: <AlertCircle className="w-3.5 h-3.5 text-red-400" />,
    running: <RefreshCw className="w-3.5 h-3.5 text-blue-400 animate-spin" />,
  }

  return (
    <div className="flex flex-col h-full">
      <div className="section-header">
        <h1 className="page-title">Ingestion Logs</h1>
        <div className="flex gap-1">
          {(['runs', 'errors'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded text-xs transition-colors ${
                tab === t
                  ? 'bg-accent-blue/10 text-accent-blue border border-accent-blue/30'
                  : 'text-text-3 hover:text-text-1 hover:bg-surface-3'
              }`}
            >
              {t === 'runs' ? `Runs (${runs.length})` : `Errors (${errors.length})`}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-6 space-y-2">
            {Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton h-12 w-full" />)}
          </div>
        ) : tab === 'runs' ? (
          runs.length === 0 ? (
            <div className="p-12 text-center text-text-3 text-sm">No ingestion runs yet.</div>
          ) : (
            <div className="divide-y divide-surface-4">
              {runs.map(run => (
                <div key={run.id}>
                  <button
                    onClick={() => toggleExpand(run.id)}
                    className="w-full flex items-center gap-4 px-6 py-3 hover:bg-surface-3/50 transition-colors text-left"
                  >
                    {statusIcon[run.status] ?? <Clock className="w-3.5 h-3.5 text-text-3" />}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono text-text-3">
                          {new Date(run.started_at).toLocaleString()}
                        </span>
                        <span className="text-2xs text-text-3">{run.triggered_by}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs font-mono">
                      <span className="text-text-3">{run.companies_checked} co.</span>
                      <span className="text-accent-blue">{run.new_jobs_found} new</span>
                      <span className="text-green-400">{run.matches_found} matches</span>
                      {run.error_count > 0 && (
                        <span className="text-red-400">{run.error_count} err</span>
                      )}
                      {run.duration_seconds != null && (
                        <span className="text-text-3">{run.duration_seconds.toFixed(0)}s</span>
                      )}
                    </div>
                    {expanded === run.id
                      ? <ChevronDown className="w-3.5 h-3.5 text-text-3 ml-2 shrink-0" />
                      : <ChevronRight className="w-3.5 h-3.5 text-text-3 ml-2 shrink-0" />}
                  </button>

                  {expanded === run.id && (
                    <div className="bg-surface-2 px-6 pb-4">
                      {!runDetails[run.id] ? (
                        <div className="py-3 flex items-center gap-2 text-xs text-text-3">
                          <RefreshCw className="w-3 h-3 animate-spin" /> Loading details…
                        </div>
                      ) : (
                        <div className="pt-2">
                          <table className="data-table text-xs">
                            <thead>
                              <tr>
                                <th>Company</th>
                                <th>Status</th>
                                <th>Jobs Found</th>
                                <th>New</th>
                                <th>Matches</th>
                                <th>Duration</th>
                                <th>Error</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(runDetails[run.id].check_logs ?? []).map((log: any) => (
                                <tr key={log.company_id}>
                                  <td className="text-text-1">{log.company_name}</td>
                                  <td>
                                    <span className={`pill text-2xs ${
                                      log.status === 'success' ? 'pill-green'
                                      : log.status === 'failed' ? 'pill-red'
                                      : 'pill-amber'
                                    }`}>{log.status}</span>
                                  </td>
                                  <td className="font-mono">{log.jobs_found}</td>
                                  <td className="font-mono text-accent-blue">{log.new_jobs_found}</td>
                                  <td className="font-mono text-green-400">{log.matches_found}</td>
                                  <td className="font-mono text-text-3">
                                    {log.duration_seconds != null ? `${log.duration_seconds.toFixed(1)}s` : '—'}
                                  </td>
                                  <td className="text-red-400 text-2xs max-w-[200px] truncate">
                                    {log.error_message ?? '—'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )
        ) : (
          // Errors tab
          errors.length === 0 ? (
            <div className="p-12 text-center text-text-3 text-sm">No errors recorded.</div>
          ) : (
            <table className="data-table">
              <thead className="sticky top-0 bg-surface-1 z-10">
                <tr>
                  <th>Time</th>
                  <th>Company</th>
                  <th>Type</th>
                  <th>HTTP</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {errors.map((e: any) => (
                  <tr key={e.id}>
                    <td className="text-text-3 text-2xs font-mono whitespace-nowrap">
                      {formatRelative(e.occurred_at)}
                    </td>
                    <td className="text-text-1 text-xs">{e.company_name}</td>
                    <td><span className="pill-red text-2xs">{e.error_type}</span></td>
                    <td className="font-mono text-xs text-text-3">{e.http_status ?? '—'}</td>
                    <td className="text-text-2 text-xs max-w-[320px] truncate">{e.error_message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
      </div>
    </div>
  )
}
