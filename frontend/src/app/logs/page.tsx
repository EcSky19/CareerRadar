'use client'
import { useEffect, useState } from 'react'
import { ingestionApi, companiesApi } from '@/lib/api'
import { IngestionRun } from '@/types'
import { formatRelative } from '@/lib/utils'
import { RefreshCw, ChevronDown, ChevronRight, AlertCircle, CheckCircle, Clock, Wrench } from 'lucide-react'

const ERROR_FIXES: Record<string, string> = {
  '404': 'Wrong ATS slug or company moved to a different ATS platform',
  '401': 'ATS requires authentication — public API not available',
  '403': 'Access denied — company blocks automated access',
  '429': 'Rate limited — too many requests',
  '526': 'SSL error on careers page',
  'bot': 'Bot detection — company uses Cloudflare or similar protection',
  'workday': 'Workday blocks public API access — no fix available',
  'timeout': 'Server too slow to respond',
}

function getErrorType(msg: string): string {
  if (!msg) return 'unknown'
  if (msg.includes('404')) return '404'
  if (msg.includes('401')) return '401'
  if (msg.includes('403')) return '403'
  if (msg.includes('429')) return '429'
  if (msg.includes('526')) return '526'
  if (msg.toLowerCase().includes('bot')) return 'bot'
  if (msg.toLowerCase().includes('workday') || msg.toLowerCase().includes('wd5')) return 'workday'
  if (msg.toLowerCase().includes('timeout')) return 'timeout'
  return 'unknown'
}

function getErrorColor(type: string): string {
  if (type === '404' || type === 'bot' || type === 'workday') return 'pill-amber'
  if (type === '401' || type === '403') return 'pill-red'
  return 'pill-red'
}

export default function LogsPage() {
  const [runs, setRuns]       = useState<IngestionRun[]>([])
  const [errors, setErrors]   = useState<any[]>([])
  const [companies, setCompanies] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [runDetails, setRunDetails] = useState<Record<string, any>>({})
  const [tab, setTab] = useState<'runs' | 'errors' | 'companies'>'runs'')

  useEffect(() => {
    Promise.all([
      ingestionApi.runs(30) as Promise<IngestionRun[]>,
      ingestionApi.errors(50) as Promise<any[]>,
      companiesApi.list() as Promise<any[]>,
    ]).then(([r, e, c]) => {
      setRuns(r)
      setErrors(e)
      setCompanies(c)
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

  const companiesWithErrors = companies.filter((c: any) => c.consecutive_errors > 0)
    .sort((a: any, b: any) => b.consecutive_errors - a.consecutive_errors)

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
          {(['runs', 'errors', 'companies'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded text-xs transition-colors ${
                tab === t
                  ? 'bg-accent-blue/10 text-accent-blue border border-accent-blue/30'
                  : 'text-text-3 hover:text-text-1 hover:bg-surface-3'
              }`}
            >
              {t === 'runs' ? `Runs (${runs.length})`
               : t === 'errors' ? `Errors (${errors.length})`
               : `Problem Companies (${companiesWithErrors.length})`}
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
        ) : tab === 'errors' ? (
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
        ) : (
          // Problem Companies tab
          companiesWithErrors.length === 0 ? (
            <div className="p-12 text-center text-text-3 text-sm">All companies scanning cleanly!</div>
          ) : (
            <div className="divide-y divide-surface-4">
              <div className="px-6 py-3 bg-surface-2 text-xs text-text-3 flex items-center gap-2">
                <Wrench className="w-3.5 h-3.5" />
                <span>{companiesWithErrors.length} companies have recurring errors. These affect job coverage but do not break the platform.</span>
              </div>
              {companiesWithErrors.map((c: any) => {
                const errType = getErrorType(c.last_error || '')
                const fix = ERROR_FIXES[errType] || 'Unknown error — check error logs'
                return (
                  <div key={c.id} className="px-6 py-4 hover:bg-surface-3/30">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium text-text-1">{c.name}</span>
                          <span className={`pill text-2xs ${getErrorColor(errType)}`}>{errType}</span>
                          <span className="text-2xs text-text-3 font-mono">{c.ats_provider}</span>
                          <span className="text-2xs text-red-400 font-mono">{c.consecutive_errors} errors</span>
                        </div>
                        <p className="text-xs text-text-3 mb-1">{c.last_error?.slice(0, 100)}</p>
                        <p className="text-xs text-amber-400 flex items-center gap-1">
                          <Wrench className="w-3 h-3" /> {fix}
                        </p>
                      </div>
                      <a href={c.careers_url} target="_blank" rel="noopener noreferrer"
                        className="text-2xs text-accent-blue hover:underline shrink-0">
                        Visit careers page →
                      </a>
                    </div>
                  </div>
                )
              })}
            </div>
          )
        )}
      </div>
    </div>
  )
}
