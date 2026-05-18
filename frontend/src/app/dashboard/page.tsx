'use client'

import { useEffect, useState } from 'react'
import { jobsApi, ingestionApi, companiesApi } from '@/lib/api'
import { MatchStats, JobMatch, IngestionRun } from '@/types'
import { scoreColor, formatRelative, PROVIDER_LABELS } from '@/lib/utils'
import {
  Briefcase, TrendingUp, Bell, Play, RefreshCw,
  ExternalLink, ChevronRight, Building2
} from 'lucide-react'
import Link from 'next/link'

export default function DashboardPage() {
  const [stats, setStats]         = useState<MatchStats | null>(null)
  const [matches, setMatches]     = useState<JobMatch[]>([])
  const [lastRun, setLastRun]     = useState<IngestionRun | null>(null)
  const [running, setRunning]     = useState(false)
  const [loading, setLoading]     = useState(true)

  useEffect(() => {
    Promise.all([
      jobsApi.stats() as Promise<MatchStats>,
      jobsApi.matches({ min_score: 70, limit: 8 }) as Promise<JobMatch[]>,
      ingestionApi.runs(1) as Promise<IngestionRun[]>,
    ]).then(([s, m, r]) => {
      setStats(s)
      setMatches(m)
      setLastRun(r?.[0] ?? null)
    }).finally(() => setLoading(false))
  }, [])

  async function triggerRun() {
    setRunning(true)
    try {
      await ingestionApi.triggerRun()
      setTimeout(() => {
        ingestionApi.runs(1).then((r: any) => setLastRun(r?.[0]))
        setRunning(false)
      }, 2000)
    } catch { setRunning(false) }
  }

  return (
    <div className="p-6 space-y-6 max-w-[1200px]">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-1 tracking-tight">Dashboard</h1>
          <p className="text-sm text-text-3 mt-0.5">
            {lastRun
              ? `Last scan ${formatRelative(lastRun.started_at)} · ${lastRun.status}`
              : 'No ingestion runs yet'}
          </p>
        </div>
        <button
          onClick={triggerRun}
          disabled={running}
          className="btn-primary gap-2"
        >
          {running
            ? <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            : <Play className="w-3.5 h-3.5" />}
          {running ? 'Scanning…' : 'Scan Now'}
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          icon={<Briefcase className="w-4 h-4 text-accent-blue" />}
          label="Total Matches"
          value={stats?.total_matches ?? '—'}
          loading={loading}
        />
        <StatCard
          icon={<TrendingUp className="w-4 h-4 text-green-400" />}
          label="High Score (80+)"
          value={stats?.high_score_matches ?? '—'}
          loading={loading}
          accent="green"
        />
        <StatCard
          icon={<Bell className="w-4 h-4 text-amber-400" />}
          label="New Today"
          value={stats?.new_today ?? '—'}
          loading={loading}
          accent="amber"
        />
        <StatCard
          icon={<Building2 className="w-4 h-4 text-purple-400" />}
          label="Applied"
          value={stats?.applied_count ?? '—'}
          loading={loading}
          accent="purple"
        />
      </div>

      {/* Top matches + run summary */}
      <div className="grid grid-cols-[1fr_340px] gap-4">

        {/* Top matches */}
        <div className="card">
          <div className="section-header">
            <h2 className="text-sm font-semibold text-text-1">Top Matches</h2>
            <Link href="/jobs" className="text-2xs text-accent-blue hover:underline flex items-center gap-1">
              View all <ChevronRight className="w-3 h-3" />
            </Link>
          </div>

          {loading ? (
            <SkeletonRows rows={6} />
          ) : matches.length === 0 ? (
            <EmptyState message="No matches yet — add companies and profiles to start" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Role</th>
                  <th>Score</th>
                  <th>Profile</th>
                  <th>Seen</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {matches.map(m => (
                  <tr key={m.id}>
                    <td>
                      <p className="text-text-1 font-medium text-sm leading-tight">{m.title}</p>
                      <p className="text-text-3 text-2xs mt-0.5">{m.company_name}</p>
                    </td>
                    <td>
                      <ScoreBadge score={m.match_score} />
                    </td>
                    <td>
                      <span className="pill-muted">{m.profile_name}</span>
                    </td>
                    <td className="text-text-3 text-xs font-mono">
                      {formatRelative(m.first_seen_at)}
                    </td>
                    <td>
                      <a
                        href={m.application_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-accent-blue hover:text-blue-400 transition-colors"
                        onClick={e => e.stopPropagation()}
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Run summary card */}
        <div className="space-y-4">
          {/* Last run */}
          <div className="card p-5">
            <h3 className="text-xs font-mono text-text-3 uppercase tracking-wider mb-3">
              Last Scan
            </h3>
            {lastRun ? (
              <div className="space-y-2">
                <RunStat label="Companies checked" value={lastRun.companies_checked} />
                <RunStat label="New jobs"          value={lastRun.new_jobs_found} accent="blue" />
                <RunStat label="New matches"       value={lastRun.matches_found} accent="green" />
                <RunStat label="Alerts sent"       value={lastRun.alerts_sent} accent="amber" />
                <RunStat label="Errors"            value={lastRun.error_count} accent={lastRun.error_count > 0 ? "red" : undefined} />
                <div className="pt-2 border-t border-surface-4">
                  <p className="text-2xs text-text-3 font-mono">
                    {lastRun.duration_seconds != null
                      ? `${lastRun.duration_seconds.toFixed(0)}s`
                      : 'In progress…'}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-text-3">No runs yet</p>
            )}
          </div>

          {/* Quick links */}
          <div className="card p-5 space-y-2">
            <h3 className="text-xs font-mono text-text-3 uppercase tracking-wider mb-3">
              Quick Actions
            </h3>
            {[
              { href: '/companies', label: 'Add a company' },
              { href: '/profiles',  label: 'Create a profile' },
              { href: '/resumes',   label: 'Upload resume' },
              { href: '/tracker',   label: 'View tracker' },
            ].map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className="flex items-center justify-between text-sm text-text-2 hover:text-text-1 transition-colors group"
              >
                {label}
                <ChevronRight className="w-3.5 h-3.5 text-text-3 group-hover:text-text-2 transition-colors" />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, loading, accent }: any) {
  const accentColor: Record<string, string> = {
    green:  'border-l-green-500/40',
    amber:  'border-l-amber-500/40',
    purple: 'border-l-purple-500/40',
    default:'border-l-blue-500/40',
  }
  const border = accentColor[accent] ?? accentColor.default

  return (
    <div className={`stat-card border-l-2 ${border}`}>
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-xs text-text-3 font-medium">{label}</span>
      </div>
      {loading
        ? <div className="skeleton h-7 w-16 mt-1" />
        : <p className="text-2xl font-bold text-text-1 font-mono mt-0.5">{value}</p>}
    </div>
  )
}

function RunStat({ label, value, accent }: { label: string; value: number; accent?: string }) {
  const color = { blue: 'text-blue-400', green: 'text-green-400', amber: 'text-amber-400', red: 'text-red-400' }
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-text-3">{label}</span>
      <span className={`text-sm font-mono font-medium ${accent ? (color as any)[accent] : 'text-text-1'}`}>
        {value}
      </span>
    </div>
  )
}

function ScoreBadge({ score }: { score: number }) {
  const color = scoreColor(score)
  return (
    <span
      className="score-badge text-2xs font-mono"
      style={{ color, borderColor: `${color}40` }}
    >
      {score}
    </span>
  )
}

function SkeletonRows({ rows }: { rows: number }) {
  return (
    <div className="p-4 space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-10 w-full" />
      ))}
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="p-8 text-center">
      <p className="text-sm text-text-3">{message}</p>
    </div>
  )
}
