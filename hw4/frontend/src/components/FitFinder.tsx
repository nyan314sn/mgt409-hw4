import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { COLLECTIONS, searchText, totalStock, type Product } from '../lib/catalogue.ts'
import { useChat } from '../lib/chat.ts'

type Option = { id: string; emoji: string; label: string }

const WHO: (Option & { pattern?: RegExp; title: string })[] = [
  { id: 'me', emoji: '🙋', label: 'Me', title: 'for you' },
  { id: 'mom', emoji: '💐', label: 'Mom', pattern: /\bmom\b/i, title: 'for Mom' },
  { id: 'dad', emoji: '🧢', label: 'Dad', pattern: /\bdad\b/i, title: 'for Dad' },
  { id: 'grand', emoji: '🧓', label: 'Grandparent', pattern: /grandma|grandpa/i, title: 'for the grandparents' },
  { id: 'family', emoji: '👨‍👩‍👧', label: 'Aunt, uncle, sibling', pattern: /\b(aunt|uncle|brother|cousin)\b/i, title: 'for the family' },
  { id: 'friend', emoji: '🎓', label: 'A Yalie friend', title: 'for a Yalie' },
]

const VIBE: (Option & { match: (p: Product) => boolean; title: string })[] = [
  { id: 'gameday', emoji: '🏈', label: 'Game day loud', title: 'Game-day',
    match: (p) => COLLECTIONS.some((c) => (c.id === 'gameday' || c.id === 'teams') && c.pattern.test(searchText(p))) },
  { id: 'cozy', emoji: '🔥', label: 'Cozy layers', title: 'Cozy',
    match: (p) => ['Hoodies', 'Jackets', 'Quarter-zips'].includes(p.category) },
  { id: 'everyday', emoji: '☕', label: 'Everyday easy', title: 'Everyday',
    match: (p) => ['Tees', 'Crewnecks'].includes(p.category) },
  { id: 'pride', emoji: '🛡️', label: 'College & school pride', title: 'Crest-proud',
    match: (p) => COLLECTIONS.some((c) => (c.id === 'college' || c.id === 'schools') && c.pattern.test(searchText(p))) },
  { id: 'any', emoji: '🎲', label: 'Surprise me', title: 'Hand-picked', match: () => true },
]

const BUDGET = [
  { id: '40', emoji: '💵', label: 'Under $40', max: 40 },
  { id: '60', emoji: '💳', label: 'Under $60', max: 60 },
  { id: '80', emoji: '🎁', label: 'Under $80', max: 80 },
  { id: 'any', emoji: '✨', label: 'No limit', max: null },
] as const

/** Three quick taps -> real matching products, revealed in the Spotlight. */
export default function FitFinder({ products }: { products: Product[] }) {
  const location = useLocation()
  const { showSpotlight } = useChat()
  const [step, setStep] = useState(0)
  const [who, setWho] = useState<string | null>(null)
  const [vibe, setVibe] = useState<string | null>(null)

  function finish(budgetId: string) {
    const w = WHO.find((o) => o.id === who) ?? WHO[0]
    const v = VIBE.find((o) => o.id === vibe) ?? VIBE[VIBE.length - 1]
    const max = BUDGET.find((b) => b.id === budgetId)?.max ?? null
    const inBudget = products.filter((p) => totalStock(p) > 0 && (max === null || p.price <= max))

    // Score: right recipient matters most, then the vibe; relax gracefully if nothing fits.
    const scored = inBudget
      .map((p) => ({ p, score: (w.pattern?.test(searchText(p)) ? 3 : 0) + (v.match(p) ? 2 : 0) }))
      .filter(({ score }) => score > 0 || (!w.pattern && v.id === 'any'))
      .sort((a, b) => b.score - a.score || b.p.sizes.filter((s) => s.quantity > 0).length - a.p.sizes.filter((s) => s.quantity > 0).length)
    const picks = scored.slice(0, 8).map((s) => s.p)
    const budgetLabel = max ? ` under $${max}` : ''
    const params = new URLSearchParams()
    if (max) params.set('max', String(max))
    if (w.pattern) params.set('collection', 'family')

    showSpotlight({
      title: picks.length ? `${v.title} picks ${w.title}${budgetLabel}` : `Nothing fits that just yet`,
      products: picks.length ? picks : inBudget.slice(0, 8),
      totalMatches: scored.length,
      browseUrl: `/products${params.size ? `?${params}` : ''}`,
    }, location.key)
    setStep(0)
    setWho(null)
    setVibe(null)
  }

  const steps = [
    { q: 'Who are you shopping for?', options: WHO, pick: (id: string) => { setWho(id); setStep(1) } },
    { q: 'What’s the vibe?', options: VIBE, pick: (id: string) => { setVibe(id); setStep(2) } },
    { q: 'And the budget?', options: BUDGET as readonly Option[], pick: finish },
  ]
  const current = steps[step]

  return (
    <div className="fit">
      <div className="fit__intro">
        <p className="eyebrow">Find your fit · 3 taps</p>
        <h2>Not sure what to get? <span className="accent">We’ll call the play.</span></h2>
        <p className="muted">Answer three quick questions and we’ll pull real picks off the rack, in stock right now.</p>
        <ol className="fit__pips" aria-label={`Step ${step + 1} of 3`}>
          {steps.map((_, i) => <li key={i} className={i <= step ? 'is-on' : ''} />)}
        </ol>
      </div>
      <div className="fit__panel" aria-live="polite">
        <p className="fit__q"><span className="fit__num">0{step + 1}</span>{current.q}</p>
        <div className="fit__options">
          {current.options.map((o) => (
            <button key={o.id} className="fit__opt" onClick={() => current.pick(o.id)}>
              <span className="fit__emoji" aria-hidden="true">{o.emoji}</span>
              {o.label}
            </button>
          ))}
        </div>
        {step > 0 && <button className="link-arrow fit__back" onClick={() => setStep(step - 1)}>← Back</button>}
      </div>
    </div>
  )
}
