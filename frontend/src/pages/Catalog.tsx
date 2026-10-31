import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Badge, DA, Icon, PageHead } from '../components/ui'
import { api } from '../services/api'
import { useApp } from '../store'
import type { Rules } from '../types'

const GR = ['#EBDDF5,#C9B3E6', '#EDE3D6,#CDAF8A', '#DEE4EE,#AEBBD0', '#F8DDEB,#E7A9CB']

export function Catalog() {
  const { products, saveProduct, toast } = useApp(), [edit, setEdit] = useState<number | 'new' | null>(null)
  const p = edit && edit !== 'new' ? products.find((x) => x.id === edit) : undefined
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const d = new FormData(e.currentTarget)
    await saveProduct({ id: p?.id, n: String(d.get('n')), p: Number(d.get('p')), s: Number(d.get('s')) }); setEdit(null); toast('Product saved')
  }
  return (
    <div className="pg">
      <PageHead title="Product Catalog" desc="Products and stock used by the AI when answering customer questions." cta={<button className="btn pr" onClick={() => setEdit('new')}>+ Add product</button>} />
      {edit && (
        <form className="card" onSubmit={submit} key={String(edit)}>
          <h2>{edit === 'new' ? 'Add product' : 'Edit product'}</h2>
          <div className="g2">
            <div><label htmlFor="pn">Name</label><input id="pn" name="n" required defaultValue={p?.n} /></div>
            <div><label htmlFor="pp">Price (DA)</label><input id="pp" name="p" type="number" min={0} required defaultValue={p?.p} /></div>
            <div><label htmlFor="pk">Stock quantity</label><input id="pk" name="s" type="number" min={0} required defaultValue={p?.s} /></div>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 14 }}><button className="btn pr">Save product</button><button type="button" className="btn" onClick={() => setEdit(null)}>Cancel</button></div>
        </form>
      )}
      <div className="gr">
        {products.map((x, i) => (
          <div key={x.id} className="card pc">
            <div className="tl" role="img" aria-label="Image placeholder" style={{ background: `linear-gradient(135deg,${GR[i % 4]})` }}>{x.n.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()}</div>
            <div className="bo">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {x.s > 0 ? <Badge k="ok" i="check">Available</Badge> : <Badge k="er" i="x">Unavailable</Badge>}
                <button className="ib" style={{ width: 40, height: 40 }} onClick={() => setEdit(x.id)} aria-label={`Edit ${x.n}`}><Icon n="edit" s={18} /></button>
              </div>
              <h2 style={{ fontSize: 20, marginTop: 10 }}>{x.n}</h2><b style={{ font: '700 18px Poppins' }}>{DA(x.p)}</b><div className="sm">{x.s > 0 ? `${x.s} in stock` : 'Out of stock'}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const INIT: Rules = { zones: { Alger: 600, Oran: 800, Constantine: 800, 'Other Wilayas': 900 }, opens: '09:00', closes: '18:00', behavior: 'Flag for human intervention', instructions: 'Escalate address changes. Never confirm without review.', tone: 'Warm and concise', languages: 'French / Algerian Arabic', maxDiscount: 0, freeAbove: 12000 }

export function RulesPage() {
  const { toast } = useApp(), saved = useRef<Rules>(INIT), [r, setR] = useState<Rules>(INIT)
  useEffect(() => {
    let alive = true
    api.rules().then((x) => { if (alive) { saved.current = x; setR(x) } }).catch(() => toast('Could not load rules'))
    return () => { alive = false }
  }, [toast])
  const set = <K extends keyof Rules>(k: K, v: Rules[K]) => setR((x) => ({ ...x, [k]: v }))
  const save = async () => { saved.current = await api.saveRules(r); toast('Rules saved') }
  const cancel = () => { setR(saved.current); toast('Changes discarded') }
  const Sec = ({ t, i, children }: { t: string; i: 'box' | 'clock' | 'ai' | 'user' | 'rules'; children: React.ReactNode }) => (
    <div className="card" style={{ margin: 0 }}><div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 6 }}><span className="it"><Icon n={i} s={20} /></span><h2 style={{ fontSize: 18 }}>{t}</h2></div>{children}</div>
  )
  return (
    <div className="pg">
      <PageHead title="Business Rules" desc="Define the operating rules and voice CommandIA uses in customer conversations." cta={<button className="btn pr" onClick={save}>Save changes</button>} />
      <div className="rg">
        <Sec t="Delivery zones & fees" i="box"><div className="g2">{Object.entries(r.zones).map(([w, f]) => <div key={w}><label>{w} (DA)</label><input type="number" min={0} value={f} onChange={(e) => set('zones', { ...r.zones, [w]: Number(e.target.value) })} /></div>)}</div></Sec>
        <Sec t="Business hours" i="clock"><div className="g2"><div><label>Opens</label><input type="time" value={r.opens} onChange={(e) => set('opens', e.target.value)} /></div><div><label>Closes</label><input type="time" value={r.closes} onChange={(e) => set('closes', e.target.value)} /></div></div><p className="sm" style={{ marginTop: 8 }}>Saturday–Thursday</p></Sec>
        <Sec t="AI response behavior" i="ai">
          <label htmlFor="rb">When unsure</label><select id="rb" value={r.behavior} onChange={(e) => set('behavior', e.target.value)}><option>Flag for human intervention</option><option>Ask a clarifying question</option></select>
          <label htmlFor="ri">Extra instructions</label><textarea id="ri" style={{ height: 70 }} value={r.instructions} onChange={(e) => set('instructions', e.target.value)} />
        </Sec>
        <Sec t="Tone of voice" i="user">
          <label htmlFor="rt">Tone</label><select id="rt" value={r.tone} onChange={(e) => set('tone', e.target.value)}><option>Warm and concise</option><option>Professional</option><option>Short and direct</option></select>
          <label>Languages</label><input value={r.languages} onChange={(e) => set('languages', e.target.value)} />
        </Sec>
        <Sec t="Pricing & discounts" i="rules"><div className="g2"><div><label>Max discount AI may offer (%)</label><input type="number" min={0} value={r.maxDiscount} onChange={(e) => set('maxDiscount', Number(e.target.value))} /></div><div><label>Free delivery above (DA)</label><input type="number" min={0} value={r.freeAbove} onChange={(e) => set('freeAbove', Number(e.target.value))} /></div></div><p className="sm" style={{ marginTop: 8 }}>Use catalog prices. No automatic discounts.</p></Sec>
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}><button className="btn pr" onClick={save}>Save changes</button><button className="btn" onClick={cancel}>Cancel</button></div>
    </div>
  )
}
