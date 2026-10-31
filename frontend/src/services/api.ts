/**
 * API service layer. Every network call of the app goes through `api`.
 * - Default: fetch() against the FastAPI backend under /api. In development Vite proxies /api,
 *   in production the backend serves the built frontend from the same origin.
 * - VITE_API_URL: optional backend origin (for example http://localhost:8000).
 * - VITE_USE_MOCK=true: in-memory seed data for frontend work without the backend.
 */
import seed from '../data/seed.json'
import type { Conv, MessageResult, Mode, Msg, Order, OStatus, Product, Rules, Settings, User } from '../types'

const BASE = ((import.meta.env.VITE_API_URL as string | undefined) ?? '').replace(/\/$/, '')
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const db = structuredClone(seed) as unknown as { convs: Conv[]; orders: Order[]; products: Product[] }
const flags: Settings = { ai: true, ig: false }
const demoRules: Rules = { zones: { Alger: 600, Oran: 800, Constantine: 800, 'Other Wilayas': 900 }, opens: '09:00', closes: '18:00', behavior: 'Flag for human intervention', instructions: 'Escalate address changes. Never confirm without review.', tone: 'Warm and concise', languages: 'French / Algerian Arabic', maxDiscount: 0, freeAbove: 12000 }
const wait = () => new Promise<void>((r) => setTimeout(r, 200))
const clone = <T,>(v: T): T => structuredClone(v)
const now = () => new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })

async function call<T>(method: string, path: string, mock: () => T, body?: unknown): Promise<T> {
  if (!USE_MOCK) {
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
  /** `simulateFail` is a demo-only flag used to show the failure state. */
  setMode: (id: number, mode: Mode, simulateFail = false) => {
    if (simulateFail) return Promise.reject(new Error('Simulated network error'))
    return call<Mode>('PATCH', `/api/conversations/${id}/mode`, () => {
      const c = db.convs.find((x) => x.id === id)!
      c.m = mode
      return mode
    }, { mode })
  },
  sendMessage: (id: number, text: string) =>
    call<MessageResult>('POST', `/api/conversations/${id}/messages`, () => {
      const c = db.convs.find((x) => x.id === id)!
      const m: Msg = { w: 'h', t: text, time: now() }
      c.msgs.push(m)
      let reply: Msg | null = null
      if (c.m === 'ai' && flags.ai) {
        reply = { w: 'a', t: 'Thanks for your message. This is the offline preview; the local backend provides the real AI reply.', time: now() }
        c.msgs.push(reply)
        c.ts = 'Now'
      }
      return { message: m, reply, mode: c.m, intent: c.intent }
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
  rules: () => call<Rules>('GET', '/api/rules', () => clone(demoRules)),
  saveRules: (r: Rules) => call<Rules>('PUT', '/api/rules', () => r, r),
}
