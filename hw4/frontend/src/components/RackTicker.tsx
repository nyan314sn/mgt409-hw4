import { Link } from 'react-router-dom'
import type { Product } from '../lib/catalogue.ts'

const CHANTS = ['Boola Boola', 'Bulldogs, bow wow wow', 'Beat Harvard', 'For God, for Country & for Yale']

/** "Live from the rack": a scrolling ticker mixing chants with real, current low-stock
 *  sizes from the catalogue (never invented). Pauses on hover; items are real links. */
export default function RackTicker({ products }: { products: Product[] }) {
  const lowStock = products
    .flatMap((p) => p.sizes.filter((s) => s.quantity > 0 && s.quantity < 5).map((s) => ({ p, s })))
    .sort((a, b) => a.s.quantity - b.s.quantity)
    .slice(0, 8)

  const items = lowStock.flatMap(({ p, s }, i) => [
    { key: `c${i}`, chant: CHANTS[i % CHANTS.length] },
    { key: `${p.id}-${s.size}`, to: `/products/${p.id}`, text: `🔥 Only ${s.quantity} left · ${p.name} · ${s.size}` },
  ])
  if (items.length === 0) return null

  const row = (copy: number) => items.map((it) => (
    'chant' in it
      ? <span key={`${copy}-${it.key}`} className="rack__chant">{it.chant}</span>
      : <Link key={`${copy}-${it.key}`} to={it.to!} className="rack__item" tabIndex={copy ? -1 : 0}>{it.text}</Link>
  ))

  return (
    <section className="rack" aria-label="Low stock right now">
      <span className="rack__live"><i aria-hidden="true" />Live from the rack</span>
      <div className="rack__viewport">
        <div className="rack__track">
          {row(0)}
          <span aria-hidden="true" className="rack__dup">{row(1)}</span>
        </div>
      </div>
    </section>
  )
}
