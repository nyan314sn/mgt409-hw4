/** Cart pricing, checkout (reserve for pickup), and order history. */
import { ApiError } from './authApi.ts'
import type { CartLine } from './cart.ts'

export type CartLineQuote = {
  productId: string
  size: string
  quantity: number
  name: string | null
  image: string | null
  unitPrice: number | null
  lineTotal: number | null
  available: number
  problem: 'unknown_product' | 'sold_out' | 'not_enough_stock' | null
}

export type CartQuote = { lines: CartLineQuote[]; itemCount: number; subtotal: number; ok: boolean }

export type OrderItem = { productId: string; name: string; size: string; quantity: number; unitPrice: number; image: string }

export type Order = {
  orderNumber: string
  status: string
  pickupName: string
  note: string | null
  itemCount: number
  subtotal: number
  createdAt: string
  items: OrderItem[]
}

/** Thrown when stock changed under the shopper; carries the fresh quote to show them. */
export class CartChangedError extends ApiError {
  quote: CartQuote

  constructor(message: string, quote: CartQuote) {
    super(409, message)
    this.quote = quote
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, ...init })
  } catch (err) {
    // A cancelled request (page changed, cart edited again) isn't a connection problem.
    if ((err as Error).name === 'AbortError') throw err
    throw new ApiError(0, 'Can’t reach the shop server. Check your connection and try again.')
  }
  const data = await res.json().catch(() => ({}))
  if (res.status === 409 && data?.detail?.quote) throw new CartChangedError(data.detail.message, data.detail.quote)
  if (res.status === 502 || res.status === 504) {  // the dev proxy: backend is down
    throw new ApiError(0, 'Can’t reach the shop server. Check your connection and try again.')
  }
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Something went wrong. Please try again.'
    throw new ApiError(res.status, res.status >= 500 ? 'The shop server had a problem. Please try again.' : detail)
  }
  return data as T
}

export const ordersApi = {
  quote: (items: CartLine[], signal?: AbortSignal) =>
    call<CartQuote>('/api/cart/quote', { method: 'POST', body: JSON.stringify({ items }), signal }),
  place: (items: CartLine[], pickupName: string, note: string) =>
    call<Order>('/api/orders', { method: 'POST', body: JSON.stringify({ items, pickupName, note: note || null }) }),
  list: () => call<Order[]>('/api/orders'),
  get: (orderNumber: string) => call<Order>(`/api/orders/${encodeURIComponent(orderNumber)}`),
}

export const formatOrderDate = (utc: string) =>
  new Date(utc.replace(' ', 'T') + 'Z').toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })
