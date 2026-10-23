import { useEffect, useState } from 'react'
import { refreshCatalogue, useCatalogue } from '../lib/catalogue.ts'

function ago(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 10) return 'just now'
  if (s < 60) return `${s}s ago`
  return `${Math.round(s / 60)} min ago`
}

/** "● Live stock · updated 20s ago ↻" - shows how fresh the stock numbers are. */
export default function LiveStock() {
  const catalogue = useCatalogue()
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 5000)
    return () => window.clearInterval(id)
  }, [])

  if (catalogue.status !== 'ready') return null
  const { updatedAt, refreshing, refreshError } = catalogue
  return (
    <p className={`livestock${refreshError ? ' is-stale' : ''}`} role="status">
      <span className="livestock__dot" aria-hidden="true" />
      {refreshError
        ? <>Couldn’t refresh stock ({refreshError}). Showing numbers from {ago(now - updatedAt)}.</>
        : <>Live stock · updated {refreshing ? 'now…' : ago(now - updatedAt)}</>}
      <button className="livestock__btn" onClick={() => void refreshCatalogue()} disabled={refreshing}
        aria-label="Refresh stock now">↻</button>
    </p>
  )
}
