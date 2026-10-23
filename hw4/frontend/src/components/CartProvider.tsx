import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { CartContext, MAX_LINE_QTY, type CartLine } from '../lib/cart.ts'

const STORAGE_KEY = 'cc-cart-v1'

function loadCart(): CartLine[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const data = raw ? JSON.parse(raw) : []
    return Array.isArray(data)
      ? data.filter((l) => typeof l?.productId === 'string' && typeof l?.size === 'string' && Number.isInteger(l?.quantity))
      : []
  } catch {
    return []
  }
}

/** The cart lives in this browser (localStorage) so guests can shop too; checkout re-checks
 *  every line against live stock and prices on the server. */
export default function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>(loadCart)

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(lines))
    } catch {
      // Storage unavailable (private mode) - the cart still works for this visit.
    }
  }, [lines])

  const add = useCallback((line: CartLine) => {
    setLines((current) => {
      const existing = current.find((l) => l.productId === line.productId && l.size === line.size)
      if (existing) {
        return current.map((l) => l === existing
          ? { ...l, quantity: Math.min(MAX_LINE_QTY, l.quantity + line.quantity) } : l)
      }
      return [...current, { ...line, quantity: Math.min(MAX_LINE_QTY, line.quantity) }]
    })
  }, [])

  const setQuantity = useCallback((productId: string, size: string, quantity: number) => {
    setLines((current) => current
      .map((l) => l.productId === productId && l.size === size
        ? { ...l, quantity: Math.max(0, Math.min(MAX_LINE_QTY, quantity)) } : l)
      .filter((l) => l.quantity > 0))
  }, [])

  const remove = useCallback((productId: string, size: string) => {
    setLines((current) => current.filter((l) => !(l.productId === productId && l.size === size)))
  }, [])

  const clear = useCallback(() => setLines([]), [])

  const value = useMemo(() => ({
    lines, count: lines.reduce((n, l) => n + l.quantity, 0), add, setQuantity, remove, clear,
  }), [lines, add, setQuantity, remove, clear])
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}
