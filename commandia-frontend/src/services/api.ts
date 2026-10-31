/**
 * API service layer. Every network call of the app goes through `api`.
 * - Without VITE_API_URL: in-memory mock data (src/data/seed.json), with a small latency.
 * - With VITE_API_URL: real fetch() calls to the FastAPI backend. The paths below are PROPOSED
 *   routes (not yet verified against the backend): adjust them here only.
 */
import seed from '../data/seed.json'
import type { Conv, Mode, Msg, Order, OStatus, Product, Rules, Settings, User } from '../types'

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? ''
const db = structuredClone(seed) as unknown as { convs: Conv[]; orders: Order[]; products: Product[] }
const flags: Settings = { ai: true, ig: false }
const wait = () => new Promise<void>((r) => setTimeout(r, 200))
const clone = <T,>(v: T): T => structuredClone(v)

async function call<T>(method: string, path: string, mock: () => T, body?: unknown): Promise<T> {
  if (BASE) {
    const r = await fetch(BASE + path, {
      method, credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
    return (await r.json()) as T
  }
  await wait()
  return mock()
}

export const api = {
  signIn: (email: string, password: string) =>
    call<User>('POST', '/api/auth/sign-in', () => ({ name: email.split('@')[0], email }), { email, password }),
  signUp: (name: string, email: string, password: string) =>
    call<User>('POST', '/api/auth/sign-up', () => ({ name, email }), { name, email, password }),
  signOut: () => call<void>('POST', '/api/auth/sign-out', () => undefined),

  conversations: () => call<Conv[]>('GET', '/api/conversations', () => clone(db.convs)),
  /** `simulateFail` is a demo-only flag used by the mock layer to show the failure state. */
  setMode: (id: number, mode: Mode, simulateFail = false) =>
    call<Mode>('PATCH', `/api/conversations/${id}/mode`, () => {
      if (simulateFail) throw new Error('Simulated network error')
      const c = db.convs.find((x) => x.id === id)!
      c.m = mode
      return mode
    }, { mode }),
  sendMessage: (id: number, text: string) =>
    call<Msg>('POST', `/api/conversations/${id}/messages`, () => {
      const m: Msg = { w: 'h', t: text, time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) }
      db.convs.find((x) => x.id === id)!.msgs.push(m)
      return m
    }, { text }),

  orders: () => call<Order[]>('GET', '/api/orders', () => clone(db.orders)),
  setOrderStatus: (id: number, status: OStatus) =>
    call<OStatus>('PATCH', `/api/orders/${id}/status`, () => { db.orders.find((o) => o.id === id)!.st = status; return status }, { status }),

  products: () => call<Product[]>('GET', '/api/products', () => clone(db.products)),
  saveProduct: (p: Omit<Product, 'id'> & { id?: number }) =>
    call<Product>(p.id ? 'PUT' : 'POST', p.id ? `/api/products/${p.id}` : '/api/products', () => {
      if (p.id) { const x = db.products.find((q) => q.id === p.id)!; Object.assign(x, p); return clone(x) }
      const n = { ...p, id: Date.now() } as Product
      db.products.push(n)
      return clone(n)
    }, p),

  settings: () => call<Settings>('GET', '/api/settings', () => ({ ...flags })),
  setAI: (on: boolean) => call<Settings>('PATCH', '/api/settings/ai', () => { flags.ai = on; return { ...flags } }, { enabled: on }),
  setInstagram: (on: boolean) =>
    call<Settings>('POST', `/api/integrations/instagram/${on ? 'connect' : 'disconnect'}`, () => { flags.ig = on; return { ...flags } }),
  saveRules: (r: Rules) => call<Rules>('PUT', '/api/rules', () => r, r),
}
