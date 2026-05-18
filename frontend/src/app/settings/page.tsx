'use client'
import { useEffect, useState } from 'react'
import { usersApi } from '@/lib/api'
import { UserProfile } from '@/types'
import { Save, CheckCircle } from 'lucide-react'

export default function SettingsPage() {
  const [user, setUser]     = useState<UserProfile | null>(null)
  const [form, setForm]     = useState<Partial<UserProfile>>({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved]   = useState(false)

  useEffect(() => {
    usersApi.me().then((u: any) => {
      setUser(u)
      setForm({
        full_name:            u.full_name ?? '',
        graduation_year:      u.graduation_year ?? undefined,
        school:               u.school ?? '',
        major:                u.major ?? '',
        alert_email:          u.alert_email ?? '',
        alert_frequency:      u.alert_frequency ?? 'daily',
        minimum_match_score:  u.minimum_match_score ?? 70,
        notifications_enabled: u.notifications_enabled ?? true,
      })
    })
  }, [])

  async function handleSave() {
    setSaving(true)
    try {
      await usersApi.update(form)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } finally { setSaving(false) }
  }

  if (!user) return (
    <div className="p-6 space-y-3">
      {Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton h-12 w-full max-w-lg" />)}
    </div>
  )

  return (
    <div className="flex flex-col h-full">
      <div className="section-header">
        <h1 className="page-title">Settings</h1>
        <button onClick={handleSave} disabled={saving} className="btn-primary">
          {saved ? <CheckCircle className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
          {saved ? 'Saved!' : saving ? 'Saving…' : 'Save Changes'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-lg space-y-8">

          {/* Account */}
          <Section title="Account">
            <Field label="Email">
              <input className="input" value={user.email} disabled />
            </Field>
            <Field label="Full Name">
              <input className="input" placeholder="Your name" value={form.full_name ?? ''}
                onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} />
            </Field>
          </Section>

          {/* Academic */}
          <Section title="Academic Background">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Graduation Year">
                <input className="input font-mono" type="number" placeholder="2025"
                  value={form.graduation_year ?? ''}
                  onChange={e => setForm(f => ({ ...f, graduation_year: Number(e.target.value) || undefined }))} />
              </Field>
              <Field label="School">
                <input className="input" placeholder="NYU, Cornell…"
                  value={form.school ?? ''}
                  onChange={e => setForm(f => ({ ...f, school: e.target.value }))} />
              </Field>
            </div>
            <Field label="Major">
              <input className="input" placeholder="Computer Science"
                value={form.major ?? ''}
                onChange={e => setForm(f => ({ ...f, major: e.target.value }))} />
            </Field>
          </Section>

          {/* Alerts */}
          <Section title="Alert Settings">
            <Field label="Alert Email" hint="Defaults to your account email if blank">
              <input className="input" type="email" placeholder={user.email}
                value={form.alert_email ?? ''}
                onChange={e => setForm(f => ({ ...f, alert_email: e.target.value }))} />
            </Field>
            <Field label="Alert Frequency">
              <select className="input" value={form.alert_frequency ?? 'daily'}
                onChange={e => setForm(f => ({ ...f, alert_frequency: e.target.value }))}>
                <option value="daily">Daily digest</option>
                <option value="realtime">Real-time (per match)</option>
              </select>
            </Field>
            <Field label="Minimum Alert Score" hint="Only send alerts for matches at or above this score">
              <div className="flex items-center gap-3">
                <input
                  className="input font-mono w-24"
                  type="number" min={0} max={100}
                  value={form.minimum_match_score ?? 70}
                  onChange={e => setForm(f => ({ ...f, minimum_match_score: Number(e.target.value) }))}
                />
                <span className="text-xs text-text-3">/ 100</span>
              </div>
            </Field>
            <Field label="Notifications">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.notifications_enabled ?? true}
                  onChange={e => setForm(f => ({ ...f, notifications_enabled: e.target.checked }))}
                  className="accent-accent-blue"
                />
                <span className="text-sm text-text-2">Email alerts enabled</span>
              </label>
            </Field>
          </Section>

          {/* Danger zone */}
          <Section title="Account Info" muted>
            <div className="text-xs text-text-3 space-y-1 font-mono">
              <p>User ID: {user.id}</p>
              <p>Created: {new Date(user.created_at ?? '').toLocaleDateString()}</p>
            </div>
          </Section>

        </div>
      </div>
    </div>
  )
}

function Section({ title, children, muted }: {
  title: string; children: React.ReactNode; muted?: boolean
}) {
  return (
    <div>
      <h2 className={`text-xs font-mono uppercase tracking-wider mb-4 ${muted ? 'text-text-3' : 'text-text-2'}`}>
        {title}
      </h2>
      <div className="card p-5 space-y-4">{children}</div>
    </div>
  )
}

function Field({ label, hint, children }: {
  label: string; hint?: string; children: React.ReactNode
}) {
  return (
    <div>
      <label className="text-xs text-text-3 mb-1 block">{label}</label>
      {children}
      {hint && <p className="text-2xs text-text-3 mt-1">{hint}</p>}
    </div>
  )
}
