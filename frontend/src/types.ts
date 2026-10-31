export type Mode = 'ai' | 'attn' | 'manual'
export type Who = 'c' | 'a' | 'h'
export interface Msg { w: Who; t: string; time: string }
export interface MessageResult { message: Msg; reply: Msg | null; mode: Mode; intent?: string }
export interface Conv { id: number; n: string; h: string; m: Mode; un: number; ts: string; oid: number | null; intent: string; why?: string; msgs: Msg[] }
export type OStatus = 'await' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled'
export interface Order { id: number; name: string; ph: string; wil: string; del: string; addr: string; tot: number; st: OStatus; d: string }
export interface Product { id: number; n: string; p: number; s: number }
export interface User { name: string; email: string }
export interface Settings { ai: boolean; ig: boolean }
export interface Rules { zones: Record<string, number>; opens: string; closes: string; behavior: string; instructions: string; tone: string; languages: string; maxDiscount: number; freeAbove: number }
export type IgState = 'off' | 'busy' | 'on'
