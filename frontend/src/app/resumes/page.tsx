'use client'

import { useEffect, useState, useRef } from 'react'
import { resumesApi } from '@/lib/api'
import { Resume, AnalysisResult } from '@/types'
import { scoreColor } from '@/lib/utils'
import {
  Upload, FileText, ChevronRight, AlertTriangle,
  CheckCircle, XCircle, Info, Sparkles, RefreshCw
} from 'lucide-react'

type View = 'list' | 'analyze' | 'results'

export default function ResumesPage() {
  const [resumes, setResumes]       = useState<Resume[]>([])
  const [selected, setSelected]     = useState<Resume | null>(null)
  const [view, setView]             = useState<View>('list')
  const [analysis, setAnalysis]     = useState<AnalysisResult | null>(null)
  const [uploading, setUploading]   = useState(false)
  const [analyzing, setAnalyzing]   = useState(false)
  const [optimizing, setOptimizing] = useState(false)
  const [loading, setLoading]       = useState(true)

  // Analyze form
  const [jobDesc, setJobDesc]       = useState('')
  const [jobTitle, setJobTitle]     = useState('')
  const [companyName, setCompanyName] = useState('')

  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    resumesApi.list().then((r: any) => {
      setResumes(r)
      if (r.length > 0) setSelected(r[0])
    }).finally(() => setLoading(false))
  }, [])

  async function handleUpload(file: File) {
    setUploading(true)
    try {
      const result = await resumesApi.upload(file, file.name.replace(/\.[^.]+$/, ''), resumes.length === 0)
      const updated = await resumesApi.list() as Resume[]
      setResumes(updated)
      setSelected(updated.find(r => r.id === result.id) ?? updated[0])
    } finally { setUploading(false) }
  }

  async function analyze() {
    if (!selected || !jobDesc.trim()) return
    setAnalyzing(true)
    try {
      const result = await resumesApi.analyze(selected.id, {
        job_description: jobDesc,
        job_title: jobTitle,
        company_name: companyName,
      }) as AnalysisResult
      setAnalysis(result)
      setView('results')
    } finally { setAnalyzing(false) }
  }

  async function optimize() {
    if (!selected || !analysis) return
    setOptimizing(true)
    try {
      const result = await resumesApi.optimize(
        selected.id,
        analysis.analysis_id,
        `${companyName || 'Optimized'} Version`,
      ) as any
      alert(`✓ ${result.version_name} created. Remember to replace all [X] placeholders with your real numbers.`)
    } finally { setOptimizing(false) }
  }

  return (
    <div className="flex h-full">
      {/* Left: resume list */}
      <aside className="w-[240px] shrink-0 border-r border-surface-4 bg-surface-0 flex flex-col">
        <div className="p-4 border-b border-surface-4">
          <h2 className="text-xs font-mono text-text-3 uppercase tracking-wider mb-3">My Resumes</h2>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="btn-primary w-full justify-center text-xs"
          >
            {uploading ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
            {uploading ? 'Uploading…' : 'Upload Resume'}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt"
            className="hidden"
            onChange={e => e.target.files?.[0] && handleUpload(e.target.files[0])}
          />
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {loading ? (
            <div className="space-y-2 p-2">
              {Array.from({ length: 3 }).map((_, i) => <div key={i} className="skeleton h-12 w-full" />)}
            </div>
          ) : resumes.length === 0 ? (
            <div className="p-4 text-center">
              <FileText className="w-8 h-8 text-text-3 mx-auto mb-2" />
              <p className="text-xs text-text-3">No resumes uploaded yet</p>
            </div>
          ) : (
            resumes.map(r => (
              <button
                key={r.id}
                onClick={() => { setSelected(r); setView('analyze'); setAnalysis(null) }}
                className={`w-full text-left px-3 py-2.5 rounded transition-colors mb-1 ${
                  selected?.id === r.id
                    ? 'bg-accent-blue/10 border border-accent-blue/20'
                    : 'hover:bg-surface-3'
                }`}
              >
                <p className="text-xs font-medium text-text-1 truncate">{r.name}</p>
                <p className="text-2xs text-text-3 font-mono mt-0.5">
                  {r.file_format?.toUpperCase()}
                  {r.is_base && ' · base'}
                </p>
                {r.parse_warnings?.length > 0 && (
                  <AlertTriangle className="w-3 h-3 text-amber-400 mt-1" />
                )}
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Right: analyze panel or results */}
      <div className="flex-1 overflow-y-auto">
        {!selected ? (
          <DropZone onFile={handleUpload} />
        ) : view === 'analyze' ? (
          <AnalyzePanel
            resume={selected}
            jobDesc={jobDesc} setJobDesc={setJobDesc}
            jobTitle={jobTitle} setJobTitle={setJobTitle}
            companyName={companyName} setCompanyName={setCompanyName}
            onAnalyze={analyze}
            analyzing={analyzing}
          />
        ) : view === 'results' && analysis ? (
          <ResultsPanel
            analysis={analysis}
            onOptimize={optimize}
            optimizing={optimizing}
            onBack={() => setView('analyze')}
          />
        ) : null}
      </div>
    </div>
  )
}

// ── Sub-panels ────────────────────────────────────────────────────────────────

function DropZone({ onFile }: { onFile: (f: File) => void }) {
  const fileRef = useRef<HTMLInputElement>(null)
  return (
    <div
      className="m-8 border-2 border-dashed border-surface-5 rounded-lg p-12 text-center cursor-pointer hover:border-accent-blue/50 transition-colors"
      onClick={() => fileRef.current?.click()}
    >
      <Upload className="w-10 h-10 text-text-3 mx-auto mb-3" />
      <p className="text-sm text-text-2">Drop your resume or click to upload</p>
      <p className="text-xs text-text-3 mt-1">PDF, DOCX, or TXT · max 10 MB</p>
      <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" className="hidden"
        onChange={e => e.target.files?.[0] && onFile(e.target.files[0])} />
    </div>
  )
}

function AnalyzePanel({ resume, jobDesc, setJobDesc, jobTitle, setJobTitle,
  companyName, setCompanyName, onAnalyze, analyzing }: any) {
  return (
    <div className="p-6 max-w-2xl space-y-5">
      <div>
        <h2 className="page-title">Analyze Against a Job</h2>
        <p className="text-sm text-text-3 mt-0.5">Paste a job description to score your resume and get keyword gap analysis.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-text-3 mb-1 block">Job Title</label>
          <input className="input" placeholder="Software Engineer" value={jobTitle}
            onChange={e => setJobTitle(e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-text-3 mb-1 block">Company</label>
          <input className="input" placeholder="Stripe" value={companyName}
            onChange={e => setCompanyName(e.target.value)} />
        </div>
      </div>

      <div>
        <label className="text-xs text-text-3 mb-1 block">Job Description *</label>
        <textarea
          className="input font-mono text-xs resize-none h-48"
          placeholder="Paste the full job description here…"
          value={jobDesc}
          onChange={e => setJobDesc(e.target.value)}
        />
      </div>

      <button
        onClick={onAnalyze}
        disabled={analyzing || !jobDesc.trim()}
        className="btn-primary"
      >
        {analyzing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
        {analyzing ? 'Analyzing…' : 'Analyze Resume'}
      </button>
    </div>
  )
}

function ResultsPanel({ analysis, onOptimize, optimizing, onBack }: {
  analysis: AnalysisResult
  onOptimize: () => void
  optimizing: boolean
  onBack: () => void
}) {
  const { scores, recruiter, keywords, priority_edits } = analysis
  const verdictColor: Record<string, string> = {
    strong_move_forward: 'text-green-400',
    move_forward: 'text-green-400',
    maybe: 'text-amber-400',
    weak_maybe: 'text-amber-400',
    likely_reject: 'text-red-400',
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="page-title">Analysis Results</h2>
        <div className="flex gap-2">
          <button onClick={onBack} className="btn-ghost text-xs">← Back</button>
          <button onClick={onOptimize} disabled={optimizing} className="btn-primary text-xs">
            {optimizing ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
            {optimizing ? 'Optimizing…' : 'AI Optimize'}
          </button>
        </div>
      </div>

      {/* Score grid */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Overall',          value: scores.overall },
          { label: 'ATS Keywords',     value: scores.ats_keyword },
          { label: 'Recruiter Scan',   value: scores.recruiter_scan },
          { label: 'Technical Depth',  value: scores.technical_depth },
          { label: 'Quantified Impact',value: scores.quantified_impact },
          { label: 'Formatting',       value: scores.formatting },
        ].map(({ label, value }) => (
          <ScoreCard key={label} label={label} value={value} />
        ))}
      </div>

      {/* Recruiter verdict */}
      <div className="card p-5">
        <div className="flex items-start gap-3">
          <div>
            <p className="text-xs text-text-3 font-mono uppercase tracking-wider mb-1">
              Recruiter Simulation
            </p>
            <p className={`text-sm font-semibold ${verdictColor[recruiter.verdict] ?? 'text-text-1'}`}>
              {recruiter.verdict.replace(/_/g, ' ')}
            </p>
          </div>
        </div>
        <p className="text-sm text-text-2 mt-3 leading-relaxed">{recruiter.impression}</p>
        <div className="mt-3 space-y-1.5">
          <p className="text-xs text-text-3"><span className="text-text-2">Reason: </span>{recruiter.main_reason}</p>
          <p className="text-xs text-text-3"><span className="text-text-2">Weakness: </span>{recruiter.biggest_weakness}</p>
          <p className="text-xs text-accent-blue">→ {recruiter.fastest_fix}</p>
        </div>
      </div>

      {/* Keywords */}
      <div className="card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-text-1">Keyword Coverage</h3>

        {keywords.required_missing.length > 0 && (
          <div>
            <p className="text-xs text-red-400 mb-2 flex items-center gap-1">
              <XCircle className="w-3 h-3" /> Required — Missing ({keywords.required_missing.length})
            </p>
            <div className="flex flex-wrap gap-1">
              {keywords.required_missing.map(k => (
                <span key={k} className="pill-red">{k}</span>
              ))}
            </div>
          </div>
        )}

        {keywords.required_found.length > 0 && (
          <div>
            <p className="text-xs text-green-400 mb-2 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> Required — Found ({keywords.required_found.length})
            </p>
            <div className="flex flex-wrap gap-1">
              {keywords.required_found.map(k => (
                <span key={k} className="pill-green">{k}</span>
              ))}
            </div>
          </div>
        )}

        {keywords.preferred_missing.length > 0 && (
          <div>
            <p className="text-xs text-amber-400 mb-2 flex items-center gap-1">
              <Info className="w-3 h-3" /> Preferred — Missing ({keywords.preferred_missing.length})
            </p>
            <div className="flex flex-wrap gap-1">
              {keywords.preferred_missing.slice(0, 12).map(k => (
                <span key={k} className="pill-amber">{k}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Priority edits */}
      {priority_edits.must_fix.length > 0 && (
        <PriorityList label="Must Fix" items={priority_edits.must_fix} color="red" />
      )}
      {priority_edits.should_fix.length > 0 && (
        <PriorityList label="Should Fix" items={priority_edits.should_fix} color="amber" />
      )}
      {priority_edits.nice_to_have.length > 0 && (
        <PriorityList label="Nice to Have" items={priority_edits.nice_to_have} color="muted" />
      )}
    </div>
  )
}

function ScoreCard({ label, value }: { label: string; value: number }) {
  const color = scoreColor(value)
  return (
    <div className="card p-4">
      <p className="text-2xs text-text-3 font-mono">{label}</p>
      <p className="text-2xl font-bold font-mono mt-1" style={{ color }}>{value}</p>
      <div className="mt-2 h-1 bg-surface-4 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${value}%`, background: color }}
        />
      </div>
    </div>
  )
}

function PriorityList({ label, items, color }: {
  label: string
  items: { section: string; description: string }[]
  color: string
}) {
  const borderColor: Record<string, string> = {
    red: 'border-red-500/30', amber: 'border-amber-500/30', muted: 'border-surface-5'
  }
  const textColor: Record<string, string> = {
    red: 'text-red-400', amber: 'text-amber-400', muted: 'text-text-3'
  }
  return (
    <div className={`card border-l-2 ${borderColor[color]} p-4`}>
      <h4 className={`text-xs font-mono uppercase tracking-wider mb-3 ${textColor[color]}`}>{label}</h4>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-xs font-mono text-text-3 shrink-0 pt-0.5">{item.section}</span>
            <span className="text-xs text-text-2">{item.description}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
