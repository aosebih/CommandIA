import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import type { Conv, Msg, Order } from '../types'
import { Badge, DA, Icon, MODE, OS, initials } from './ui'

export function ConvItem({ c, active, onClick }: { c: Conv; active: boolean; onClick: () => void }) {
  const l = c.msgs[c.msgs.length - 1], md = MODE[c.m]
  return (
    <button className={`ci ${c.m === 'attn' ? 'attn' : ''}`} aria-current={active} onClick={onClick}>
      <span className="av" aria-hidden="true">{initials(c.n)}</span>
      <span style={{ minWidth: 0, flex: 1 }}>
        <span className="t"><span>{c.n}</span><span className="sm">{c.ts}</span></span>
        <span className="sn" style={{ display: 'block' }}>{l.w === 'a' ? 'AI: ' : l.w === 'h' ? 'You: ' : ''}{l.t}</span>
        <span style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 4 }}>
          <Badge k={md[0]} i={md[1]}>{md[2]}</Badge>{c.un ? <><span className="ud" /><span className="sm">Unread</span></> : null}
        </span>
      </span>
    </button>
  )
}

const Bubble = ({ m, c }: { m: Msg; c: Conv }) => (
  <div className={`m ${m.w}`}>
    <div className="lb">
      {m.w === 'c' ? <><Icon n="user" s={12} />{c.n} · Customer</> : m.w === 'a' ? <><Icon n="ai" s={12} />AI Assistant<span className="tag">Automatic reply</span></> : <><Icon n="hand" s={12} />You · Human Agent</>} · {m.time}
    </div>
    <div className="bb">{m.t}</div>
  </div>
)

interface TP { c: Conv; aiOn: boolean; showBack?: boolean; showDetails?: boolean; onBack?: () => void; onDetails?: () => void; onTake?: () => void; onResume?: () => void; onSend?: (t: string) => Promise<void>; onSettings?: () => void }
export function Thread({ c, aiOn, showBack, showDetails, onBack, onDetails, onTake, onResume, onSend, onSettings }: TP) {
  const md = MODE[c.m], manual = c.m === 'manual', end = useRef<HTMLDivElement>(null)
  const [draft, setDraft] = useState(''), [sending, setSending] = useState(false)
  useEffect(() => { const e = end.current; if (e) e.scrollTop = e.scrollHeight }, [c.id, c.msgs.length])
  useEffect(() => setDraft(''), [c.id])
  const submit = async (e?: FormEvent) => {
    e?.preventDefault(); const t = draft.trim(); if (!t || !manual || !onSend || sending) return
    setSending(true); try { await onSend(t); setDraft('') } finally { setSending(false) }
  }
  const key = (e: KeyboardEvent) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void submit() } }
  return (
    <>
      <div className="th">
        {showBack && <button className="btn" style={{ minHeight: 44, padding: '0 10px' }} onClick={onBack} aria-label="Back to conversations"><Icon n="back" s={18} /></button>}
        <div className="who"><h2>{c.n}</h2><div className="sm">{c.h} · Instagram</div></div>
        <div className={`mbx ${md[0]}`}><span className="eb">Conversation mode</span><b><Icon n={md[1]} s={14} /> {md[2]}</b></div>
        {manual ? <button className="btn" onClick={onResume}>Resume AI</button> : <button className={`btn ${c.m === 'attn' ? 'pr' : ''}`} onClick={onTake}><Icon n="hand" />Take over</button>}
        {showDetails && <button className="btn" onClick={onDetails}>Details</button>}
      </div>
      {c.m === 'attn' && <div className="bn wa" role="alert"><Icon n="warn" s={22} /><div><strong>Human intervention required</strong><br />{c.why}</div><button className="btn pr" onClick={onTake}>Pause AI &amp; take over</button></div>}
      {manual && <div className="bn in"><Icon n="user" s={22} /><div><strong>Manual Mode · AI paused for this conversation</strong><br />Anything you type is sent directly by you. The AI will not reply here.</div><button className="btn" onClick={onResume}>Resume AI</button></div>}
      {c.m === 'ai' && !aiOn && <div className="bn wa"><Icon n="warn" s={22} /><div><strong>Global AI is off</strong><br />The AI will not reply in any conversation.</div><button className="btn" onClick={onSettings}>AI Settings</button></div>}
      <div className="msgs" ref={end} tabIndex={0} aria-label="Messages">{c.msgs.map((m, i) => <Bubble key={i} m={m} c={c} />)}</div>
      <form className="cmp" onSubmit={submit}>
        <textarea aria-label="Message" value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={key} disabled={!manual}
          placeholder={manual ? 'Type a reply as yourself…' : 'AI is handling this chat. Take over to type.'} />
        <button className="btn pr" disabled={!manual || sending} aria-label="Send"><Icon n="send" s={18} /><span className="hm2">Send</span></button>
      </form>
    </>
  )
}

export function Ctx({ c, order, onOrder, onTake, onResume, toast }: { c: Conv; order?: Order; onOrder: () => void; onTake: () => void; onResume: () => void; toast: (m: string) => void }) {
  const manual = c.m === 'manual'
  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><h2>Customer context</h2><span className="b mu">Demo data</span></div>
      <div style={{ textAlign: 'center', margin: '16px 0' }}><span className="av" style={{ width: 56, height: 56, margin: '0 auto 8px' }}>{initials(c.n)}</span><div><h3>{c.n}</h3><div className="sm">{c.h}</div></div></div>
      <div className="eb" style={{ marginTop: 16 }}>Detected intent</div><p style={{ margin: '4px 0 12px' }}><Badge k="in" i="ai">{c.intent}</Badge></p>
      <div className="eb">Order</div>
      {order ? (
        <div className="card" style={{ margin: '8px 0' }}>
          <dl className="kv"><dt>Order</dt><dd>#{order.id}</dd><dt>Full name</dt><dd>{order.name}</dd><dt>Phone</dt><dd>{order.ph}</dd><dt>Wilaya</dt><dd>{order.wil}</dd><dt>Delivery</dt><dd>{order.del}</dd><dt>Address</dt><dd>{order.addr}</dd><dt>Total</dt><dd><b style={{ fontWeight: 700 }}>{DA(order.tot)}</b></dd><dt>Status</dt><dd><Badge k={OS[order.st][0]} i={OS[order.st][1]}>{OS[order.st][2]}</Badge></dd></dl>
        </div>
      ) : <p className="sm" style={{ margin: '8px 0' }}>No order yet.</p>}
      <div className="eb" style={{ margin: '12px 0 8px' }}>Quick actions</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {order && <button className="btn" onClick={onOrder}>View order #{order.id}</button>}
        <button className="btn" onClick={() => toast('Phone copied (simulated)')}>Copy phone</button>
        <button className="btn" onClick={manual ? onResume : onTake}>{manual ? 'Resume AI' : 'Take over'}</button>
      </div>
    </>
  )
}
