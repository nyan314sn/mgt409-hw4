import type { PointerEvent } from 'react'
import { Link } from 'react-router-dom'
import FitFinder from '../components/FitFinder.tsx'
import LoadError from '../components/LoadError.tsx'
import ProductCard from '../components/ProductCard.tsx'
import RackTicker from '../components/RackTicker.tsx'
import Reveal from '../components/Reveal.tsx'
import { useTitle } from '../lib/useTitle.ts'
import {
  COLLECTIONS, RESIDENTIAL_COLLEGES, searchText, useCatalogue, type Product,
} from '../lib/catalogue.ts'

const HERO_PICKS = ['basic-hoodie-big-yale', 'boola-boola-t-shirt', 'yale-mom-crewneck']
const FAVORITES = [
  'champion-reverse-weave-hoodie-1', 'district-vit-crewneck-vintage-bulldog',
  '2025-yale-vs-harvard-t-shirt', 'saybrook-sweater-fleece-jacket',
]

const STORIES = [
  { id: 'college', title: 'Rep your college', blurb: 'Fourteen colleges, one rivalry at a time. Find your crest before Feb Club.' },
  { id: 'teams', title: 'Back your team', blurb: 'From the Bowl to the boathouse — left-chest marks for twenty-plus sports.' },
  { id: 'family', title: 'Dress the family', blurb: 'Mom, Dad, Grandpa, the cousin who visits every Commencement. Covered.' },
  { id: 'schools', title: 'Your school, your crest', blurb: 'SOM, Law, Medicine, Art, and more — for the grad and professional crowd.' },
  { id: 'gameday', title: 'Game day ready', blurb: 'Layers loud enough for the Yale Bowl and warm enough for November.' },
]

/** Hero parallax: the hanging jerseys drift toward the cursor. */
function onHeroMove(e: PointerEvent<HTMLElement>) {
  if (e.pointerType !== 'mouse' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const r = e.currentTarget.getBoundingClientRect()
  e.currentTarget.style.setProperty('--mx', `${(e.clientX - r.left) / r.width - 0.5}`)
  e.currentTarget.style.setProperty('--my', `${(e.clientY - r.top) / r.height - 0.5}`)
}

export default function Home() {
  const catalogue = useCatalogue()
  useTitle(null)
  const products = catalogue.status === 'ready' ? catalogue.products : []
  const byId = (id: string) => products.find((p) => p.id === id)
  const inCollection = (id: string) => {
    const c = COLLECTIONS.find((x) => x.id === id)!
    return products.filter((p) => c.pattern.test(searchText(p))).length
  }
  const collegeCount = (college: string) =>
    products.filter((p) => searchText(p).toLowerCase().includes(college.toLowerCase())).length
  const collegesWithGear = RESIDENTIAL_COLLEGES.filter((c) => collegeCount(c) > 0).length

  const scoreboard = [
    { n: products.length || '—', label: 'Pieces on the rack' },
    { n: collegesWithGear || '—', label: 'College crests' },
    { n: products.length ? inCollection('teams') : '—', label: 'Team pieces' },
    { n: 57, label: 'Broadway, New Haven' },
  ]

  return (
    <>
      <section className="hero2" onPointerMove={onHeroMove}>
        <div className="hero2__marquee" aria-hidden="true">
          <span>BOOLA BOOLA · BOOLA BOOLA · BOOLA BOOLA · </span>
          <span>BOOLA BOOLA · BOOLA BOOLA · BOOLA BOOLA · </span>
        </div>
        <div className="hero2__inner">
          <div className="hero2__copy">
            <p className="hero2__kicker"><span className="dot" aria-hidden="true" />Open on Broadway · New Haven, CT</p>
            <h1 className="hero2__title">
              Wear your<br /><span className="hero2__yale">Yale</span> story.
            </h1>
            <p className="lede">
              Hoodies for 8 a.m. lectures, crews for Cross Campus, and a tee for every Bulldog who
              ever yelled at a Harvard fan. Officially licensed, picked by a family-run shop.
            </p>
            <div className="hero__actions">
              <button className="btn btn--primary btn--xl"
                onClick={() => { document.getElementById('fit')?.scrollIntoView({ behavior: 'smooth', block: 'center' }) }}>
                ✦ Find my fit
              </button>
              <Link to="/products" className="btn btn--ghost btn--xl">Shop the rack</Link>
            </div>
            <dl className="scoreboard">
              {scoreboard.map((s) => (
                <div key={s.label}><dt>{s.label}</dt><dd>{s.n}</dd></div>
              ))}
            </dl>
          </div>
          <div className="hero2__rack" aria-hidden="true">
            <span className="hero2__rail" />
            {HERO_PICKS.map((id, i) => {
              const p = byId(id)
              return (
                <div key={id} className={`hanger hanger--${i}`}>
                  <span className="hanger__hook" />
                  <div className="hanger__item">
                    {p ? <img src={p.image} alt="" /> : <div className="polaroid__blank" />}
                    {p && <span className="hanger__tag">${Math.floor(p.price)}</span>}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      <RackTicker products={products} />

      <section className="section" id="fit">
        <Reveal>
          {catalogue.status === 'ready' ? <FitFinder products={products} /> : <p className="status" role="status">Warming up the fit finder…</p>}
        </Reveal>
      </section>

      <section className="section">
        <Reveal>
          <div className="section__head">
            <p className="eyebrow">Shop by story</p>
            <h2>Everyone has a Yale chapter. <span className="accent">Find yours.</span></h2>
          </div>
        </Reveal>
        <div className="jerseys">
          {STORIES.map((s, i) => (
            <Reveal key={s.id} delay={i * 80}>
              <Link to={`/products?collection=${s.id}`} className="jersey">
                <span className="jersey__num" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
                <h3>{s.title}</h3>
                <p>{s.blurb}</p>
                <span className="story__cta">{catalogue.status === 'ready' ? `${inCollection(s.id)} pieces →` : 'Browse →'}</span>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="section section--band pennant-band">
        <Reveal>
          <div className="section__head">
            <p className="eyebrow">Residential colleges</p>
            <h2>Hang your crest.</h2>
            <p className="muted">Tap a pennant to see that college’s gear. Faded pennants are on our wish list.</p>
          </div>
        </Reveal>
        <ul className="pennants">
          {RESIDENTIAL_COLLEGES.map((college, i) => {
            const count = collegeCount(college)
            const style = { animationDelay: `${(i % 7) * 0.12}s` }
            return (
              <li key={college} style={style}>
                {count > 0 ? (
                  <>
                    <Link to={`/products?q=${encodeURIComponent(college)}`} className="pennant">
                      <span className="pennant__name">{college}</span>
                      <span className="sr-only"> ({count} {count === 1 ? 'item' : 'items'})</span>
                    </Link>
                    <span className="pennant__count" aria-hidden="true">{count}</span>
                  </>
                ) : (
                  <span className="pennant is-empty" title="Coming soon">
                    <span className="pennant__name">{college}</span>
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      </section>

      <section className="section">
        <Reveal>
          <div className="section__head section__head--row">
            <div>
              <p className="eyebrow">A few favorites</p>
              <h2>Straight off the rack.</h2>
              <p className="muted">Hover a card and tap your size to grab it without leaving the page.</p>
            </div>
            <Link to="/products" className="link-arrow">See all products →</Link>
          </div>
        </Reveal>
        {catalogue.status === 'loading' && <p className="status" role="status">Loading the rack…</p>}
        {catalogue.status === 'error' && <LoadError message={catalogue.message} />}
        {catalogue.status === 'ready' && (
          <div className="grid">
            {FAVORITES.map(byId).filter((p): p is Product => !!p).map((p, i) => (
              <Reveal key={p.id} delay={i * 90}><ProductCard product={p} /></Reveal>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <Reveal>
          <div className="storefront">
            <div className="storefront__awning" aria-hidden="true" />
            <div className="storefront__body">
              <div>
                <p className="neon" aria-hidden="true">Campus Customs</p>
                <h2>Reserve online. Pick up on Broadway.</h2>
                <p className="muted">
                  We’re a short walk from Old Campus. Add your size to the cart, reserve it, and we’ll
                  have it waiting. Pay at the counter, try it on, and ask about custom printing for
                  your team, club, or reunion while you’re here.
                </p>
                <div className="hero__actions">
                  <Link to="/products" className="btn btn--primary">Start a reservation</Link>
                  <a className="btn btn--ghost" href="https://maps.google.com/?q=57+Broadway+New+Haven+CT" target="_blank" rel="noreferrer">
                    Get directions ↗
                  </a>
                </div>
              </div>
              <address className="storefront__door">
                <span className="storefront__num">57</span>
                Broadway<br />New Haven, CT
              </address>
            </div>
          </div>
        </Reveal>
      </section>
    </>
  )
}
