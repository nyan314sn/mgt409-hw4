import { useEffect, type CSSProperties } from 'react'
import { Link, useLocation } from 'react-router-dom'
import ProductCard from './ProductCard.tsx'
import { useChat } from '../lib/chat.ts'

/**
 * The Spotlight: products the shop assistant found, shown as full product cards in a panel
 * that slides over the main page area (beside the chat panel). It doesn't replace the page
 * underneath - closing it (×, Esc, or navigating) brings the page back exactly as it was.
 * Cards are the same ProductCard used on the Products page, so clicking one opens the
 * normal product-detail page.
 */
export default function Spotlight() {
  const { spotlight, closeSpotlight, open: chatOpen } = useChat()
  const location = useLocation()
  // Only shown on the page it was opened on; any navigation (card click, nav link) hides it.
  const visible = spotlight !== null && spotlight.locationKey === location.key

  useEffect(() => {
    if (!visible) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') closeSpotlight() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [visible, closeSpotlight])

  if (!visible) return null
  const { showcase, id } = spotlight
  const count = showcase.products.length
  const total = showcase.totalMatches

  return (
    <section
      key={id}
      className={`spot${chatOpen ? ' spot--beside-chat' : ''}`}
      aria-labelledby="spot-title"
      // Close when a card or link inside is followed.
      onClick={(e) => (e.target as HTMLElement).closest('a') && closeSpotlight()}
    >
      <div className="spot__aurora" aria-hidden="true" />
      <div className="spot__inner">
        <header className="spot__head">
          <div>
            <p className="spot__eyebrow"><span aria-hidden="true">✦</span> Found by your shop assistant</p>
            <h2 id="spot-title" className="spot__title">{showcase.title}</h2>
            <p className="spot__meta" role="status">
              {total && total > count ? `Showing ${count} of ${total} matches` : `${count} ${count === 1 ? 'pick' : 'picks'}`}
              <span aria-hidden="true"> · </span>
              tap any card for the full details
            </p>
          </div>
          <div className="spot__actions">
            {showcase.browseUrl && (
              <Link to={showcase.browseUrl} className="btn btn--ghost btn--sm">
                See all{total ? ` ${total}` : ''} on Products →
              </Link>
            )}
            <button className="spot__close" onClick={closeSpotlight} aria-label="Close product spotlight">×</button>
          </div>
        </header>

        <div className="spot__grid">
          {showcase.products.map((p, i) => (
            <div key={p.id} className="spot__item" style={{ '--i': i } as CSSProperties}>
              {i === 0 && count > 1 && <span className="spot__ribbon">Top pick</span>}
              <ProductCard product={p} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
