import { useEffect, useState, type ReactNode } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import logo from '../assets/logo.png'
import seed from '../data/seed.json'
import { ConvItem, Thread } from '../components/Inbox'
import { Badge, DA, Icon, type IconName } from '../components/ui'
import { useApp } from '../store'
import type { Conv } from '../types'

export function PubFrame() {
  const { pathname } = useLocation()
  useEffect(() => { document.getElementById('app')?.scrollTo(0, 0) }, [pathname])
  return <div id="app" className="pub"><Outlet /></div>
}

const LINKS: [string, string][] = [['/features', 'Features'], ['/how-it-works', 'How it works'], ['/pricing', 'Pricing'], ['/faq', 'FAQ']]
function Frame({ children }: { children: ReactNode }) {
  const nav = useNavigate(), { pathname } = useLocation(), { auth, signOut } = useApp()
  return (
    <div className="main pubw">
      <header className="nv"><div className="in">
        <button className="logo" onClick={() => nav('/')} aria-label="CommandIA home"><img src={logo} alt="commandia" style={{ width: 130 }} /></button>
        <nav className="nl" aria-label="Site">{LINKS.map(([to, t]) => <button key={to} onClick={() => nav(to)} aria-current={pathname === to ? 'page' : undefined}>{t}</button>)}</nav>
        {auth.user ? <><button className="btn pr" onClick={() => nav('/app')}>Open dashboard</button><button className="btn" onClick={async () => { await signOut(); nav('/') }}>Sign out</button></>
          : <><button className="btn" onClick={() => nav('/signin')}>Sign in</button><button className="btn pr" onClick={() => nav('/signup')}>Get started</button></>}
      </div></header>
      {children}
      <footer className="dk ft"><div className="in">
        <div><img src={logo} alt="commandia" style={{ width: 130, borderRadius: 8 }} /><p className="sm" style={{ marginTop: 10, maxWidth: 300 }}>Demo prototype. Authentication, integrations and billing are simulated.</p></div>
        <div>{LINKS.map(([to, t]) => <button key={to} onClick={() => nav(to)}>{t}</button>)}</div>
        <div><button onClick={() => nav('/signin')}>Sign in</button><button onClick={() => nav('/signup')}>Get started</button></div>
      </div></footer>
    </div>
  )
}

const Head = ({ e, t, d }: { e: string; t: string; d: string }) => <div className="sh"><div className="eb mg">{e}</div><h2>{t}</h2><p>{d}</p></div>
type F = [IconName, string, string, string[]?]
const Cards = ({ items }: { items: F[] }) => (
  <div className="g3">{items.map((f) => <div className="card" key={f[1]}><span className="it"><Icon n={f[0]} s={20} /></span><h3>{f[1]}</h3><p className="sm">{f[2]}</p>{f[3] && <ul>{f[3].map((x) => <li key={x}>{x}</li>)}</ul>}</div>)}</div>
)
const FE: F[] = [
  ['inbox', 'Smart Inbox', 'Follow incoming Instagram DMs in one place.', ['Search and filter: all, AI handled, needs attention, human handled', 'Conversations needing a human are prioritized', 'Customer context and detected intent beside the chat']],
  ['ai', 'AI conversation management', 'The AI replies using your catalog and business rules.', ['Every automatic reply is labelled as such', 'Customer, AI and human messages look different at a glance']],
  ['hand', 'Human Takeover', 'Step in when the AI flags a conversation.', ['Pause the AI for one conversation and reply yourself', 'Persistent mode indicator and confirmations', 'Resume AI whenever you are done']],
  ['ord', 'Order management', 'Customer details collected in chat become orders.', ['Name, phone, Wilaya, delivery type and address', 'Orders are never confirmed automatically', 'Actions follow the order status']],
  ['box', 'Product catalog', 'Keep the products the AI talks about up to date.', ['Add and edit products and prices', 'Track stock and availability']],
  ['rules', 'Business rules', 'Tell the AI how your business works.', ['Delivery zones and fees, business hours', 'AI behavior, tone of voice, pricing and discounts']],
  ['plug', 'AI settings & integrations', 'Control automation and connect your account.', ['Global AI Auto-Pilot switch, separate from each conversation mode', 'Instagram Business connection (simulated in this prototype)']],
]
const ST = [['Create your account', 'Sign up with email (demo authentication in this prototype).'], ['Set up your business', 'Business name, industry and currency.'], ['Connect Instagram', 'Link your Instagram Business account. Simulated in this prototype.'], ['Let the AI reply', 'It answers using your catalog and business rules.'], ['Step in when needed', 'Take over flagged conversations, then resume the AI.'], ['Manage orders', 'Review collected details, then confirm, ship and deliver.']]
const Steps = () => <div className="g3">{ST.map((x, i) => <div className="card" key={x[0]}><span className="nm">{i + 1}</span><h3>{x[0]}</h3><p className="sm">{x[1]}</p></div>)}</div>
function Fin() {
  const nav = useNavigate()
  return <section className="dk ps" style={{ textAlign: 'center' }}><div className="in"><h2 style={{ fontSize: 'clamp(26px,4vw,40px)' }}>Ready to turn conversations into orders?</h2><p style={{ color: '#CDBDF5', margin: '10px 0 24px' }}>Try the demo workspace. No payment, no real account.</p><div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}><button className="btn pr" onClick={() => nav('/signup')}>Get Started</button><button className="btn" onClick={() => nav('/signin')}>Sign in</button></div></div></section>
}

export function Home() {
  const nav = useNavigate(), convs = seed.convs as unknown as Conv[]
  return (
    <Frame>
      <section className="dk hero"><div className="in">
        <div className="eb mg" style={{ color: 'var(--r)' }}>L'IA qui vend pour vous</div>
        <h1 style={{ marginTop: 10 }}>Turn every message into an <span className="acc">order.</span></h1>
        <p className="lead">CommandIA manages your customer conversations from social media. The AI replies, you step in when it matters, and orders end up organized in one dashboard.</p>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}><button className="btn pr" onClick={() => nav('/signup')}>Get Started</button><button className="btn" onClick={() => nav('/features')}>Explore Features</button></div>
        <div className="main pvw" aria-hidden="true" {...({ inert: '' } as object)}>
          <section className="list">{convs.map((c) => <ConvItem key={c.id} c={c} active={c.id === 1} onClick={() => undefined} />)}</section>
          <section className="thread"><Thread c={convs[0]} aiOn /></section>
        </div>
      </div></section>
      <section className="ps"><div className="in"><Head e="The problem" t="Replying to every DM by hand does not scale" d="Slow replies and missed messages mean missed sales. CommandIA keeps conversations moving and keeps you in control." />
        <Cards items={[['inbox', 'Fewer missed messages', 'The AI answers customers while you are busy.'], ['hand', 'You stay in control', 'Take over any conversation and resume the AI when done.'], ['ord', 'Orders, organized', 'Customer details are collected and never confirmed without you.']]} /></div></section>
      <section className="ps w"><div className="in"><Head e="Features" t="Everything in one workspace" d="What the product does today." /><Cards items={FE.slice(0, 6).map((f) => [f[0], f[1], f[2]] as F)} /><p style={{ textAlign: 'center', marginTop: 24 }}><button className="btn" onClick={() => nav('/features')}>See all features</button></p></div></section>
      <section className="ps"><div className="in"><Head e="How it works" t="From sign-up to your first order" d="Six steps." /><Steps /></div></section>
      <Fin />
    </Frame>
  )
}
export const Features = () => <Frame><section className="ps"><div className="in"><Head e="Features" t="What CommandIA does" d="Capabilities available in the product today. Instagram is simulated in this prototype." /><Cards items={FE} /></div></section><Fin /></Frame>
export const How = () => <Frame><section className="ps"><div className="in"><Head e="How it works" t="Your journey with CommandIA" d="From setup to daily use." /><Steps /></div></section><Fin /></Frame>

const PLANS: { n: string; p: number; d: string; f: string[]; pop?: boolean }[] = [
  { n: 'Starter', p: 2900, d: 'For a single shop getting started.', f: ['Smart Inbox', 'Human Takeover', 'Instagram integration (simulated)', 'Up to 20 products'] },
  { n: 'Growth', p: 6900, d: 'For growing sales volume.', f: ['Everything in Starter', 'Up to 100 products', 'Full business rules', 'Priority email support'], pop: true },
  { n: 'Scale', p: 0, d: 'For larger teams.', f: ['Everything in Growth', 'Custom catalog size', 'Custom team seats', 'Dedicated support'] },
]
const CMP = [['Smart Inbox', '✓', '✓', '✓'], ['Human Takeover', '✓', '✓', '✓'], ['Order management', '✓', '✓', '✓'], ['Product catalog', 'Up to 20', 'Up to 100', 'Custom'], ['Business rules', 'Basic', 'Full', 'Full'], ['Team seats', '1', '3', 'Custom'], ['Support', 'Email', 'Priority email', 'Dedicated']]
export function Pricing() {
  const nav = useNavigate(), [y, setY] = useState(false)
  return (
    <Frame><section className="ps"><div className="in">
      <Head e="Pricing" t="Simple plans" d="Illustrative prices and limits for demonstration. Not final, and no payment processing exists in this prototype." />
      <div className="chips" style={{ justifyContent: 'center', margin: '-16px 0 24px' }}><button className="chip" aria-pressed={!y} onClick={() => setY(false)}>Monthly</button><button className="chip" aria-pressed={y} onClick={() => setY(true)}>Yearly (illustrative −20%)</button></div>
      <div className="g3">{PLANS.map((p) => (
        <div key={p.n} className={`card pt ${p.pop ? 'pop' : ''}`}>{p.pop && <Badge k="ok" i="check">Most popular</Badge>}<h3>{p.n}</h3>
          <div className="pr0">{p.p ? DA(y ? Math.round(p.p * 0.8) : p.p) : 'Custom'}</div><span className="sm">{p.p ? 'per month, illustrative' : 'contact sales (simulated)'}</span><p className="sm">{p.d}</p>
          <ul>{p.f.map((x) => <li key={x}><Icon n="check" s={14} /> {x}</li>)}</ul>
          <button className={`btn ${p.pop ? 'pr' : ''}`} onClick={() => nav('/signup')}>{p.p ? 'Get Started' : 'Contact us'}</button></div>
      ))}</div>
      <div className="card" style={{ marginTop: 24, overflowX: 'auto', padding: 8 }}><table className="tb"><tbody>
        <tr><th>Compare (illustrative)</th><th>Starter</th><th>Growth</th><th>Scale</th></tr>
        {CMP.map((r) => <tr key={r[0]}><td>{r[0]}</td>{r.slice(1).map((c, i) => <td key={i}>{c === '✓' ? <><Icon n="check" s={16} /><span style={{ position: 'absolute', left: -9999 }}>Included</span></> : c}</td>)}</tr>)}
      </tbody></table></div>
    </div></section><Fin /></Frame>
  )
}
const QA = [['How long does setup take?', 'You create an account, enter your business details and connect Instagram. In this prototype the connection is simulated.'], ['What does the AI do?', 'It replies to customer messages using your catalog and business rules. Automatic replies are labelled in the conversation.'], ['Can I step in myself?', 'Yes. Conversations the AI flags need a human, and you can take over any chat, reply manually, then resume the AI.'], ['Does the AI confirm orders on its own?', 'No. Collected customer details never confirm an order automatically; you confirm it.'], ['Which accounts can I connect?', 'Instagram Business is the channel shown in this prototype, and the connection is simulated. Other channels are not available.'], ['How does billing work?', 'Plans shown are illustrative. No payment processing is implemented in this prototype.'], ['Is this a real account?', 'No. Sign-in and sign-up are a demo flow and no real data is stored on a server.']]
export const Faq = () => <Frame><section className="ps"><div className="in" style={{ maxWidth: 760 }}><Head e="FAQ" t="Frequently asked questions" d="Straight answers about the prototype." />{QA.map((q) => <details key={q[0]}><summary>{q[0]}</summary><p>{q[1]}</p></details>)}</div></section><Fin /></Frame>
