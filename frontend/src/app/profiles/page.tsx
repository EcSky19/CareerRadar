'use client'
import { useEffect, useState } from 'react'
import { profilesApi } from '@/lib/api'
import { TargetProfile } from '@/types'
import { Plus, Trash2, Copy, ChevronDown, ChevronUp, X, Tag } from 'lucide-react'

const ROLE_TYPE_OPTIONS = [
  { value: 'internship', label: 'Internship' },
  { value: 'new_grad',   label: 'New Grad' },
  { value: 'full_time',  label: 'Full-Time' },
  { value: 'coop',       label: 'Co-op' },
  { value: 'contract',   label: 'Contract' },
]

const SEARCH_MODE_OPTIONS = [
  { value: 'strict_software_ai',    label: 'Strict: Software / AI' },
  { value: 'balanced',              label: 'Balanced' },
  { value: 'finance_tech_balanced', label: 'Finance-Tech Balanced' },
  { value: 'finance_broad',         label: 'Finance Broad' },
  { value: 'investment_only',       label: 'Investment Only' },
  { value: 'broad',                 label: 'Broad' },
]

const BLANK_FORM = {
  name: '',
  desired_titles: [] as string[],
  desired_keywords: [] as string[],
  desired_locations: [] as string[],
  excluded_keywords: [] as string[],
  role_types: [] as string[],
  remote_preference: 'any',
  minimum_match_score: 70,
  search_mode: 'balanced',
  alerts_enabled: true,
}

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<TargetProfile[]>([])
  const [loading, setLoading]   = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing]   = useState<TargetProfile | null>(null)
  const [form, setForm]         = useState(BLANK_FORM)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    profilesApi.list(false).then((p: any) => setProfiles(p))
      .finally(() => setLoading(false))
  }, [])

  function openCreate() {
    setEditing(null)
    setForm(BLANK_FORM)
    setShowForm(true)
  }

  function openEdit(profile: TargetProfile) {
    setEditing(profile)
    setForm({
      name: profile.name,
      desired_titles: [...profile.desired_titles],
      desired_keywords: [...profile.desired_keywords],
      desired_locations: [...profile.desired_locations],
      excluded_keywords: [...profile.excluded_keywords],
      role_types: [...profile.role_types],
      remote_preference: profile.remote_preference,
      minimum_match_score: profile.minimum_match_score,
      search_mode: profile.search_mode,
      alerts_enabled: profile.alerts_enabled,
    })
    setShowForm(true)
  }

  async function save() {
    if (!form.name.trim()) return
    if (editing) {
      const updated = await profilesApi.update(editing.id, form) as TargetProfile
      setProfiles(prev => prev.map(p => p.id === editing.id ? updated : p))
    } else {
      const created = await profilesApi.create(form) as TargetProfile
      setProfiles(prev => [created, ...prev])
    }
    setShowForm(false)
  }

  async function deleteProfile(id: string) {
    if (!confirm('Delete this profile?')) return
    await profilesApi.delete(id)
    setProfiles(prev => prev.filter(p => p.id !== id))
  }

  async function duplicateProfile(id: string) {
    const copy = await profilesApi.duplicate(id) as TargetProfile
    setProfiles(prev => [copy, ...prev])
  }

  return (
    <div className="flex flex-col h-full">
      <div className="section-header">
        <h1 className="page-title">Target Profiles <span className="text-text-3 font-normal text-sm ml-1">({profiles.length})</span></h1>
        <button onClick={openCreate} className="btn-primary">
          <Plus className="w-3.5 h-3.5" /> New Profile
        </button>
      </div>

      {/* Form panel */}
      {showForm && (
        <div className="border-b border-surface-4 bg-surface-2 p-5">
          <div className="max-w-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">{editing ? 'Edit Profile' : 'New Profile'}</h3>
              <button onClick={() => setShowForm(false)} className="p-1 hover:bg-surface-4 rounded">
                <X className="w-4 h-4 text-text-3" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-text-3 mb-1 block">Profile Name *</label>
                <input className="input" placeholder="Software Engineering"
                  value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-text-3 mb-1 block">Min Match Score</label>
                <input className="input font-mono" type="number" min={0} max={100}
                  value={form.minimum_match_score}
                  onChange={e => setForm(f => ({ ...f, minimum_match_score: Number(e.target.value) }))} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-text-3 mb-1 block">Search Mode</label>
                <select className="input" value={form.search_mode}
                  onChange={e => setForm(f => ({ ...f, search_mode: e.target.value }))}>
                  {SEARCH_MODE_OPTIONS.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-text-3 mb-1 block">Remote Preference</label>
                <select className="input" value={form.remote_preference}
                  onChange={e => setForm(f => ({ ...f, remote_preference: e.target.value }))}>
                  {['any', 'remote', 'hybrid', 'onsite'].map(v => (
                    <option key={v} value={v}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Role types */}
            <div>
              <label className="text-xs text-text-3 mb-1.5 block">Role Types</label>
              <div className="flex flex-wrap gap-1.5">
                {ROLE_TYPE_OPTIONS.map(({ value, label }) => {
                  const selected = form.role_types.includes(value)
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setForm(f => ({
                        ...f,
                        role_types: selected
                          ? f.role_types.filter(r => r !== value)
                          : [...f.role_types, value],
                      }))}
                      className={`pill cursor-pointer ${selected ? 'pill-blue' : 'pill-muted'}`}
                    >
                      {label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Tag fields */}
            <TagField
              label="Desired Titles"
              placeholder="Software Engineer, ML Engineer…"
              tags={form.desired_titles}
              onChange={tags => setForm(f => ({ ...f, desired_titles: tags }))}
            />
            <TagField
              label="Keywords"
              placeholder="Python, Kubernetes, distributed systems…"
              tags={form.desired_keywords}
              onChange={tags => setForm(f => ({ ...f, desired_keywords: tags }))}
            />
            <TagField
              label="Locations"
              placeholder="New York, San Francisco, Remote…"
              tags={form.desired_locations}
              onChange={tags => setForm(f => ({ ...f, desired_locations: tags }))}
            />
            <TagField
              label="Excluded Keywords"
              placeholder="Director, VP, 10+ years…"
              tags={form.excluded_keywords}
              onChange={tags => setForm(f => ({ ...f, excluded_keywords: tags }))}
              danger
            />

            <div className="flex items-center gap-3 pt-1">
              <button onClick={save} disabled={!form.name.trim()} className="btn-primary">
                {editing ? 'Save Changes' : 'Create Profile'}
              </button>
              <button onClick={() => setShowForm(false)} className="btn-ghost">Cancel</button>
              <label className="flex items-center gap-2 ml-auto cursor-pointer">
                <input type="checkbox" checked={form.alerts_enabled}
                  onChange={e => setForm(f => ({ ...f, alerts_enabled: e.target.checked }))}
                  className="accent-accent-blue" />
                <span className="text-xs text-text-2">Alerts enabled</span>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Profile list */}
      <div className="flex-1 overflow-y-auto divide-y divide-surface-4">
        {loading ? (
          <div className="p-6 space-y-3">
            {Array.from({ length: 3 }).map((_, i) => <div key={i} className="skeleton h-16 w-full" />)}
          </div>
        ) : profiles.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <p className="text-text-2">No profiles yet.</p>
            <p className="text-text-3 text-sm">Create a profile to tell the matching engine what roles you want.</p>
          </div>
        ) : (
          profiles.map(profile => (
            <div key={profile.id} className="hover:bg-surface-3/30 transition-colors">
              <div className="flex items-center gap-4 px-6 py-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-medium text-text-1">{profile.name}</h3>
                    {!profile.is_active && <span className="pill-muted text-2xs">inactive</span>}
                    {!profile.alerts_enabled && <span className="pill-amber text-2xs">alerts off</span>}
                  </div>
                  <div className="flex items-center gap-3 mt-1 flex-wrap">
                    <span className="text-2xs text-text-3 font-mono">score ≥{profile.minimum_match_score}</span>
                    <span className="text-2xs text-text-3 font-mono">{profile.search_mode}</span>
                    {profile.role_types.length > 0 && (
                      <div className="flex gap-1">
                        {profile.role_types.map(r => (
                          <span key={r} className="pill-blue text-2xs">{r}</span>
                        ))}
                      </div>
                    )}
                    {profile.desired_titles.length > 0 && (
                      <span className="text-2xs text-text-3">
                        {profile.desired_titles.slice(0, 3).join(', ')}
                        {profile.desired_titles.length > 3 && ` +${profile.desired_titles.length - 3}`}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(profile)} className="btn-ghost text-xs py-1">Edit</button>
                  <button onClick={() => duplicateProfile(profile.id)}
                    className="p-1.5 rounded hover:bg-surface-4 transition-colors" title="Duplicate">
                    <Copy className="w-3.5 h-3.5 text-text-3 hover:text-text-1" />
                  </button>
                  <button onClick={() => deleteProfile(profile.id)}
                    className="p-1.5 rounded hover:bg-surface-4 transition-colors" title="Delete">
                    <Trash2 className="w-3.5 h-3.5 text-text-3 hover:text-red-400" />
                  </button>
                  <button onClick={() => setExpanded(expanded === profile.id ? null : profile.id)}
                    className="p-1.5 rounded hover:bg-surface-4 transition-colors">
                    {expanded === profile.id
                      ? <ChevronUp className="w-3.5 h-3.5 text-text-3" />
                      : <ChevronDown className="w-3.5 h-3.5 text-text-3" />}
                  </button>
                </div>
              </div>

              {expanded === profile.id && (
                <div className="px-6 pb-4 grid grid-cols-2 gap-4 bg-surface-2/50 text-xs">
                  <TagDisplay label="Titles" tags={profile.desired_titles} color="blue" />
                  <TagDisplay label="Keywords" tags={profile.desired_keywords} color="green" />
                  <TagDisplay label="Locations" tags={profile.desired_locations} color="purple" />
                  <TagDisplay label="Excluded" tags={profile.excluded_keywords} color="red" />
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ── Micro components ──────────────────────────────────────────────────────────

function TagField({ label, placeholder, tags, onChange, danger }: {
  label: string; placeholder: string; tags: string[];
  onChange: (tags: string[]) => void; danger?: boolean
}) {
  const [input, setInput] = useState('')

  function add() {
    const val = input.trim()
    if (!val || tags.includes(val)) return
    onChange([...tags, val])
    setInput('')
  }

  return (
    <div>
      <label className="text-xs text-text-3 mb-1 block">{label}</label>
      <div className="flex gap-2">
        <input
          className="input flex-1"
          placeholder={placeholder}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
        />
        <button type="button" onClick={add} className="btn-ghost px-3">Add</button>
      </div>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {tags.map(tag => (
            <span
              key={tag}
              className={`pill ${danger ? 'pill-red' : 'pill-blue'} cursor-pointer`}
              onClick={() => onChange(tags.filter(t => t !== tag))}
            >
              {tag} <X className="w-2.5 h-2.5 ml-0.5 inline" />
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function TagDisplay({ label, tags, color }: { label: string; tags: string[]; color: string }) {
  if (tags.length === 0) return null
  return (
    <div>
      <p className="text-text-3 mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-1">
        {tags.map(t => <span key={t} className={`pill-${color} text-2xs`}>{t}</span>)}
      </div>
    </div>
  )
}
