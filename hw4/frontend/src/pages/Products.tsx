import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import LiveStock from '../components/LiveStock.tsx'
import LoadError from '../components/LoadError.tsx'
import ProductCard from '../components/ProductCard.tsx'
import { useTitle } from '../lib/useTitle.ts'
import {
  CATEGORIES, COLLECTIONS, COLOR_FAMILIES, searchText, useCatalogue,
} from '../lib/catalogue.ts'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const SORTS = [
  { id: 'featured', label: 'Featured' },
  { id: 'price-asc', label: 'Price: low to high' },
  { id: 'price-desc', label: 'Price: high to low' },
  { id: 'name', label: 'Name A–Z' },
]

export default function Products() {
  const catalogue = useCatalogue()
  const [params, setParams] = useSearchParams()

  const q = params.get('q') ?? ''
  const category = params.get('category') ?? ''
  const collection = params.get('collection') ?? ''
  const color = params.get('color') ?? ''
  const size = params.get('size') ?? ''
  const max = Number(params.get('max')) || 0
  const sort = params.get('sort') ?? 'featured'
  const collectionLabel = COLLECTIONS.find((c) => c.id === collection)?.label
  // Tab title follows the filters: "Hoodies", "Search: saybrook", "Bulldog teams"...
  useTitle(q ? `Search: ${q}` : category || collectionLabel || 'Products')

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const results = useMemo(() => {
    if (catalogue.status !== 'ready') return []
    const words = q.toLowerCase().split(/\s+/).filter(Boolean)
    const coll = COLLECTIONS.find((c) => c.id === collection)
    const fam = COLOR_FAMILIES.find((f) => f.id === color)

    const list = catalogue.products.filter((p) => {
      const text = searchText(p).toLowerCase()
      if (words.some((w) => !text.includes(w))) return false
      if (category && p.category !== category) return false
      if (coll && !coll.pattern.test(searchText(p))) return false
      if (fam && !fam.pattern.test((p.colors[0] ?? '').toLowerCase())) return false
      if (size && !p.sizes.some((s) => s.size === size && s.quantity > 0)) return false
      if (max && p.price > max) return false
      return true
    })

    if (sort === 'price-asc') list.sort((a, b) => a.price - b.price)
    if (sort === 'price-desc') list.sort((a, b) => b.price - a.price)
    if (sort === 'name') list.sort((a, b) => a.name.localeCompare(b.name))
    return list
  }, [catalogue, q, category, collection, color, size, max, sort])

  const hasFilters = [...params.keys()].some((k) => k !== 'sort')

  return (
    <div className="page">
      <header className="page__head">
        <p className="eyebrow">The rack</p>
        <h1>Products</h1>
        <p className="muted">Every piece, with stock by size. Tap a product for the full story. Filters stay in the URL, so you can share a search.</p>
      </header>

      <div className="filters" role="search">
        <label className="field field--grow">
          <span>Search</span>
          <input
            type="search"
            value={q}
            placeholder="Try “Saybrook”, “hockey”, or “Mom”"
            onChange={(e) => update('q', e.target.value)}
          />
        </label>
        <label className="field">
          <span>Collection</span>
          <select value={collection} onChange={(e) => update('collection', e.target.value)}>
            <option value="">All collections</option>
            {COLLECTIONS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>In stock in</span>
          <select value={size} onChange={(e) => update('size', e.target.value)}>
            <option value="">Any size</option>
            {SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Max price</span>
          <select value={max ? String(max) : ''} onChange={(e) => update('max', e.target.value)}>
            <option value="">Any price</option>
            {[40, 60, 80, 100].map((m) => <option key={m} value={m}>Under ${m}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Sort</span>
          <select value={sort} onChange={(e) => update('sort', e.target.value === 'featured' ? '' : e.target.value)}>
            {SORTS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </label>
      </div>

      <div className="chips" role="group" aria-label="Category">
        <button className={`chip${!category ? ' is-active' : ''}`} aria-pressed={!category} onClick={() => update('category', '')}>All</button>
        {CATEGORIES.map((c) => (
          <button key={c} className={`chip${category === c ? ' is-active' : ''}`} aria-pressed={category === c}
            onClick={() => update('category', category === c ? '' : c)}>
            {c}
          </button>
        ))}
      </div>

      <div className="chips" role="group" aria-label="Garment color">
        {COLOR_FAMILIES.map((f) => (
          <button key={f.id} className={`chip chip--color${color === f.id ? ' is-active' : ''}`} aria-pressed={color === f.id}
            onClick={() => update('color', color === f.id ? '' : f.id)}>
            <span className="swatch" style={{ background: f.swatch }} aria-hidden="true" />
            {f.label}
          </button>
        ))}
      </div>

      {catalogue.status === 'loading' && <p className="status" role="status">Loading products…</p>}
      {catalogue.status === 'error' && (
        <LoadError message={catalogue.message} />
      )}
      {catalogue.status === 'ready' && (
        <>
          <div className="results-bar">
            <p role="status">{results.length} of {catalogue.products.length} products</p>
            <LiveStock />
            {hasFilters && <button className="link-arrow" onClick={() => setParams({}, { replace: true })}>Clear filters</button>}
          </div>
          {results.length === 0 ? (
            <div className="empty">
              <p className="empty__title">Nothing on the rack matches that.</p>
              <p className="muted">Try fewer filters, or search for a college, sport, or family member.</p>
            </div>
          ) : (
            <div className="grid">
              {results.map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          )}
        </>
      )}

    </div>
  )
}
