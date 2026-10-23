import { useSyncExternalStore } from 'react'

export type SizeStock = { size: string; quantity: number }

export type Product = {
  id: string
  name: string
  garmentType: string
  category: string
  description: string
  colors: string[]
  tags: string[]
  image: string
  price: number
  sizes: SizeStock[]
}

export const CATEGORIES = ['Hoodies', 'Crewnecks', 'Quarter-zips', 'Tees', 'Jackets']

export const RESIDENTIAL_COLLEGES = [
  'Benjamin Franklin', 'Berkeley', 'Branford', 'Davenport', 'Ezra Stiles',
  'Grace Hopper', 'Jonathan Edwards', 'Morse', 'Pauli Murray', 'Pierson',
  'Saybrook', 'Silliman', 'Timothy Dwight', 'Trumbull',
]

/** Curated "collections" shared by the Home tiles and the Products filter. */
export const COLLECTIONS = [
  { id: 'college', label: 'Residential colleges', pattern: new RegExp(RESIDENTIAL_COLLEGES.join('|'), 'i') },
  { id: 'teams', label: 'Bulldog teams', pattern: /baseball|basketball|football|hockey|soccer|tennis|squash|sailing|fencing|lacrosse|diving|swimming|golf|volleyball|track|field hockey/i },
  { id: 'family', label: 'Yale family', pattern: /\b(mom|dad|grandma|grandpa|aunt|uncle|brother|cousin)\b/i },
  { id: 'schools', label: 'Grad & professional', pattern: /school of|law school|divinity|forest school/i },
  { id: 'gameday', label: 'Game day', pattern: /harvard|the game|yale bowl|boola/i },
]

/** Group the many color names into a few families, keyed on the garment's main color. */
export const COLOR_FAMILIES: { id: string; label: string; swatch: string; pattern: RegExp }[] = [
  { id: 'navy', label: 'Navy', swatch: '#1c2b4f', pattern: /navy/ },
  { id: 'gray', label: 'Gray', swatch: '#9b9ba3', pattern: /gray|charcoal/ },
  { id: 'white', label: 'White & cream', swatch: '#f3efe6', pattern: /white|cream|ivory/ },
  { id: 'blue', label: 'Blue', swatch: '#3a6fd1', pattern: /blue/ },
  { id: 'black', label: 'Black', swatch: '#111114', pattern: /black/ },
  { id: 'warm', label: 'Red & coral', swatch: '#d9443f', pattern: /red|coral/ },
  { id: 'gold', label: 'Gold & yellow', swatch: '#e6b93a', pattern: /gold|yellow/ },
  { id: 'green', label: 'Green', swatch: '#3f8f5a', pattern: /green/ },
]

export function swatchFor(color: string): string {
  const family = COLOR_FAMILIES.find((f) => f.pattern.test(color.toLowerCase()))
  return family?.swatch ?? '#c9c4cf'
}

export function searchText(p: Product): string {
  return [p.id.replace(/-/g, ' '), p.name, p.description, ...p.tags].join(' ')
}

export function totalStock(p: Product): number {
  return p.sizes.reduce((sum, s) => sum + s.quantity, 0)
}

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

// ---------- live catalogue store ----------
// One shared copy of GET /api/products for the whole app. It refreshes every 45 seconds
// while the tab is visible and whenever the shopper comes back to the tab, so stock on
// cards and product pages doesn't go stale during a long visit. A failed refresh keeps the
// last good data on screen (with a note) instead of blanking the page.

export type CatalogueState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; products: Product[]; updatedAt: number; refreshing: boolean; refreshError: string | null }

const REFRESH_MS = 45_000
const STALE_ON_FOCUS_MS = 15_000

let state: CatalogueState = { status: 'loading' }
let inflight: Promise<void> | null = null
const listeners = new Set<() => void>()

function setState(next: CatalogueState) {
  state = next
  listeners.forEach((l) => l())
}

/** Fetch the latest products and stock. Safe to call often - concurrent calls share one request. */
export function refreshCatalogue(): Promise<void> {
  if (inflight) return inflight
  if (state.status === 'ready') setState({ ...state, refreshing: true })
  else if (state.status === 'error') setState({ status: 'loading' })
  inflight = fetch('/api/products')
    .then(async (res) => {
      if (res.status === 502 || res.status === 504) throw new Error('can’t reach the shop server')  // backend down
      if (!res.ok) throw new Error(`the server answered ${res.status}`)
      const products = (await res.json()) as Product[]
      setState({ status: 'ready', products, updatedAt: Date.now(), refreshing: false, refreshError: null })
    })
    .catch((err: Error) => {
      const message = err.message.includes('fetch') ? 'can’t reach the shop server' : err.message
      if (state.status === 'ready') setState({ ...state, refreshing: false, refreshError: message })
      else setState({ status: 'error', message })
    })
    .finally(() => { inflight = null })
  return inflight
}

function onWake() {
  if (document.visibilityState !== 'visible') return
  if (state.status !== 'ready' || Date.now() - state.updatedAt > STALE_ON_FOCUS_MS) void refreshCatalogue()
}

let timer: number | undefined

function subscribe(listener: () => void) {
  listeners.add(listener)
  if (listeners.size === 1) {
    if (state.status !== 'ready') void refreshCatalogue()
    timer = window.setInterval(() => { if (document.visibilityState === 'visible') void refreshCatalogue() }, REFRESH_MS)
    document.addEventListener('visibilitychange', onWake)
    window.addEventListener('focus', onWake)
    window.addEventListener('online', onWake)
  }
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', onWake)
      window.removeEventListener('focus', onWake)
      window.removeEventListener('online', onWake)
    }
  }
}

export function useCatalogue(): CatalogueState {
  return useSyncExternalStore(subscribe, () => state, () => state)
}
