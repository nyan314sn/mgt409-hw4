import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useParams } from 'react-router-dom'
import Confetti from '../components/Confetti.tsx'
import { useAuth } from '../lib/auth.ts'
import { formatPrice } from '../lib/catalogue.ts'
import { formatOrderDate, ordersApi, type Order } from '../lib/ordersApi.ts'
import { useTitle } from '../lib/useTitle.ts'

function useLoad<T>(load: () => Promise<T>, key: string) {
  const [state, setState] = useState<{ key: string; data?: T; error?: string } | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    load()
      .then((data) => active && setState({ key, data }))
      .catch((err: Error) => active && setState({ key, error: err.message }))
    return () => { active = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt])
  const current = state?.key === key ? state : null
  return { ...current, loading: !current, retry: () => { setState(null); setAttempt((n) => n + 1) } }
}

function Failed({ error, retry }: { error: string; retry: () => void }) {
  return (
    <div className="status status--error loaderror" role="alert">
      <p>{error}</p>
      <button className="btn btn--primary btn--sm" onClick={retry}>Try again</button>
    </div>
  )
}

function OrderItems({ order }: { order: Order }) {
  return (
    <ul className="mini">
      {order.items.map((i) => (
        <li key={`${i.productId}-${i.size}`}>
          {i.image && <img src={i.image} alt="" />}
          <span><Link to={`/products/${i.productId}`}>{i.name}</Link> <small>({i.size}) × {i.quantity}</small></span>
          <strong>{formatPrice(i.unitPrice * i.quantity)}</strong>
        </li>
      ))}
    </ul>
  )
}

export function OrderList() {
  const { user } = useAuth()
  useTitle('My orders')
  const orders = useLoad(() => ordersApi.list(), 'list')
  if (user === null) return <Navigate to="/login" state={{ from: '/orders' }} replace />

  return (
    <div className="page">
      <header className="page__head">
        <p className="eyebrow">My orders</p>
        <h1>Your reservations</h1>
        <p className="muted">Pick up and pay at Campus Customs, 57 Broadway.</p>
      </header>
      {orders.loading && <p className="status" role="status">Loading your orders…</p>}
      {orders.error && <Failed error={orders.error} retry={orders.retry} />}
      {orders.data?.length === 0 && (
        <div className="empty">
          <p className="empty__title">No reservations yet.</p>
          <Link to="/products" className="btn btn--primary">Browse products</Link>
        </div>
      )}
      <div className="orders">
        {orders.data?.map((o) => (
          <Link key={o.orderNumber} to={`/orders/${o.orderNumber}`} className="ordercard">
            <div>
              <p className="ordercard__num">{o.orderNumber}</p>
              <p className="muted">{formatOrderDate(o.createdAt)} · {o.itemCount} item{o.itemCount === 1 ? '' : 's'}</p>
            </div>
            <span className="ordercard__status">{o.status === 'reserved' ? 'Ready for pickup' : o.status}</span>
            <strong>{formatPrice(o.subtotal)}</strong>
          </Link>
        ))}
      </div>
    </div>
  )
}

export function OrderDetail() {
  const { orderNumber = '' } = useParams()
  const { user } = useAuth()
  const justPlaced = (useLocation().state as { justPlaced?: boolean } | null)?.justPlaced
  useTitle(`Order ${orderNumber}`)
  const order = useLoad(() => ordersApi.get(orderNumber), orderNumber)
  if (user === null) return <Navigate to="/login" state={{ from: `/orders/${orderNumber}` }} replace />

  return (
    <div className="page">
      {order.loading && <p className="status" role="status">Loading your order…</p>}
      {order.error && <Failed error={order.error} retry={order.retry} />}
      {order.data && (
        <>
          {justPlaced && <Confetti />}
          <header className={`confirm${justPlaced ? ' is-new' : ''}`}>
            <p className="eyebrow">{justPlaced ? '✦ Reserved!' : 'Order'}</p>
            <h1>{justPlaced ? `Boola Boola, ${order.data.pickupName.split(' ')[0]}!` : order.data.orderNumber}</h1>
            <p className="confirm__num">Order <strong>{order.data.orderNumber}</strong></p>
            <p className="muted">
              {justPlaced ? 'Your items are set aside. ' : ''}Show this number at Campus Customs, 57 Broadway, New Haven,
              and pay at the counter. Reserved {formatOrderDate(order.data.createdAt)} for {order.data.pickupName}.
            </p>
          </header>
          <div className="cart">
            <section className="cart__summary cart__summary--wide">
              <h2>Items</h2>
              <OrderItems order={order.data} />
              <dl><div><dt>Total due at pickup</dt><dd>{formatPrice(order.data.subtotal)}</dd></div></dl>
              {order.data.note && <p className="muted">Your note: “{order.data.note}”</p>}
            </section>
          </div>
          <p className="confirm__links">
            <Link to="/orders" className="btn btn--ghost">All my orders</Link>
            <Link to="/products" className="btn btn--primary">Keep shopping</Link>
          </p>
        </>
      )}
    </div>
  )
}
