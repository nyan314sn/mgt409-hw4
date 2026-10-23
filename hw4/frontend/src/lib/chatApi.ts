/**
 * Chat client for the FastAPI backend.
 *
 * History lives on the server, keyed by the logged-in user's session cookie. The browser
 * sends only the new message (plus the product page it's on, if any) and loads past turns
 * from /api/chat/history.
 *
 * Contract: POST /api/chat returns the chat text and the product data as two separate
 * objects. `message` goes in the chat bubble; `showcase` is rendered on the page in the
 * Spotlight as full product cards (never inside the chat bubble).
 */
import { ApiError } from './authApi.ts'
import type { Product } from './catalogue.ts'

export type ChatRole = 'user' | 'assistant'

/** Products the assistant put on the page. Same Product shape as GET /api/products. */
export type Showcase = {
  title: string
  products: Product[]
  /** How many products matched the search behind these cards, if known. */
  totalMatches: number | null
  /** Products-page link with the same search, e.g. /products?category=Hoodies. */
  browseUrl: string | null
}

export type ChatMessage = {
  role: ChatRole
  content: string
  showcase?: Showcase | null
  /** UTC "YYYY-MM-DD HH:MM:SS" for messages loaded from history. */
  createdAt?: string | null
}

/** Where the shopper is, sent with every message so the assistant knows what "this" means.
 *  Only locators are sent; the server checks them against the catalogue. */
export type PageContext = {
  /** Current path + query, e.g. "/products/saybrook-college-crewneck" or "/products?category=Hoodies". */
  path: string
  /** Products shown in the Spotlight right now, in on-screen order. */
  spotlightProductIds: string[]
  spotlightTitle: string | null
}

export type ChatRequest = {
  message: string
  page: PageContext
}

export type ChatHistory = {
  /** true: saved to the shopper's account. false: guest chat, kept for this visit only. */
  saved: boolean
  messages: ChatMessage[]
}

export type ChatReply = {
  message: { role: 'assistant'; content: string }
  showcase: Showcase | null
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, ...init })
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err
    throw new ApiError(0, 'Can’t reach the shop server. Please try again.')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    // 502/504 come from the dev proxy when the backend itself is down.
    if (res.status === 502 || res.status === 504) throw new ApiError(0, 'Can’t reach the shop server right now.')
    const detail = typeof data.detail === 'string' ? data.detail : 'Sorry, the assistant couldn’t answer. Please try again.'
    throw new ApiError(res.status, detail)
  }
  return data as T
}

export function sendChatMessage(req: ChatRequest, signal?: AbortSignal): Promise<ChatReply> {
  return call<ChatReply>('/api/chat', { method: 'POST', body: JSON.stringify(req), signal })
}

export function fetchChatHistory(signal?: AbortSignal): Promise<ChatHistory> {
  return call<ChatHistory>('/api/chat/history', { signal })
}
