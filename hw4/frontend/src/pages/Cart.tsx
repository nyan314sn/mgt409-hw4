import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { MAX_LINE_QTY, useCart } from '../lib/cart.ts'
import { formatPrice, useCatalogue } from '../lib/catalogue.ts'
import { ordersApi, type CartLineQuote, type CartQuote } from '../lib/ordersApi.ts'
import { useTitle } from '../lib/useTitle.ts'

function problemText(line: CartLineQuote): string | null {
  if (line.problem === 'unknown_product') return 'This item is no longer sold.'
  if (line.problem === 'sold_out') return `Sold out in ${line.size} since you added it.`
  if (line.problem === 'not_enough_stock') return `Only ${line.available} left in ${line.size}.`
  return null
}

export default function Cart() {
  const cart = useCart()
  const navigate = useNavigate()
  const catalogue = useCatalogue()
  const stockVersion = catalogue.status === 'ready' ? catalogue.updatedAt : 0
  const [quote, setQuote] = useState<CartQuote | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useTitle(cart.count ? `Your cart (${cart.count})` : 'Your cart')

  // Re-price the cart against live stock whenever it changes or stock refreshes.
  useEffect(() => {
    if (cart.lines.length === 0) return
    const controller = new AbortController()
    ordersApi.quote(cart.lines, controller.signal)
      .then((q) => { setQuote(q); setError('') })
      .catch((err: Error) => { if (err.name !== 'AbortError') setError(err.message) })
    return () => controller.abort()
  }, [cart.lines, stockVersion, attempt])

  if (cart.lines.length === 0) {
    return (
      <div className="page page--center">
        <p className="eyebrow">Your cart</p>
        <h1>Your cart is empty.</h1>
        <p className="muted">Find something with a crest on it - then reserve it for pickup at 57 Broadway.</p>
        <Link to="/products" className="btn btn--primary">Browse products</Link>
      </div>
    )
  }

  const lines = quote?.lines ?? []

  return (
    <div className="page">
      <header className="page__head">
        <p className="eyebrow">Your cart</p>
        <h1>Ready when you are.</h1>
        <p className="muted">Reserve online, then pay and pick up at the shop. Prices and stock are checked live.</p>
      </header>

      {error && (
        <div className="status status--error loaderror" role="alert">
          <p>Couldn’t check your cart: {error}</p>
          <button className="btn btn--primary btn--sm" onClick={() => setAttempt((n) => n + 1)}>Try again</button>
        </div>
      )}

      <div className="cart">
        <ul className="cart__lines">
          {!quote && !error && <li className="status" role="status">Checking prices and stock…</li>}
          {lines.map((line) => {
            const warning = problemText(line)
            const max = Math.min(MAX_LINE_QTY, Math.max(line.available, 1))
            return (
              <li key={`${line.productId}-${line.size}`} className={`cartline${warning ? ' has-problem' : ''}`}>
                {line.image && <img src={line.image} alt="" className="cartline__img" />}
                <div className="cartline__info">
                  <Link to={`/products/${line.productId}`} className="cartline__name">{line.name ?? line.productId}</Link>
                  <p className="muted">Size {line.size}{line.unitPrice !== null && ` · ${formatPrice(line.unitPrice)} each`}</p>
                  {warning && (
                    <p className="cartline__warn" role="alert">
                      ⚠ {warning}{' '}
                      {line.problem === 'not_enough_stock' && (
                        <button className="link-arrow" onClick={() => cart.setQuantity(line.productId, line.size, line.available)}>
                          Change to {line.available}
                        </button>
                      )}
                    </p>
                  )}
                </div>
                <div className="qty" role="group" aria-label={`Quantity for ${line.name ?? line.productId} size ${line.size}`}>
                  <button onClick={() => cart.setQuantity(line.productId, line.size, line.quantity - 1)} aria-label="One fewer">−</button>
                  <output>{line.quantity}</output>
                  <button onClick={() => cart.setQuantity(line.productId, line.size, line.quantity + 1)}
                    disabled={line.quantity >= max} aria-label="One more">+</button>
                </div>
                <p className="cartline__total">{line.lineTotal !== null ? formatPrice(line.lineTotal) : '—'}</p>
                <button className="cartline__remove" onClick={() => cart.remove(line.productId, line.size)}
                  aria-label={`Remove ${line.name ?? line.productId} size ${line.size}`}>×</button>
              </li>
            )
          })}
        </ul>

        <aside className="cart__summary">
          <h2>Summary</h2>
          <dl>
            <div><dt>Items</dt><dd>{quote?.itemCount ?? cart.count}</dd></div>
            <div><dt>Subtotal</dt><dd>{quote ? formatPrice(quote.subtotal) : '…'}</dd></div>
            <div><dt>Pay</dt><dd>At pickup</dd></div>
          </dl>
          <button className="btn btn--primary btn--block" disabled={!quote?.ok} onClick={() => navigate('/checkout')}>
            Reserve for pickup →
          </button>
          {quote && !quote.ok && <p className="cartline__warn">Fix the items marked ⚠ to continue.</p>}
          <p className="muted cart__where">📍 Pick up at Campus Customs, 57 Broadway, New Haven.</p>
          <button className="link-arrow" onClick={cart.clear}>Empty cart</button>
        </aside>
      </div>
    </div>
  )
}
