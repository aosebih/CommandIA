import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ConvItem, Ctx, Thread } from '../components/Inbox'
import { Icon, Modal, useMedia } from '../components/ui'
import { useApp } from '../store'
import type { Conv } from '../types'

const FILTERS = [['all', 'All'], ['ai', 'AI handled'], ['attn', 'Needs attention'], ['human', 'Human handled']] as const
const match = (c: Conv, f: string) => f === 'all' || (f === 'ai' && c.m === 'ai') || (f === 'attn' && c.m === 'attn') || (f === 'human' && c.m === 'manual')

export default function InboxPage() {
  const { id } = useParams(), nav = useNavigate(), { convs, orders, ai, setMode, sendMessage, markRead, toast } = useApp()
  const mobile = useMedia('(max-width:767px)'), narrow = useMedia('(max-width:860px)')
  const [q, setQ] = useState(''), [f, setF] = useState<string>('all'), [cx, setCx] = useState(false)
  const [modal, setModal] = useState<'take' | 'resume' | null>(null), [fail, setFail] = useState(false), [err, setErr] = useState(false), [busy, setBusy] = useState(false)
  const list = useMemo(() => convs.filter((c) => match(c, f) && (c.n + c.h + c.msgs.map((m) => m.t).join(' ')).toLowerCase().includes(q.toLowerCase())).sort((a, b) => +(b.m === 'attn') - +(a.m === 'attn')), [convs, f, q])
  const sel = convs.find((c) => c.id === Number(id)) ?? (mobile ? undefined : convs[0])
  const open = (c: Conv) => { markRead(c.id); setCx(false); nav(`/app/inbox/${c.id}`) }
  const ask = (m: 'take' | 'resume') => { setErr(false); setModal(m) }
  const close = () => { setModal(null); setErr(false) }
  const confirm = async () => {
    if (!sel || !modal) return
    setBusy(true)
    try { await setMode(sel.id, modal === 'take' ? 'manual' : 'ai', fail); toast(modal === 'take' ? `Manual Mode: AI paused for ${sel.n}` : `AI Active again for ${sel.n}`); close() } catch { setErr(true) } finally { setBusy(false) }
  }
  const order = sel && orders.find((o) => o.id === sel.oid)
  const t = modal === 'take'
  return (
    <div className={`inbox ${mobile && !id ? 'l' : 't'} ${cx ? 'cx' : ''}`}>
      <section className="list" aria-label="Conversations">
        <div className="hd">
          <h2 style={{ fontSize: 22 }}>Conversations</h2><div className="sm">{convs.length} active</div>
          <div style={{ position: 'relative', marginTop: 12 }}><input type="search" aria-label="Search conversations" placeholder="Search conversations" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          <div className="chips">{FILTERS.map(([k, l]) => <button key={k} className="chip" aria-pressed={f === k} onClick={() => setF(k)}>{k === 'all' ? `All ${convs.length}` : l}</button>)}</div>
        </div>
        <div>{list.map((c) => <ConvItem key={c.id} c={c} active={c.id === sel?.id} onClick={() => open(c)} />)}{!list.length && <p className="sm" style={{ padding: 16 }}>No conversations match.</p>}</div>
      </section>
      <section className="thread" aria-label="Conversation">
        {sel && <Thread c={sel} aiOn={ai} showBack={mobile} showDetails={narrow} onBack={() => nav('/app/inbox')} onDetails={() => setCx(!cx)} onTake={() => ask('take')} onResume={() => ask('resume')} onSend={(txt) => sendMessage(sel.id, txt)} onSettings={() => nav('/app/ai-settings')} />}
      </section>
      <aside className="ctx" aria-label="Customer context">
        {mobile && <button className="btn" onClick={() => setCx(false)} style={{ marginBottom: 12 }}><Icon n="back" />Back to chat</button>}
        {sel && <Ctx c={sel} order={order} onOrder={() => nav(`/app/orders/${order!.id}`)} onTake={() => ask('take')} onResume={() => ask('resume')} toast={toast} />}
      </aside>
      {modal && sel && (
        <Modal title={t ? 'Pause AI & take over?' : 'Resume AI handling?'} onClose={close}>
          <p>{t ? `The AI will stop replying to ${sel.n} in this conversation only. Anything you type will be sent by you.` : `The AI will start replying to ${sel.n} again automatically.`}</p>
          {err && <div className="b er" style={{ marginBottom: 12, whiteSpace: 'normal' }}><Icon n="warn" s={14} /> Could not switch mode (simulated network error). Nothing changed. Try again.</div>}
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', margin: '0 0 14px' }}><input type="checkbox" style={{ width: 18, minHeight: 0 }} checked={fail} onChange={() => setFail(!fail)} /> Simulate a failure (demo)</label>
          <div className="ac"><button className="btn" onClick={() => { close(); toast('Cancelled. Nothing changed.') }}>Cancel</button><button className="btn pr" disabled={busy} onClick={confirm}>{err ? 'Retry' : t ? 'Pause AI & take over' : 'Resume AI'}</button></div>
        </Modal>
      )}
    </div>
  )
}
