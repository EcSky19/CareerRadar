// src/lib/utils.ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function scoreColor(score: number): string {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#f59e0b'
  return '#ef4444'
}

export function scoreClass(score: number): string {
  if (score >= 80) return 'score-text-high'
  if (score >= 60) return 'score-text-mid'
  return 'score-text-low'
}

export function formatDate(iso?: string): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatRelative(iso?: string): string {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 7) return `${days}d ago`
  if (days < 30) return `${Math.floor(days / 7)}w ago`
  return formatDate(iso)
}

export const PROVIDER_LABELS: Record<string, string> = {
  greenhouse: 'Greenhouse',
  lever:      'Lever',
  ashby:      'Ashby',
  workday:    'Workday',
  icims:      'iCIMS',
  smartrecruiters: 'SmartRecruiters',
  custom_html: 'HTML',
  unknown:    'Unknown',
}

export const STATUS_LABELS: Record<string, string> = {
  not_applied: 'Not Applied',
  saved:       'Saved',
  applied:     'Applied',
  interview:   'Interview',
  rejected:    'Rejected',
  offer:       'Offer',
  archived:    'Archived',
}

export const STATUS_PILL: Record<string, string> = {
  not_applied: 'pill-muted',
  saved:       'pill-blue',
  applied:     'pill-purple',
  interview:   'pill-amber',
  rejected:    'pill-red',
  offer:       'pill-green',
  archived:    'pill-muted',
}
