import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../lib/auth.ts'
import { useTitle } from '../lib/useTitle.ts'

type Run = {
  id: number; createdAt: string; kind: string; who: string; status: string; error: string | null
  durationMs: number; requests: number; inputTokens: number; outputTokens: number; costUsd: number | null
  toolCalls: { tool: string; args: string }[]; showcaseCount: number
}
type Report = {
  days: number
  prices: { inputPerMTok: number; outputPerMTok: number }
  totals: { runs: number; errors: number; inputTokens: number; outputTokens: number; costUsd: number; avgMs: number; shoppers: number }
  byDay: { day: string; runs: number; costUsd: number; tokens: number }[]
  tools: { tool: string; calls: number }[]
  recent: Run[]
}

const usd = (n: number) => `$${n < 1 ? n.toFixed(4) : n.toFixed(2)}`
const num = (n: number) => n.toLocaleString('en-US')

/** Single-series column chart: estimated cost per day. One color (no legend needed - the
 *  heading names it), 4px rounded tops, hairline baseline, hover/focus tooltip, max labelled. */
function CostByDay({ days }: { days: Report['byDay'] }) {
  const [hover, setHover] = useState<number | null>(null)
  if (days.length === 0) return <p className="muted">No agent runs in this period yet.</p>
  const max = Math.max(...days.map((d) => d.costUsd), 0.0001)
  const peak = days.findIndex((d) => d.costUsd === max)
  return (
    <figure className="usagechart">
      <div className="usagechart__plot" role="img" aria-label="Estimated cost per day; values are in the table below">
        {days.map((d, i) => (
          <div key={d.day} className="usagechart__col" tabIndex={0}
            onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(i)} onBlur={() => setHover(null)}>
            {(i === peak || hover === i) && (
              <span className={`usagechart__tip${hover === i ? ' is-hover' : ''}`}>
                {hover === i ? `${d.day} · ${usd(d.costUsd)} · ${d.runs} runs` : usd(d.costUsd)}
              </span>
            )}
            <span className="usagechart__bar" style={{ height: `${Math.max(2, (d.costUsd / max) * 100)}%` }} />
            <span className="usagechart__x">{d.day.slice(5)}</span>
          </div>
        ))}
      </div>
      <details>
        <summary>Show as table</summary>
        <table className="usagetable">
          <thead><tr><th>Day</th><th>Runs</th><th>Tokens</th><th>Est. cost</th></tr></thead>
          <tbody>{days.map((d) => <tr key={d.day}><td>{d.day}</td><td>{d.runs}</td><td>{num(d.tokens)}</td><td>{usd(d.costUsd)}</td></tr>)}</tbody>
        </table>
      </details>
    </figure>
  )
}

export default function AdminUsage() {
  const { user } = useAuth()
  const [days, setDays] = useState(7)
  const [state, setState] = useState<{ days: number; report?: Report; error?: string } | null>(null)
  const [attempt, setAttempt] = useState(0)
  useTitle('Assistant usage & cost')

  useEffect(() => {
    if (!user?.is_admin) return
    let active = true
    fetch(`/api/admin/usage?days=${days}`, { credentials: 'same-origin' })
      .then(async (res) => {
        if (!res.ok) throw new Error(`the server answered ${res.status}`)
        return res.json() as Promise<Report>
      })
      .then((report) => active && setState({ days, report }))
      .catch((err: Error) => active && setState({ days, error: err.message.includes('fetch') ? 'can’t reach the shop server' : err.message }))
    return () => { active = false }
  }, [user, days, attempt])

  if (user === undefined) return <div className="page"><p className="status" role="status">Loading…</p></div>
  if (!user?.is_admin) {
    return (
      <div className="page page--center">
        <p className="eyebrow">Staff only</p>
        <h1>This page is for shop staff.</h1>
        <Link to="/" className="btn btn--primary">Back to the shop</Link>
      </div>
    )
  }

  const current = state?.days === days ? state : null
  const r = current?.report
  const maxTool = Math.max(1, ...(r?.tools.map((t) => t.calls) ?? [1]))

  return (
    <div className="page">
      <header className="page__head usagehead">
        <div>
          <p className="eyebrow">Staff · shop assistant</p>
          <h1>Usage & cost</h1>
          <p className="muted">Every chat turn and history summary, with the tools the assistant called, tokens, and an estimated cost.</p>
        </div>
        <div className="chips" role="group" aria-label="Period">
          {[1, 7, 30].map((d) => (
            <button key={d} className={`chip${days === d ? ' is-active' : ''}`} aria-pressed={days === d} onClick={() => setDays(d)}>
              {d === 1 ? 'Today' : `${d} days`}
            </button>
          ))}
        </div>
      </header>

      {!current && <p className="status" role="status">Loading usage…</p>}
      {current?.error && (
        <div className="status status--error loaderror" role="alert">
          <p>Couldn’t load usage: {current.error}.</p>
          <button className="btn btn--primary btn--sm" onClick={() => { setState(null); setAttempt((n) => n + 1) }}>Try again</button>
        </div>
      )}

      {r && (
        <>
          <div className="tiles">
            <div className="tile"><span>Agent runs</span><strong>{num(r.totals.runs)}</strong><small>{r.totals.shoppers} shoppers</small></div>
            <div className="tile"><span>Estimated cost</span><strong>{usd(r.totals.costUsd)}</strong><small>at ${r.prices.inputPerMTok}/${r.prices.outputPerMTok} per 1M tokens</small></div>
            <div className="tile"><span>Tokens</span><strong>{num(r.totals.inputTokens + r.totals.outputTokens)}</strong><small>{num(r.totals.inputTokens)} in · {num(r.totals.outputTokens)} out</small></div>
            <div className="tile"><span>Avg. response</span><strong>{(r.totals.avgMs / 1000).toFixed(1)}s</strong><small>{r.totals.errors} errors</small></div>
          </div>

          <div className="usagegrid">
            <section className="panel">
              <h2>Estimated cost per day</h2>
              <CostByDay days={r.byDay} />
            </section>
            <section className="panel">
              <h2>Tools called</h2>
              {r.tools.length === 0 && <p className="muted">No tool calls yet.</p>}
              <ul className="toolbars">
                {r.tools.map((t) => (
                  <li key={t.tool}>
                    <span className="toolbars__name">{t.tool}</span>
                    <span className="toolbars__track"><span style={{ width: `${(t.calls / maxTool) * 100}%` }} /></span>
                    <span className="toolbars__n">{t.calls}</span>
                  </li>
                ))}
              </ul>
            </section>
          </div>

          <section className="panel">
            <h2>Recent runs</h2>
            <div className="tablewrap">
              <table className="usagetable">
                <thead>
                  <tr><th>When (UTC)</th><th>Who</th><th>Kind</th><th>Status</th><th>Tools called</th><th>Tokens in/out</th><th>Time</th><th>Est. cost</th></tr>
                </thead>
                <tbody>
                  {r.recent.map((run) => (
                    <tr key={run.id} className={run.status === 'error' ? 'is-error' : ''}>
                      <td>{run.createdAt.slice(5, 16)}</td>
                      <td>{run.who}</td>
                      <td>{run.kind}</td>
                      <td>{run.status === 'ok' ? '✓ ok' : `✕ ${run.error ?? 'error'}`}</td>
                      <td>{run.toolCalls.length ? run.toolCalls.map((c, i) => <code key={i} title={c.args}>{c.tool}</code>) : '—'}</td>
                      <td>{num(run.inputTokens)} / {num(run.outputTokens)}</td>
                      <td>{(run.durationMs / 1000).toFixed(1)}s</td>
                      <td>{run.costUsd !== null ? usd(run.costUsd) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
