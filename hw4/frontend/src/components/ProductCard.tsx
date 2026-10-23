import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useCart } from '../lib/cart.ts'
import { swatchFor, totalStock, type Product } from '../lib/catalogue.ts'
import { tilt } from '../lib/tilt.ts'

/** Product card: tilts toward the cursor, wears a varsity hang-tag price, and has a
 *  "quick add" size bar so a shopper can grab their size without leaving the grid. */
export default function ProductCard({ product }: { product: Product }) {
  const cart = useCart()
  const [added, setAdded] = useState<string | null>(null)
  const stock = totalStock(product)
  const lowest = product.sizes.filter((s) => s.quantity > 0 && s.quantity < 5)
  const href = `/products/${product.id}`
  const dollars = Math.floor(product.price)

  function quickAdd(size: string) {
    cart.add({ productId: product.id, size, quantity: 1 })
    setAdded(size)
    window.setTimeout(() => setAdded((s) => (s === size ? null : s)), 1800)
  }

  return (
    <article className="card tilt" {...tilt}>
      <div className="card__media">
        <Link to={href} tabIndex={-1} aria-hidden="true" className="card__imglink">
          <img src={product.image} alt="" loading="lazy" />
        </Link>
        <span className="hangtag" aria-hidden="true"><small>$</small>{dollars}</span>
        {stock === 0 && <span className="badge badge--out">Sold out</span>}
        {stock > 0 && lowest.length > 0 && (
          <span className="badge">🔥 Only {lowest[0].quantity} left in {lowest[0].size}</span>
        )}
        {stock > 0 && (
          <div className="quickadd" role="group" aria-label={`Quick add ${product.name}`}>
            <span className="quickadd__label">{added ? `✓ Added ${added}` : 'Quick add'}</span>
            <div className="quickadd__sizes">
              {product.sizes.map((s) => (
                <button key={s.size} disabled={s.quantity === 0} onClick={() => quickAdd(s.size)}
                  aria-label={`Add size ${s.size} to cart${s.quantity === 0 ? ' (sold out)' : ''}`}>
                  {s.size}
                </button>
              ))}
            </div>
          </div>
        )}
        <span className="glare" aria-hidden="true" />
      </div>
      <Link to={href} className="card__link">
        <div className="card__body">
          <p className="card__kicker">{product.category}</p>
          <h3 className="card__title">{product.name}</h3>
          <p className="card__desc">{product.description}</p>
          <div className="card__row">
            <span className="price">${product.price.toFixed(2)}</span>
            <span className="swatches" aria-label={`Colors: ${product.colors.join(', ')}`}>
              {product.colors.slice(0, 4).map((c) => (
                <span key={c} className="swatch" style={{ background: swatchFor(c) }} title={c} />
              ))}
            </span>
          </div>
        </div>
      </Link>
    </article>
  )
}
