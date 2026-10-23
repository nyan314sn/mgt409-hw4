import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth.ts'
import { useCart } from '../lib/cart.ts'
import { formatPrice, refreshCatalogue } from '../lib/catalogue.ts'
import { CartChangedError, ordersApi, type CartQuote } from '../lib/ordersApi.ts'
import { useTitle } from '../lib/useTitle.ts'

export default function Checkout() {
  const { user } = useAuth()
  const cart = useCart()
  const navigate = useNavigate()
  const [quote, setQuote] = useState<CartQuote | null>(null)
  const [pickupName, setPickupName] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [placing, setPlacing] = useState(false)
  useTitle('Checkout')

  useEffect(() => {
    if (cart.lines.length === 0) return
    const controller = new AbortController()
    ordersApi.quote(cart.lines, controller.signal)
      .then(setQuote)
      .catch((err: Error) => { if (err.name !== 'AbortError') setError(err.message) })
    return () => controller.abort()
  }, [cart.lines])

  if (user === undefined) return <div className="page"><p className="status" role="status">Loading…</p></div>
  if (user === null) return <Navigate to="/login" state={{ from: '/checkout' }} replace />
  if (cart.lines.length === 0 && !placing) return <Navigate to="/cart" replace />

  const name = pickupName || `${user.first_name} ${user.last_name}`.trim()

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return setError('Enter the name for pickup.')
    setPlacing(true)
    setError('')
    try {
      const order = await ordersApi.place(cart.lines, name.trim(), note.trim())
      cart.clear()
      void refreshCatalogue()  // stock just changed
      navigate(`/orders/${order.orderNumber}`, { replace: true, state: { justPlaced: true } })
    } catch (err) {
      setPlacing(false)
      if (err instanceof CartChangedError) {
        setQuote(err.quote)
        setError(err.message)
      } else {
        setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
      }
    }
  }

  return (
    <div className="page">
      <header className="page__head">
        <p className="eyebrow">Checkout</p>
        <h1>Reserve for pickup</h1>
        <p className="muted">No payment online. We set your items aside at 57 Broadway, and you pay at the counter.</p>
      </header>

      <div className="cart">
        <form className="form checkout" onSubmit={onSubmit} aria-busy={placing}>
          {error && (
            <div className="status status--error" role="alert">
              <p>{error}</p>
              {quote && !quote.ok && <Link to="/cart">Review your cart →</Link>}
            </div>
          )}
          <label className="field">
            <span>Name for pickup</span>
            <input value={name} onChange={(e) => setPickupName(e.target.value)} maxLength={80} autoComplete="name" required />
          </label>
          <label className="field">
            <span>Note for the shop (optional)</span>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} rows={3}
              placeholder="e.g. picking up Friday afternoon" />
          </label>
          <p className="muted">Confirmation goes to your account under <strong>My orders</strong> ({user.email}).</p>
          <button type="submit" className="btn btn--primary btn--block" disabled={placing || !quote?.ok}>
            {placing ? 'Reserving…' : `Reserve ${quote ? quote.itemCount : ''} item${quote?.itemCount === 1 ? '' : 's'}`}
          </button>
        </form>

        <aside className="cart__summary">
          <h2>Your items</h2>
          {!quote && <p className="status" role="status">Checking stock…</p>}
          <ul className="mini">
            {quote?.lines.map((l) => (
              <li key={`${l.productId}-${l.size}`} className={l.problem ? 'has-problem' : ''}>
                {l.image && <img src={l.image} alt="" />}
                <span>{l.quantity} × {l.name} <small>({l.size})</small>{l.problem && <em> ⚠ {l.problem === 'not_enough_stock' ? `only ${l.available} left` : 'unavailable'}</em>}</span>
                <strong>{l.lineTotal !== null ? formatPrice(l.lineTotal) : '—'}</strong>
              </li>
            ))}
          </ul>
          {quote && <dl><div><dt>Total due at pickup</dt><dd>{formatPrice(quote.subtotal)}</dd></div></dl>}
        </aside>
      </div>
    </div>
  )
}
