import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { api } from './services/api'
import type { Conv, IgState, Mode, Order, OStatus, Product, User } from './types'

interface Auth { user: User | null; done: boolean }
const KEY = 'cmdia-auth'
const load = (): Auth => { try { return { user: null, done: false, ...JSON.parse(localStorage.getItem(KEY) || '{}') } } catch { return { user: null, done: false } } }

interface Ctx {
  auth: Auth; ready: boolean
  signIn: (email: string, pw: string) => Promise<void>; signUp: (n: string, e: string, pw: string) => Promise<void>
  signOut: () => Promise<void>; finishOnboarding: () => void
  convs: Conv[]; orders: Order[]; products: Product[]; ai: boolean; ig: IgState
  setMode: (id: number, m: Mode, fail?: boolean) => Promise<void>
  sendMessage: (id: number, text: string) => Promise<void>; markRead: (id: number) => void
  setOrder: (id: number, s: OStatus) => Promise<void>
  saveProduct: (p: Omit<Product, 'id'> & { id?: number }) => Promise<void>
  toggleAI: () => Promise<void>; setIG: (on: boolean) => Promise<void>
  toast: (m: string) => void
}
const C = createContext<Ctx>(null as unknown as Ctx)
export const useApp = () => useContext(C)

export function Provider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<Auth>(load)
  const [convs, setConvs] = useState<Conv[]>([]); const [orders, setOrders] = useState<Order[]>([]); const [products, setProducts] = useState<Product[]>([])
  const [ai, setAi] = useState(true); const [ig, setIg] = useState<IgState>('off'); const [ready, setReady] = useState(false)
  const [msg, setMsg] = useState(''); const tm = useRef(0)
  const persist = (a: Auth) => { setAuth(a); localStorage.setItem(KEY, JSON.stringify(a)) }
  const toast = useCallback((m: string) => { setMsg(m); window.clearTimeout(tm.current); tm.current = window.setTimeout(() => setMsg(''), 2600) }, [])

  useEffect(() => {
    if (!auth.user) { setReady(false); return }
    Promise.all([api.conversations(), api.orders(), api.products(), api.settings()]).then(([c, o, p, s]) => {
      setConvs(c); setOrders(o); setProducts(p); setAi(s.ai); setIg(s.ig ? 'on' : 'off'); setReady(true)
    }).catch(() => toast('Could not load data'))
  }, [auth.user, toast])

  const v: Ctx = {
    auth, ready, convs, orders, products, ai, ig, toast,
    signIn: async (e, pw) => { const user = await api.signIn(e, pw); persist({ user, done: auth.done }) },
    signUp: async (n, e, pw) => { const user = await api.signUp(n, e, pw); persist({ user, done: false }) },
    signOut: async () => { await api.signOut(); persist({ user: null, done: auth.done }) },
    finishOnboarding: () => persist({ ...auth, done: true }),
    setMode: async (id, m, fail) => { await api.setMode(id, m, fail); setConvs((cs) => cs.map((c) => (c.id === id ? { ...c, m } : c))) },
    sendMessage: async (id, text) => { const m = await api.sendMessage(id, text); setConvs((cs) => cs.map((c) => (c.id === id ? { ...c, ts: 'Now', msgs: [...c.msgs, m] } : c))) },
    markRead: (id) => setConvs((cs) => cs.map((c) => (c.id === id && c.un ? { ...c, un: 0 } : c))),
    setOrder: async (id, s) => { await api.setOrderStatus(id, s); setOrders((os) => os.map((o) => (o.id === id ? { ...o, st: s } : o))) },
    saveProduct: async (p) => { const n = await api.saveProduct(p); setProducts((ps) => (p.id ? ps.map((x) => (x.id === n.id ? n : x)) : [...ps, n])) },
    toggleAI: async () => { const s = await api.setAI(!ai); setAi(s.ai) },
    setIG: async (on) => { setIg('busy'); try { const s = await api.setInstagram(on); setIg(s.ig ? 'on' : 'off') } catch { setIg(on ? 'off' : 'on'); toast('Instagram action failed') } },
  }
  return <C.Provider value={v}>{children}<div role="status" aria-live="polite">{msg && <div className="toast">{msg}</div>}</div></C.Provider>
}
