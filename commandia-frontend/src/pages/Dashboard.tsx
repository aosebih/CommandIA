import { useNavigate } from 'react-router-dom'
import { Badge, DA, Icon, Modal, PageHead, Switch, initials, type IconName } from '../components/ui'
import { useApp } from '../store'
import { useState, type ReactNode } from 'react'

export function Overview() {
  const nav = useNavigate(), { convs, orders } = useApp()
  const attn = convs.filter((c) => c.m === 'attn'), aw = orders.filter((o) => o.st === 'await')
  return (
    <div className="pg">
      <PageHead title="Good morning, Naila" desc="Here’s what needs your attention across Luna Concept Store." cta={<button className="btn pr" onClick={() => nav('/app/inbox')}><Icon n="inbox" s={18} />Open Smart Inbox</button>} />
      <div className="st">
        <div className="card"><span className="sm">Active conversations</span><b>{convs.length}</b><span className="up">+8 today</span></div>
        <div className="card hl"><span className="sm">Need attention</span><b>{attn.length}</b><span style={{ color: '#8A5A00' }}>Review now</span></div>
        <div className="card"><span className="sm">Orders today</span><b>{orders.length}</b><span className="up">{DA(orders.reduce((a, o) => a + o.tot, 0))}</span></div>
        <div className="card"><span className="sm">AI resolution rate</span><b>92%</b><span className="up">Last 7 days</span></div>
      </div>
      <div className="card" style={{ marginTop: 16, padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div><h2 style={{ fontSize: 22 }}>Needs your attention</h2><p className="sm">Conversations and orders waiting for review. Demonstration data.</p></div>
          <button className="btn" onClick={() => nav('/app/inbox')}>View inbox</button>
        </div>
        {attn.map((c) => (
          <button key={c.id} className="ar" onClick={() => nav(`/app/inbox/${c.id}`)}><span className="av">{initials(c.n)}</span><span style={{ flex: 1 }}><b style={{ fontWeight: 700 }}>{c.n}: {c.intent}</b><br /><span className="sm">{c.why}</span></span><Badge k="wa" i="warn">Intervention needed</Badge></button>
        ))}
        {aw.map((o) => (
          <button key={o.id} className="ar" onClick={() => nav(`/app/orders/${o.id}`)}><span className="av">#</span><span style={{ flex: 1 }}><b style={{ fontWeight: 700 }}>Order #{o.id} awaiting confirmation</b><br /><span className="sm">{o.name} · {o.wil}</span></span><Badge k="in" i="clock">Review</Badge></button>
        ))}
      </div>
    </div>
  )
}

const Row = ({ i, t, d, tag }: { i: IconName; t: string; d: string; tag: ReactNode }) => (
  <div style={{ display: 'flex', gap: 14, alignItems: 'center', padding: '16px 0', borderTop: '1px solid var(--bd)' }}><span className="it"><Icon n={i} s={20} /></span><div style={{ flex: 1 }}><b style={{ fontWeight: 700 }}>{t}</b><div className="sm">{d}</div></div>{tag}</div>
)

export function AiSettings() {
  const { ai, ig, convs, toggleAI, toast } = useApp(), n = (m: string) => convs.filter((c) => c.m === m).length
  return (
    <div className="pg">
      <PageHead title="AI Settings" desc="Control how CommandIA responds across your connected social accounts." />
      <div className="rg" style={{ alignItems: 'start' }}>
        <div className="card" style={{ padding: 24 }}>
          <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
            <span className="it"><Icon n="ai" s={20} /></span>
            <div style={{ flex: 1 }}><h2 style={{ fontSize: 20 }}>Global AI Auto-Pilot</h2><p className="sm" style={{ marginTop: 6 }}>When enabled, the AI may respond to eligible conversations on all connected accounts. Conversation-level Manual Mode always takes priority.</p></div>
            <Switch on={ai} label="Global AI Auto-Pilot" onClick={() => void toggleAI().then(() => toast(ai ? 'Global AI off: manual mode for all chats' : 'Global AI: Auto-Pilot on'))} />
          </div>
          <p style={{ marginTop: 16 }}>{ai ? <Badge k="ok" i="check">Active globally</Badge> : <Badge k="wa" i="warn">Off · manual mode</Badge>} <span className="sm">Applies to {ig === 'on' ? 1 : 0} connected social account</span></p>
        </div>
        <div className="card" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 20, marginBottom: 12 }}>Understand the three controls</h2>
          <Row i="ai" t="Global AI status" d="Master control for automatic replies across the workspace." tag={ai ? <Badge k="ok" i="check">On</Badge> : <Badge k="wa" i="warn">Off</Badge>} />
          <Row i="user" t="Conversation mode" d={`AI Active or Manual Mode for one customer thread. Now: ${n('ai')} AI, ${n('attn')} need human, ${n('manual')} manual.`} tag={<Badge k="in" i="user">Per chat</Badge>} />
          <Row i="plug" t="Social connection" d="Whether CommandIA can access a social account in this demo." tag={ig === 'on' ? <Badge k="ok" i="check">Connected</Badge> : <Badge k="mu" i="x">Not connected</Badge>} />
        </div>
      </div>
    </div>
  )
}

export function Integrations() {
  const { ig, setIG, toast } = useApp(), [ask, setAsk] = useState(false), on = ig === 'on', bz = ig === 'busy'
  return (
    <div className="pg">
      <PageHead title="Integrations" desc="Manage simulated social channels connected to this workspace." />
      <div className="bn in" style={{ margin: '0 0 16px' }}><Icon n="warn" s={20} /><div><strong>Prototype environment.</strong> No real social account or customer data is connected.</div></div>
      <div className="card" style={{ padding: 24 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="ig" style={on ? undefined : { filter: 'grayscale(1)', opacity: 0.6 }}><Icon n="plug" s={30} /></span>
          <div style={{ flex: 1, minWidth: 200 }}><h2 style={{ fontSize: 20 }}>Instagram Business</h2><p className="sm">Receive DMs, supervise AI replies, and collect order details.</p></div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {on ? <><button className="btn" onClick={() => void setIG(true).then(() => toast('Instagram reconnected (simulated)'))}>Reconnect</button><button className="btn dg" onClick={() => setAsk(true)}>Disconnect</button></>
              : <button className="btn pr" disabled={bz} onClick={() => void setIG(true).then(() => toast('Instagram connected (simulated)'))}>Connect Instagram Business</button>}
          </div>
        </div>
        {on || bz ? (
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', border: '1px solid var(--bd)', borderRadius: 16, padding: 14, marginTop: 18, flexWrap: 'wrap' }}>
            <span className="lc" style={{ background: '#F1EBFF', color: 'var(--v)' }}>LC</span>
            <div style={{ flex: 1 }}><b style={{ fontWeight: 700 }}>@luna.concept.dz</b><div className="sm">Instagram Business · Simulated</div></div>
            {bz ? <Badge k="wa" i="clock">Connecting…</Badge> : <Badge k="ok" i="check">Active · Connected</Badge>}
          </div>
        ) : <p className="sm" style={{ marginTop: 16 }}><Badge k="mu" i="x">Not connected</Badge> Connect your account so the AI can answer your DMs (simulated).</p>}
      </div>
      {ask && (
        <Modal title="Disconnect Instagram?" onClose={() => setAsk(false)}>
          <p>The AI will stop receiving and answering messages from this account. (Simulated)</p>
          <div className="ac"><button className="btn" onClick={() => setAsk(false)}>Cancel</button><button className="btn dg" onClick={() => { setAsk(false); void setIG(false).then(() => toast('Instagram disconnected (simulated)')) }}>Disconnect</button></div>
        </Modal>
      )}
    </div>
  )
}
