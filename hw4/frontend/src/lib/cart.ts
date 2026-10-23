import { createContext, useContext } from 'react'

export const MAX_LINE_QTY = 10

/** A cart line. Prices are never stored here - they come live from the server. */
export type CartLine = { productId: string; size: string; quantity: number }

export type CartContextValue = {
  lines: CartLine[]
  count: number
  add: (line: CartLine) => void
  setQuantity: (productId: string, size: string, quantity: number) => void
  remove: (productId: string, size: string) => void
  clear: () => void
}

export const CartContext = createContext<CartContextValue | null>(null)

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used inside <CartProvider>')
  return ctx
}
