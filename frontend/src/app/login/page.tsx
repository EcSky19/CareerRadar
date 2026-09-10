'use client'

import { useState } from 'react'
import { createClient } from '@supabase/supabase-js'
import { Zap } from 'lucide-react'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

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
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', -apple-system, sans-serif; }
        .login-input {
          width: 100%;
          padding: 11px 14px;
          background: #161b24;
          border: 1px solid #242d3d;
          border-radius: 8px;
          color: #eef1f7;
          font-size: 14px;
          font-family: 'Inter', sans-serif;
          outline: none;
          transition: border-color 0.2s;
        }
        .login-input:focus { border-color: #24c78e; }
        .login-input::placeholder { color: #3d4d63; }
        .login-btn {
          width: 100%;
          padding: 11px;
          background: #24c78e;
          border: none;
          border-radius: 8px;
          color: white;
          font-size: 14px;
          font-weight: 600;
          font-family: 'Inter', sans-serif;
          cursor: pointer;
          transition: opacity 0.2s, transform 0.1s;
          letter-spacing: 0.01em;
        }
        .login-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
        .login-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .toggle-btn {
          background: none;
          border: none;
          color: #24c78e;
          font-size: 13px;
          font-family: 'Inter', sans-serif;
          cursor: pointer;
          font-weight: 500;
        }
        .toggle-btn:hover { text-decoration: underline; }
      `}</style>

      <div style={{minHeight:'100vh',background:'#0b0e14',display:'flex',alignItems:'center',justifyContent:'center',padding:'0 16px'}}>
        <div style={{width:'100%',maxWidth:'400px'}}>

          {/* Logo */}
          <div style={{textAlign:'center',marginBottom:'36px'}}>
            <div style={{width:'48px',height:'48px',background:'linear-gradient(135deg,#24c78e,#1aad7a)',borderRadius:'12px',display:'inline-flex',alignItems:'center',justifyContent:'center',marginBottom:'16px',boxShadow:'0 4px 20px rgba(36,199,142,0.25)'}}>
              <Zap size={24} color="white" strokeWidth={2.5} />
            </div>
            <h1 style={{color:'#eef1f7',fontSize:'24px',fontWeight:700,letterSpacing:'-0.5px',fontFamily:'Inter,sans-serif'}}>Career Radar</h1>
            <p style={{color:'#56647a',fontSize:'14px',marginTop:'6px',fontFamily:'Inter,sans-serif'}}>
              {mode === 'login' ? 'Sign in to your account' : 'Create your account'}
            </p>
          </div>

          {/* Card */}
          <div style={{background:'#111520',border:'1px solid #1e2736',borderRadius:'16px',padding:'32px'}}>

            {/* Private Beta Banner (signup only) */}
            {mode === 'signup' && (
              <div style={{background:'rgba(255,193,7,0.06)',border:'1px solid rgba(255,193,7,0.2)',borderRadius:'10px',padding:'14px 16px',marginBottom:'24px',textAlign:'center'}}>
                <div style={{fontSize:'14px',fontWeight:600,color:'#ffc107',marginBottom:'5px',fontFamily:'Inter,sans-serif'}}>🔒 Private Beta</div>
                <div style={{fontSize:'13px',color:'#7a8899',lineHeight:'1.6',fontFamily:'Inter,sans-serif'}}>Career Radar is currently invite-only and still being tested. Public access coming soon.</div>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div style={{marginBottom:'18px'}}>
                <label style={{display:'block',fontSize:'13px',color:'#8d99b0',marginBottom:'7px',fontWeight:500,fontFamily:'Inter,sans-serif'}}>Email</label>
                <input className="login-input" type="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="you@example.com" />
              </div>

              <div style={{marginBottom:'22px'}}>
                <label style={{display:'block',fontSize:'13px',color:'#8d99b0',marginBottom:'7px',fontWeight:500,fontFamily:'Inter,sans-serif'}}>Password</label>
                <input className="login-input" type="password" value={password} onChange={e=>setPassword(e.target.value)} required placeholder="••••••••" />
              </div>

              {error && (
                <div style={{background:'rgba(224,82,82,0.08)',border:'1px solid rgba(224,82,82,0.2)',borderRadius:'8px',padding:'11px 14px',color:'#e05252',fontSize:'13px',marginBottom:'16px',fontFamily:'Inter,sans-serif'}}>{error}</div>
              )}
              {message && (
                <div style={{background:'rgba(36,199,142,0.08)',border:'1px solid rgba(36,199,142,0.2)',borderRadius:'8px',padding:'11px 14px',color:'#24c78e',fontSize:'13px',marginBottom:'16px',fontFamily:'Inter,sans-serif'}}>{message}</div>
              )}

              <button className="login-btn" type="submit" disabled={loading}>
                {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            </form>

            <div style={{textAlign:'center',marginTop:'20px'}}>
              <span style={{color:'#56647a',fontSize:'13px',fontFamily:'Inter,sans-serif'}}>
                {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
              </span>
              <button className="toggle-btn" onClick={()=>{setMode(mode==='login'?'signup':'login');setError('');setMessage('')}}>
                {mode === 'login' ? 'Sign up' : 'Sign in'}
              </button>
            </div>
          </div>

        </div>
      </div>
    </>
  )
}
