import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import logo from '../assets/logo.png'
import sym from '../assets/sym.png'
import { Icon } from '../components/ui'
import { useApp } from '../store'

export function AuthPage({ mode }: { mode: 'in' | 'up' }) {
  const nav = useNavigate(), { auth, signIn, signUp, toast } = useApp(), up = mode === 'up', [busy, setBusy] = useState(false)
  if (auth.user) return <Navigate to={auth.done ? '/app' : '/onboarding'} replace />
  const go = async (name: string, email: string, pw: string) => {
    setBusy(true)
    try { if (up) { await signUp(name, email, pw); nav('/onboarding') } else { await signIn(email, pw); nav('/app') } } catch { toast(up ? 'Could not create this account' : 'Invalid email or password') } finally { setBusy(false) }
  }
  const submit = (e: FormEvent<HTMLFormElement>) => { e.preventDefault(); const d = new FormData(e.currentTarget); void go(String(d.get('name') ?? ''), String(d.get('email')), String(d.get('password'))) }
  return (
    <div className="main pubw dk au"><div style={{ width: '100%', maxWidth: 420 }}>
      <button className="logo" onClick={() => nav('/')} style={{ marginBottom: 20 }} aria-label="Back to website"><img src={logo} alt="commandia" style={{ width: 150 }} /></button>
      <div className="card" style={{ padding: 24, color: 'var(--n)' }}>
        <h1 style={{ fontSize: 26 }}>{up ? 'Create your account' : 'Welcome back'}</h1>
        <p className="sm" style={{ margin: '6px 0 10px' }}>{up ? 'Start setting up your workspace.' : 'Sign in to open your dashboard.'}</p>
        <div className="bn in" style={{ margin: '0 0 6px', padding: '8px 12px' }}><div style={{ minWidth: 0 }}>Local demo account. Your workspace stays on this machine.</div></div>
        <form onSubmit={submit}>
          {up && <><label htmlFor="an">Full name</label><input id="an" name="name" required autoComplete="name" /></>}
          <label htmlFor="ae">Email</label><input id="ae" name="email" type="email" required autoComplete="email" />
          <label htmlFor="ap">Password</label><input id="ap" name="password" type="password" required minLength={6} autoComplete={up ? 'new-password' : 'current-password'} />
          <button className="btn pr" disabled={busy} style={{ width: '100%', marginTop: 16 }}>{up ? 'Create account' : 'Sign in'}</button>
        </form>
        <button className="btn" disabled={busy} style={{ width: '100%', marginTop: 8 }} onClick={() => void go('Demo User', 'demo@commandia.dz', 'demo1234')}>Continue with Google (simulated)</button>
        <p className="sm" style={{ marginTop: 14, textAlign: 'center' }}>{up ? 'Already have an account?' : 'New to CommandIA?'} <button style={{ color: 'var(--m)', fontWeight: 500, textDecoration: 'underline', minHeight: 44 }} onClick={() => nav(up ? '/signin' : '/signup')}>{up ? 'Sign in' : 'Get started'}</button></p>
      </div>
    </div></div>
  )
}

export function Onboarding() {
  const nav = useNavigate(), { finishOnboarding, setIG } = useApp(), [s, setS] = useState(1), [name, setName] = useState('Luna Concept Store')
  const next = () => setS(s + 1)
  const B = ({ t, f }: { t: string; f: () => void }) => <button className="btn pr" style={{ width: '100%', marginTop: 14 }} onClick={f}>{t}</button>
  return (
    <div id="app" className="pub"><div className="ob"><div className="mb" role="dialog" aria-modal="true" aria-label="Onboarding">
      <div className="dots">{[1, 2, 3].map((i) => <i key={i} className={i <= s ? 'on' : ''} />)}</div>
      {s === 1 && <><h1>Set up your business</h1><label htmlFor="bn">Business name</label><input id="bn" value={name} onChange={(e) => setName(e.target.value)} /><label htmlFor="bi">Industry</label><select id="bi"><option>Fashion &amp; Accessories</option><option>Food &amp; Beverage</option></select><label htmlFor="bc">Currency</label><select id="bc"><option>Algerian Dinar (DA)</option></select><B t="Continue" f={next} /></>}
      {s === 2 && <><h1>Connect Instagram</h1><p className="sm" style={{ marginTop: 8 }}>Simulated step. You can skip it and connect later in Integrations.</p><B t="Connect (simulated)" f={() => { void setIG(true); next() }} /><button className="btn" style={{ width: '100%', marginTop: 8 }} onClick={next}>Skip for now</button></>}
      {s === 3 && <><div style={{ textAlign: 'center' }}><img src={sym} width={72} alt="" style={{ borderRadius: 16 }} /><h1 style={{ marginTop: 12 }}>You are all set!</h1><p className="sm" style={{ marginTop: 6 }}>Your workspace is ready.</p></div><B t="Go to dashboard" f={() => { finishOnboarding(); nav('/app') }} /></>}
      <button className="sm" style={{ marginTop: 10, minHeight: 36 }} onClick={() => nav(-1)}><Icon n="back" s={12} /> Back</button>
    </div></div></div>
  )
}
