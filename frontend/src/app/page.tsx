'use client'

import { useEffect, useState, useCallback } from 'react'
import { jobsApi } from '@/lib/api'
import { JobMatch, ApplicationStatus } from '@/types'
import {
  scoreColor, formatRelative, STATUS_LABELS, STATUS_PILL
} from '@/lib/utils'
import {
  ExternalLink, Bookmark, BookmarkCheck, X,
  Filter, ChevronDown, Info
} from 'lucide-react'

export default function JobsPage() {
  const [matches, setMatches]      = useState<JobMatch[]>([])
  const [loading, setLoading]      = useState(true)
  const [minScore, setMinScore]    = useState(60)
  const [savedOnly, setSavedOnly]  = useState(false)
  const [showDismissed, setShowDismissed] = useState(false)
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null)

  const fetchMatches = useCallback(async () => {
    setLoading(true)
    try {
      const data = await jobsApi.matches({
        min_score: minScore,
        saved_only: savedOnly,
        show_dismissed: showDismissed,
        limit: 100,
      }) as JobMatch[]
      setMatches(data)
    } finally {
      setLoading(false)
    }
  }, [minScore, savedOnly, showDismissed])

  useEffect(() => { fetchMatches() }, [fetchMatches])

  async function toggleSave(match: JobMatch, e: React.MouseEvent) {
    e.stopPropagation()
    if (match.is_saved) {
      await jobsApi.unsave(match.id)
    } else {
      await jobsApi.save(match.id)
    }
    setMatches(prev => prev.map(m =>
      m.id === match.id ? { ...m, is_saved: !m.is_saved } : m
    ))
  }

  async function dismiss(match: JobMatch, e: React.MouseEvent) {
    e.stopPropagation()
    await jobsApi.dismiss(match.id)
    setMatches(prev => prev.filter(m => m.id !== match.id))
  }

  async function updateAppStatus(jobId: string, status: ApplicationStatus) {
    await jobsApi.upsertApp(jobId, { status })
    setMatches(prev => prev.map(m =>
      m.job_id === jobId ? { ...m, application_status: status } : m
    ))
    if (selectedMatch?.job_id === jobId) {
      setSelectedMatch(prev => prev ? { ...prev, application_status: status } : null)
    }
  }

  return (
    <div className="flex h-full">
      {/* Main table */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="section-header">
          <h1 className="page-title">Job Matches</h1>
          <div className="flex items-center gap-3">
            {/* Min score filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-text-3" />
              <span className="text-xs text-text-3">Min score</span>
              <select
                value={minScore}
                onChange={e => setMinScore(Number(e.target.value))}
                className="bg-surface-3 border border-surface-4 rounded px-2 py-1 text-xs text-text-1"
              >
                {[50,60,70,80,90].map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>

            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={savedOnly}
                onChange={e => setSavedOnly(e.target.checked)}
                className="accent-accent-blue"
              />
              <span className="text-xs text-text-2">Saved only</span>
            </label>

            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={showDismissed}
                onChange={e => setShowDismissed(e.target.checked)}
                className="accent-accent-blue"
              />
              <span className="text-xs text-text-2">Show dismissed</span>
            </label>

            <span className="text-xs text-text-3 font-mono ml-1">
              {matches.length} results
            </span>
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="skeleton h-14 w-full" />
              ))}
            </div>
          ) : matches.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-text-3 text-sm">No matches found for the current filters.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead className="sticky top-0 bg-surface-1 z-10">
                <tr>
                  <th>Role</th>
                  <th>Score</th>
                  <th>Profile</th>
                  <th>Status</th>
                  <th>Seen</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {matches.map(m => (
                  <tr
                    key={m.id}
                    onClick={() => setSelectedMatch(m)}
                    className={selectedMatch?.id === m.id ? 'bg-surface-3' : ''}
                  >
                    <td className="min-w-[260px]">
                      <p className="text-text-1 font-medium text-sm">{m.title}</p>
                      <p className="text-text-3 text-2xs font-mono">
                        {m.company_name}
                        {m.location && ` · ${m.location}`}
                        {m.is_remote && ' · Remote'}
                      </p>
                    </td>
                    <td>
                      <ScoreBadge score={m.match_score} />
                    </td>
                    <td>
                      <span className="pill-muted text-2xs">{m.profile_name}</span>
                    </td>
                    <td>
                      <select
                        value={m.application_status}
                        onChange={e => updateAppStatus(m.job_id, e.target.value as ApplicationStatus)}
                        onClick={e => e.stopPropagation()}
                        className={`text-2xs px-2 py-0.5 rounded border font-mono cursor-pointer
                          bg-surface-3 border-surface-4 text-text-2`}
                      >
                        {STATUS_OPTIONS.map(s => (
                          <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                        ))}
                      </select>
                    </td>
                    <td className="text-text-3 text-2xs font-mono whitespace-nowrap">
                      {formatRelative(m.first_seen_at)}
                    </td>
                    <td>
                      <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                        <button
                          onClick={e => toggleSave(m, e)}
                          className="p-1 rounded hover:bg-surface-4 transition-colors"
                          title={m.is_saved ? 'Unsave' : 'Save'}
                        >
                          {m.is_saved
                            ? <BookmarkCheck className="w-3.5 h-3.5 text-accent-blue" />
                            : <Bookmark className="w-3.5 h-3.5 text-text-3 hover:text-text-2" />}
                        </button>
                        <a
                          href={m.application_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 rounded hover:bg-surface-4 transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5 text-text-3 hover:text-accent-blue" />
                        </a>
                        <button
                          onClick={e => dismiss(m, e)}
                          className="p-1 rounded hover:bg-surface-4 transition-colors"
                          title="Dismiss"
                        >
                          <X className="w-3.5 h-3.5 text-text-3 hover:text-red-400" />
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

      {/* Detail panel */}
      {selectedMatch && (
        <MatchDetailPanel
          match={selectedMatch}
          onClose={() => setSelectedMatch(null)}
          onStatusChange={updateAppStatus}
        />
      )}
    </div>
  )
}

// ── Detail panel ─────────────────────────────────────────────────────────────

function MatchDetailPanel({
  match, onClose, onStatusChange,
}: {
  match: JobMatch
  onClose: () => void
  onStatusChange: (jobId: string, status: ApplicationStatus) => void
}) {
  return (
    <aside className="w-[360px] shrink-0 border-l border-surface-4 bg-surface-2 flex flex-col overflow-y-auto animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between p-5 border-b border-surface-4">
        <div className="flex-1 min-w-0 pr-3">
          <h2 className="text-sm font-semibold text-text-1 leading-snug">{match.title}</h2>
          <p className="text-xs text-text-3 font-mono mt-0.5">{match.company_name}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-surface-4 shrink-0"
        >
          <X className="w-4 h-4 text-text-3" />
        </button>
      </div>

      <div className="p-5 space-y-5">
        {/* Score */}
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-center">
            <ScoreBadge score={match.match_score} large />
            <span className="text-2xs text-text-3 mt-1">match</span>
          </div>
          <div className="flex-1">
            <p className="text-xs text-text-2 leading-relaxed">{match.match_reason}</p>
          </div>
        </div>

        {/* Signals */}
        {match.matched_title_terms?.length > 0 && (
          <SignalRow label="Title signals" items={match.matched_title_terms} color="blue" />
        )}
        {match.matched_keywords?.length > 0 && (
          <SignalRow label="Keyword hits" items={match.matched_keywords} color="green" />
        )}
        {match.domain_signals_found?.length > 0 && (
          <SignalRow label="Domain signals" items={match.domain_signals_found} color="amber" />
        )}

        {/* Details */}
        <div className="space-y-2">
          <p className="text-2xs font-mono text-text-3 uppercase tracking-wider">Details</p>
          <DetailRow label="Location"  value={match.location || 'Not specified'} />
          <DetailRow label="Remote"    value={match.is_remote ? 'Yes' : match.is_remote === false ? 'No' : '—'} />
          <DetailRow label="Posted"    value={match.posted_at ? formatRelative(match.posted_at) : '—'} />
          <DetailRow label="Profile"   value={match.profile_name} />
        </div>

        {/* Status */}
        <div>
          <p className="text-2xs font-mono text-text-3 uppercase tracking-wider mb-2">
            Application Status
          </p>
          <select
            value={match.application_status}
            onChange={e => onStatusChange(match.job_id, e.target.value as ApplicationStatus)}
            className="input text-sm"
          >
            {STATUS_OPTIONS.map(s => (
              <option key={s} value={s}>{STATUS_LABELS[s]}</option>
            ))}
          </select>
        </div>

        {/* CTA */}
        <a
          href={match.application_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary w-full justify-center"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Apply Now
        </a>
      </div>
    </aside>
  )
}

// ── Micro-components ─────────────────────────────────────────────────────────

function ScoreBadge({ score, large }: { score: number; large?: boolean }) {
  const color = scoreColor(score)
  const size  = large ? 'w-14 h-14 text-sm' : 'w-9 h-9 text-2xs'
  return (
    <span
      className={`score-badge font-mono ${size}`}
      style={{ color, borderColor: `${color}40` }}
    >
      {score}
    </span>
  )
}

function SignalRow({ label, items, color }: { label: string; items: string[]; color: string }) {
  const pill = `pill-${color}`
  return (
    <div>
      <p className="text-2xs text-text-3 mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-1">
        {items.slice(0, 8).map(t => (
          <span key={t} className={pill}>{t}</span>
        ))}
      </div>
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-text-3">{label}</span>
      <span className="text-xs text-text-2 font-mono">{value}</span>
    </div>
  )
}
