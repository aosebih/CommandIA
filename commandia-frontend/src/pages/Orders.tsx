import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Badge, DA, Icon, Modal, OS, PageHead } from '../components/ui'
import { useApp } from '../store'
import type { OStatus } from '../types'

const CHIPS: [string, string][] = [['', 'All'], ['await', 'Awaiting'], ['confirmed', 'Confirmed'], ['shipped', 'Shipped'], ['delivered', 'Delivered'], ['cancelled', 'Cancelled']]
const NEXT: Partial<Record<OStatus, [OStatus, string]>> = { await: ['confirmed', 'Confirm order'], confirmed: ['shipped', 'Mark as shipped'], shipped: ['delivered', 'Mark as delivered'] }

export default function Orders() {
  const { id } = useParams(), nav = useNavigate(), { orders, convs, setOrder, toast } = useApp()
  const [q, setQ] = useState(''), [f, setF] = useState(''), [ask, setAsk] = useState(false)
  const o = orders.find((x) => x.id === Number(id))
  if (id && o) {
    const s = OS[o.st], nx = NEXT[o.st], conv = convs.find((c) => c.oid === o.id)
    const act = (st: OStatus) => void setOrder(o.id, st).then(() => toast('Order status updated: ' + OS[st][2]))
    return (
      <div className="pg">
        <button className="btn" onClick={() => nav('/app/orders')} style={{ marginBottom: 16 }}><Icon n="back" />Orders</button>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginBottom: 20 }}><h1>Order #{o.id}</h1><Badge k={s[0]} i={s[1]}>{s[2]}</Badge></div>
        <div className="card"><dl className="kv" style={{ gridTemplateColumns: '120px 1fr', gap: 8 }}><dt>Full name</dt><dd>{o.name}</dd><dt>Phone</dt><dd>{o.ph}</dd><dt>Wilaya</dt><dd>{o.wil}</dd><dt>Delivery type</dt><dd>{o.del}</dd><dt>Address</dt><dd>{o.addr}</dd><dt>Total</dt><dd><b>{DA(o.tot)}</b></dd><dt>Date</dt><dd>{o.d}</dd></dl></div>
        {o.st === 'await' && <div className="bn wa" style={{ margin: '0 0 16px' }}><Icon n="clock" s={20} /><div>Customer details were collected, but the order is <strong>not confirmed</strong>. Confirm it manually.</div></div>}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {nx && <button className="btn pr" onClick={() => act(nx[0])}>{nx[1]}</button>}
          {(o.st === 'await' || o.st === 'confirmed') && <button className="btn dg" onClick={() => setAsk(true)}>Cancel order</button>}
          {conv && <button className="btn" onClick={() => nav(`/app/inbox/${conv.id}`)}>Open conversation</button>}
        </div>
        {ask && <Modal title="Cancel this order?" onClose={() => setAsk(false)}><p>The customer will not be notified automatically. (Simulated)</p><div className="ac"><button className="btn" onClick={() => setAsk(false)}>Keep order</button><button className="btn dg" onClick={() => { setAsk(false); act('cancelled') }}>Cancel order</button></div></Modal>}
      </div>
    )
  }
  const rows = orders.filter((x) => (!f || x.st === f) && (x.name + x.ph + x.wil).toLowerCase().includes(q.toLowerCase()))
  return (
    <div className="pg">
      <PageHead title="Orders" desc="Track and manage orders collected from customer conversations." cta={<button className="btn pr" onClick={() => toast('Create order (simulated)')}>+ Create order</button>} />
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', padding: 16 }}>
          <input type="search" style={{ maxWidth: 420, flex: 1, minWidth: 200 }} aria-label="Search orders" placeholder="Search orders or customers" value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="chips" style={{ margin: 0 }}>{CHIPS.map(([k, l]) => <button key={k} className="chip" aria-pressed={f === k} onClick={() => setF(k)}>{l}</button>)}</div>
        </div>
        <div className="row hh">{['ORDER', 'CUSTOMER', 'PHONE', 'WILAYA', 'DELIVERY', 'TOTAL', 'STATUS', 'DATE'].map((h) => <span key={h}>{h}</span>)}</div>
        <div>
          {rows.map((x) => { const s = OS[x.st]; return (
            <button key={x.id} className="row" onClick={() => nav(`/app/orders/${x.id}`)}>
              <b>#{x.id}</b><span>{x.name}</span><span className="hm">{x.ph}</span><span className="hm">{x.wil}</span><span className="hm">{x.del}</span><span className="hm">{DA(x.tot)}</span><span><Badge k={s[0]} i={s[1]}>{s[2]}</Badge></span><span className="hm sm">{x.d}</span>
            </button>) })}
          {!rows.length && <p className="sm" style={{ padding: 16 }}>No orders match.</p>}
        </div>
      </div>
    </div>
  )
}
