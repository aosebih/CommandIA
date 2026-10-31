import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import logo from '../assets/logo.png'
import sym from '../assets/sym.png'
import { useApp } from '../store'
import { Badge, Icon, Switch, type IconName } from './ui'

const NAV: [string, string, IconName][] = [
  ['/app', 'Overview', 'home'], ['/app/inbox', 'Smart Inbox', 'inbox'], ['/app/orders', 'Orders', 'ord'], ['/app/catalog', 'Product Catalog', 'box'],
  ['/app/rules', 'Business Rules', 'rules'], ['/app/ai-settings', 'AI Settings', 'ai'], ['/app/integrations', 'Integrations', 'plug'],
]
const TABS: [string, string, IconName][] = [['/app', 'Home', 'home'], ['/app/inbox', 'Inbox', 'inbox'], ['/app/orders', 'Orders', 'ord'], ['/app/catalog', 'Catalog', 'box'], ['/app/ai-settings', 'Settings', 'rules']]
const on = (path: string, to: string) => (to === '/app' ? path === '/app' : path.startsWith(to))

export default function AppShell() {
  const { convs, ai, toggleAI, signOut, toast } = useApp()
  const nav = useNavigate(), { pathname } = useLocation(), [menu, setMenu] = useState(false)
  const attn = convs.filter((c) => c.m === 'attn').length
  useEffect(() => setMenu(false), [pathname])
  const title = NAV.find((n) => on(pathname, n[0]))?.[1] ?? 'Overview'
  const out = async () => { await signOut(); nav('/') }
  const Menu = () => (
    <div className="menu">
      <button onClick={() => nav('/onboarding')}>Replay onboarding</button>
      <button onClick={() => nav('/features')}>Visit website</button>
      <button onClick={out}>Sign out</button>
    </div>
  )
  return (
    <div id="app">
      <nav className="side" aria-label="Main">
        <div className="logo"><img src={logo} alt="commandia, L'IA qui vend pour vous" /></div>
        <button className="ws" onClick={() => toast('Workspace selector (simulated)')} aria-label="Workspace selector">
          <span style={{ display: 'flex', gap: 10, alignItems: 'center' }}><span className="lc">LC</span><span><span className="sm" style={{ display: 'block', color: 'var(--r)' }}>Workspace</span><b style={{ fontWeight: 500 }}>Luna Concept Store</b></span></span><span aria-hidden="true">▾</span>
        </button>
        <div className="nav">
          {NAV.map(([to, t, i]) => (
            <button key={to} onClick={() => nav(to)} aria-current={on(pathname, to) ? 'page' : undefined}>
              <Icon n={i} s={18} />{t}{to === '/app/inbox' && attn > 0 && <span className="bdg" aria-label={`${attn} need attention`}>{attn}</span>}
            </button>
          ))}
        </div>
        <div className="ai" style={{ marginTop: 'auto' }}>
          <span style={{ color: 'var(--r)' }}><Icon n="ai" s={22} /></span>
          <div style={{ flex: 1 }}><b>AI Auto-Pilot</b><div className="sm">{ai ? 'Active globally' : 'Off · manual mode'}</div></div>
          <Switch on={ai} label="Global AI Auto-Pilot" onClick={() => void toggleAI().then(() => toast(ai ? 'Global AI off: manual mode for all chats' : 'Global AI: Auto-Pilot on'))} />
        </div>
        <button className="hp" onClick={() => toast('Help & support (simulated)')}>? &nbsp;Help &amp; support</button>
        <button className="vo" onClick={() => nav('/onboarding')}>View onboarding</button>
      </nav>
      <main className="main">
        <header className="top">
          <div><div className="eb mg">Luna Concept Store</div><div className="tt">{title}</div></div>
          <div className="tr">
            <button className={`b ${ai ? 'ok' : 'wa'}`} style={{ minHeight: 36, padding: '0 12px' }} onClick={() => nav('/app/ai-settings')}>
              {ai ? <><Icon n="check" s={14} />Global AI active</> : <><Icon n="warn" s={14} />Global AI off</>}
            </button>
            <button className="ib" onClick={() => toast('No new alerts (simulated)')} aria-label="Alerts"><Icon n="warn" s={20} /></button>
            <button className="pf" onClick={() => setMenu(!menu)} aria-label="Profile menu"><span className="av">NB</span><span><b style={{ fontWeight: 700, display: 'block', lineHeight: 1.2 }}>Naila B.</b><span className="sm">Administrator</span></span>▾</button>
            {menu && <Menu />}
          </div>
        </header>
        <div className="mob">
          <img src={sym} alt="commandia" style={{ borderRadius: 8, background: 'var(--lg)' }} />
          <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>{ai ? <Badge k="ok" i="ai">AI on</Badge> : <Badge k="wa" i="warn">AI off</Badge>}<button className="ib" onClick={() => setMenu(!menu)} aria-label="Profile menu">NB</button></span>
          {menu && <Menu />}
        </div>
        <Outlet />
      </main>
      <nav className="tabs" aria-label="Main">
        {TABS.map(([to, t, i]) => (
          <button key={to} onClick={() => nav(to)} aria-current={on(pathname, to) || (to === '/app/ai-settings' && (on(pathname, '/app/rules') || on(pathname, '/app/integrations'))) ? 'page' : undefined}><Icon n={i} s={22} />{t}</button>
        ))}
      </nav>
    </div>
  )
}
