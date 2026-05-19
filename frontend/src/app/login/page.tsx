'use client'

import { useState } from 'react'
import { createClient } from '@supabase/supabase-js'
import { Zap } from 'lucide-react'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export default function LoginPage() {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode]         = useState<'login' | 'signup'>('login')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [message, setMessage]   = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setMessage('')
    try {
      if (mode === 'signup') {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
        setMessage('Check your email for a confirmation link.')
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
        window.location.href = '/dashboard'
      }
    } catch (err: any) {
      setError(err.message ?? 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{minHeight:'100vh',background:'#0d0f12',display:'flex',alignItems:'center',justifyContent:'center',fontFamily:'Inter,-apple-system,sans-serif'}}>
      <div style={{width:'100%',maxWidth:'380px',padding:'0 16px'}}>
        <div style={{textAlign:'center',marginBottom:'32px'}}>
          <div style={{width:'44px',height:'44px',background:'#24c78e',borderRadius:'10px',display:'inline-flex',alignItems:'center',justifyContent:'center',marginBottom:'14px'}}>
            <Zap size={22} color="white" />
          </div>
          <h1 style={{color:'#eef1f7',fontSize:'22px',fontWeight:700,letterSpacing:'-0.5px'}}>Career Radar</h1>
          <p style={{color:'#56647a',fontSize:'13px',marginTop:'4px'}}>
            {mode === 'login' ? 'Sign in to your account' : 'Create your account'}
          </p>
        </div>
        <div style={{background:'#181c22',border:'1px solid #2a3040',borderRadius:'12px',padding:'28px'}}>
          <form onSubmit={handleSubmit}>
            <div style={{marginBottom:'14px'}}>
              <label style={{display:'block',fontSize:'12px',color:'#8d99b0',marginBottom:'5px',fontWeight:500}}>Email</label>
              <input type="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="you@example.com"
                style={{width:'100%',padding:'9px 12px',background:'#1e2430',border:'1px solid #2a3040',borderRadius:'6px',color:'#eef1f7',fontSize:'13px',outline:'none',fontFamily:'inherit',boxSizing:'border-box'}} />
            </div>
            <div style={{marginBottom:'20px'}}>
              <label style={{display:'block',fontSize:'12px',color:'#8d99b0',marginBottom:'5px',fontWeight:500}}>Password</label>
              <input type="password" value={password} onChange={e=>setPassword(e.target.value)} required placeholder="••••••••"
                style={{width:'100%',padding:'9px 12px',background:'#1e2430',border:'1px solid #2a3040',borderRadius:'6px',color:'#eef1f7',fontSize:'13px',outline:'none',fontFamily:'inherit',boxSizing:'border-box'}} />
            </div>
            {error && (
              <div style={{background:'rgba(224,82,82,.08)',border:'1px solid rgba(224,82,82,.2)',borderRadius:'6px',padding:'10px 12px',color:'#e05252',fontSize:'12px',marginBottom:'14px'}}>{error}</div>
            )}
            {message && (
              <div style={{background:'rgba(36,199,142,.08)',border:'1px solid rgba(36,199,142,.2)',borderRadius:'6px',padding:'10px 12px',color:'#24c78e',fontSize:'12px',marginBottom:'14px'}}>{message}</div>
            )}
            <button type="submit" disabled={loading}
              style={{width:'100%',padding:'10px',background:'#24c78e',border:'none',borderRadius:'6px',color:'white',fontSize:'13px',fontWeight:600,cursor:loading?'not-allowed':'pointer',fontFamily:'inherit',opacity:loading?0.7:1}}>
              {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
          <div style={{textAlign:'center',marginTop:'18px'}}>
            <button onClick={()=>{setMode(mode==='login'?'signup':'login');setError('');setMessage('')}}
              style={{background:'none',border:'none',color:'#24c78e',fontSize:'12px',cursor:'pointer',fontFamily:'inherit'}}>
              {mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
