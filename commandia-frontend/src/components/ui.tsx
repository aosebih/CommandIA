import { useEffect, useState, type ReactNode } from 'react'
import type { Mode, OStatus } from '../types'

export const IP = {
  inbox: 'M4 5h16v11H9l-5 4z', home: 'M4 11l8-7 8 7v9H4z', ord: 'M5 8h14l-1 12H6zM9 8a3 3 0 016 0',
  box: 'M12 3l8 4v10l-8 4-8-4V7zM4 7l8 4 8-4M12 11v10', rules: 'M4 7h10M18 7h2M4 17h2M10 17h10M14 5v4M6 15v4',
  ai: 'M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z', plug: 'M9 3v5M15 3v5M6 8h12v4a6 6 0 01-12 0zM12 18v3',
  send: 'M3 12l18-9-7 18-3-8z', warn: 'M12 4l9 16H3zM12 10v4M12 17v.5', check: 'M5 12l5 5 9-10', x: 'M6 6l12 12M18 6L6 18',
  search: 'M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-5-5', user: 'M12 4a4 4 0 100 8 4 4 0 000-8zM4 20c0-4 4-6 8-6s8 2 8 6',
  back: 'M15 5l-7 7 7 7', hand: 'M8 12V6a1.5 1.5 0 013 0v5M11 11V4.5a1.5 1.5 0 013 0V11M14 11V6a1.5 1.5 0 013 0v7a6 6 0 01-6 6 5 5 0 01-4-2l-3-5a1.5 1.5 0 012.5-1.5L8 14',
  clock: 'M12 4a8 8 0 100 16 8 8 0 000-16zM12 8v4l3 2', edit: 'M4 20h4L19 9l-4-4L4 16zM13 7l4 4',
} as const
export type IconName = keyof typeof IP

export const Icon = ({ n, s = 16 }: { n: IconName; s?: number }) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={IP[n]} /></svg>
)
export const Badge = ({ k, i, children }: { k: string; i: IconName; children: ReactNode }) => <span className={`b ${k}`}><Icon n={i} s={13} />{children}</span>
export const MODE: Record<Mode, [string, IconName, string]> = { ai: ['ok', 'ai', 'AI Active'], attn: ['wa', 'warn', 'Needs human'], manual: ['in', 'user', 'Manual Mode'] }
export const OS: Record<OStatus, [string, IconName, string]> = {
  await: ['wa', 'clock', 'Awaiting confirmation'], confirmed: ['ok', 'check', 'Confirmed'], shipped: ['in', 'box', 'Shipped'], delivered: ['ok', 'check', 'Delivered'], cancelled: ['er', 'x', 'Cancelled'],
}
export const DA = (n: number) => n.toLocaleString('fr-FR').replace(/[\u202f\u00a0]/g, ' ') + ' DA'
export const initials = (n: string) => n.split(' ').map((w) => w[0]).join('')

export function useMedia(q: string) {
  const [m, setM] = useState(() => matchMedia(q).matches)
  useEffect(() => { const mq = matchMedia(q), f = () => setM(mq.matches); mq.addEventListener('change', f); f(); return () => mq.removeEventListener('change', f) }, [q])
  return m
}
export const Switch = ({ on, label, onClick }: { on: boolean; label: string; onClick: () => void }) => <button className="sw" role="switch" aria-checked={on} aria-label={label} onClick={onClick} />
export const PageHead = ({ title, desc, cta }: { title: string; desc: string; cta?: ReactNode }) => (
  <div className="phd"><div><div className="eb mg">Workspace management</div><h1>{title}</h1><p>{desc}</p></div>{cta}</div>
)
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => { const f = (e: KeyboardEvent) => e.key === 'Escape' && onClose(); addEventListener('keydown', f); return () => removeEventListener('keydown', f) }, [onClose])
  return <div className="mod"><div className="mb" role="dialog" aria-modal="true" aria-labelledby="mt"><h2 id="mt">{title}</h2>{children}</div></div>
}
