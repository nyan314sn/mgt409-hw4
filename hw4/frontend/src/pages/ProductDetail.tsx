import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import LiveStock from '../components/LiveStock.tsx'
import LoadError from '../components/LoadError.tsx'
import ProductCard from '../components/ProductCard.tsx'
import { MAX_LINE_QTY, useCart } from '../lib/cart.ts'
import { useChat } from '../lib/chat.ts'
import { useTitle } from '../lib/useTitle.ts'
import {
  COLLECTIONS, formatPrice, searchText, swatchFor, totalStock, useCatalogue, type Product,
} from '../lib/catalogue.ts'

function stockLabel(quantity: number): string {
  if (quantity === 0) return 'Sold out'
  if (quantity < 5) return `Only ${quantity} left`
  return `${quantity} in stock`
}

/** Same collection first, then same category, excluding the product itself. */
function related(product: Product, all: Product[]): Product[] {
  const coll = COLLECTIONS.find((c) => c.pattern.test(searchText(product)))
  const score = (p: Product) =>
    (coll && coll.pattern.test(searchText(p)) ? 2 : 0) + (p.category === product.category ? 1 : 0)
  return all
    .filter((p) => p.id !== product.id && score(p) > 0)
    .sort((a, b) => score(b) - score(a) || a.name.localeCompare(b.name))
    .slice(0, 4)
}

export default function ProductDetail() {
  const { id } = useParams()
  const catalogue = useCatalogue()
  const product = catalogue.status === 'ready' ? catalogue.products.find((p) => p.id === id) : undefined
  // Tab title: "Saybrook College Crewneck · $58.00 | Campus Customs"
  useTitle(product ? `${product.name} · ${formatPrice(product.price)}`
    : catalogue.status === 'ready' ? 'Product not found' : 'Loading…')

  if (catalogue.status === 'loading') {
    return <div className="page"><p className="status" role="status">Loading product…</p></div>
  }
  if (catalogue.status === 'error') {
    return <div className="page"><LoadError message={catalogue.message} /></div>
  }

  if (!product) {
    return (
      <div className="page page--center">
        <p className="eyebrow">Not on the rack</p>
        <h1>We couldn’t find that product.</h1>
        <Link to="/products" className="btn btn--primary">Back to products</Link>
      </div>
    )
  }

  // key resets the size choice when moving between products.
  return <ProductView key={product.id} product={product} all={catalogue.products} />
}

function ProductView({ product, all }: { product: Product; all: Product[] }) {
  const { openChat } = useChat()
  const cart = useCart()
  const [size, setSize] = useState('')
  const [qty, setQty] = useState(1)
  const [added, setAdded] = useState<{ size: string; qty: number } | null>(null)
  const stock = totalStock(product)
  const suggestions = related(product, all)
  const chosen = product.sizes.find((s) => s.size === size)
  const inCart = cart.lines.find((l) => l.productId === product.id && l.size === size)?.quantity ?? 0
  // Can't add more than is in stock (minus what's already in the cart), and at most 10 per line.
  const maxQty = chosen ? Math.max(0, Math.min(MAX_LINE_QTY, chosen.quantity) - inCart) : 0
  const amount = Math.min(qty, Math.max(maxQty, 1))

  function pickSize(next: string) {
    setSize(next)
    setQty(1)
    setAdded(null)
  }

  function addToCart() {
    if (!chosen || maxQty === 0) return
    cart.add({ productId: product.id, size, quantity: amount })
    setAdded({ size, qty: amount })
    setQty(1)
  }

  const buyLabel = !size ? 'Choose a size'
    : chosen?.quantity === 0 ? `Sold out in ${size}`
    : maxQty === 0 ? `All ${size} stock is in your cart`
    : `Add to cart · ${formatPrice(product.price * amount)}`

  return (
    <div className="page">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/products">Products</Link>
        <span aria-hidden="true">/</span>
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>{product.category}</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{product.name}</span>
      </nav>

      <div className="detail">
        <div className="detail__media zoom" onPointerMove={(e) => {
          // Hover zoom: the photo scales up around the cursor so shoppers can see the crest stitching.
          const r = e.currentTarget.getBoundingClientRect()
          e.currentTarget.style.setProperty('--zx', `${((e.clientX - r.left) / r.width) * 100}%`)
          e.currentTarget.style.setProperty('--zy', `${((e.clientY - r.top) / r.height) * 100}%`)
        }}>
          <img src={product.image} alt={product.description} />
          <span className="zoom__hint" aria-hidden="true">🔍 Hover to zoom</span>
        </div>

        <div className="detail__info">
          <p className="eyebrow">{product.garmentType}</p>
          <h1 className="detail__title">{product.name}</h1>
          <p className="price price--xl">{formatPrice(product.price)}</p>
          <p className="detail__desc">{product.description}</p>

          <h2 className="detail__label">Colors</h2>
          <ul className="detail__colors">
            {product.colors.map((c) => (
              <li key={c}><span className="swatch" style={{ background: swatchFor(c) }} aria-hidden="true" />{c}</li>
            ))}
          </ul>

          <h2 className="detail__label" id="size-label">
            Size {chosen && <span className="muted">— {stockLabel(chosen.quantity)}</span>}
          </h2>
          <div className="size-picker" role="radiogroup" aria-labelledby="size-label">
            {product.sizes.map((s) => (
              <button
                key={s.size}
                role="radio"
                aria-checked={size === s.size}
                className={`size-picker__opt${size === s.size ? ' is-active' : ''}${s.quantity === 0 ? ' is-out' : ''}`}
                onClick={() => pickSize(s.size)}
              >
                <strong>{s.size}</strong>
                <small>{stockLabel(s.quantity)}</small>
              </button>
            ))}
          </div>
          <p className="muted detail__total">
            {stock > 0 ? `${stock} units across all sizes.` : 'Sold out in every size.'}
          </p>

          <LiveStock />

          <div className="buy">
            <div className="qty" role="group" aria-label="Quantity">
              <button onClick={() => setQty((n) => Math.max(1, n - 1))} disabled={amount <= 1} aria-label="One fewer">−</button>
              <output aria-live="polite">{amount}</output>
              <button onClick={() => setQty((n) => Math.min(maxQty, n + 1))} disabled={amount >= maxQty} aria-label="One more">+</button>
            </div>
            <button className="btn btn--primary buy__add" onClick={addToCart} disabled={!chosen || maxQty === 0}>
              🛍 {buyLabel}
            </button>
          </div>
          {added && (
            <p className="toast" role="status">
              ✓ Added {added.qty} × {added.size} to your cart. <Link to="/cart">View cart & reserve →</Link>
            </p>
          )}
          <p className="muted buy__note">Reserve online, pay when you pick up at 57 Broadway.</p>

          <div className="detail__actions">
            <button className="btn btn--ghost" onClick={() => openChat()}>
              💬 Ask about this item
            </button>
            <Link to="/products" className="btn btn--ghost">Keep browsing</Link>
          </div>

          <h2 className="detail__label">Good to search for</h2>
          <ul className="tags">
            {product.tags.map((t) => (
              <li key={t}><Link to={`/products?q=${encodeURIComponent(t)}`} className="chip">{t}</Link></li>
            ))}
          </ul>
        </div>
      </div>

      {suggestions.length > 0 && (
        <section className="related">
          <h2>You might also like</h2>
          <div className="grid">
            {suggestions.map((p) => <ProductCard key={p.id} product={p} />)}
          </div>
        </section>
      )}
    </div>
  )
}
