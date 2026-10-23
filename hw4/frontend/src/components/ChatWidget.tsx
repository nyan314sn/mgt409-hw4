import { useEffect, useRef, useState, type FormEvent } from 'react'
import ChatTeaser from './ChatTeaser.tsx'
import { Link, matchPath, useLocation } from 'react-router-dom'
import RichText from './RichText.tsx'
import { useAuth } from '../lib/auth.ts'
import { ApiError, type User } from '../lib/authApi.ts'
import { useCatalogue } from '../lib/catalogue.ts'
import { useChat } from '../lib/chat.ts'
import {
  fetchChatHistory, sendChatMessage, type ChatMessage, type PageContext, type Showcase,
} from '../lib/chatApi.ts'

const SUGGESTIONS = ['What hoodies do you have?', 'Gift ideas for a Yale dad under $60', 'Anything for Saybrook?']
const PRODUCT_SUGGESTIONS = ['Do you have this in pink?', 'Is it in stock in medium?', 'What colors does it come in?']
const FOLLOW_UPS = ['Which is the cheapest?', 'Any in navy?', 'What’s in stock in M?']

/** Below this width the chat panel covers the page, so it steps aside for the Spotlight. */
const NARROW = '(max-width: 900px)'

export default function ChatWidget() {
  const { open, setOpen } = useChat()
  const { user } = useAuth()

  return (
    <div className="chat">
      {open && (
        <section
          className="chat__panel"
          role="dialog"
          aria-label="Shop assistant chat"
          onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
        >
          <header className="chat__head">
            <span className="chat__avatar" aria-hidden="true">CC</span>
            <div>
              <p className="chat__title">The Counter <small>· shop assistant</small></p>
              <p className="chat__sub">
                <span className="chat__dot is-live" aria-hidden="true" />
                {user ? 'Online · saved to your account' : 'Online · guest chat, not saved'}
              </p>
            </div>
            <button className="chat__close" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
          </header>
          {user === undefined
            ? <p className="chat__gate muted" role="status">Loading…</p>
            // key: logging in or out starts a fresh conversation view (guest chats end at login).
            : <Conversation key={user ? `user-${user.id}` : 'guest'} user={user} />}
        </section>
      )}

      {!open && <ChatTeaser />}
      <button
        className={`chat__launcher${open ? ' is-open' : ''}`}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-label={open ? 'Close shop assistant' : 'Open shop assistant'}
      >
        {open ? '×' : (
          <>
            <span className="chat__launcher-ring" aria-hidden="true" />
            <span aria-hidden="true">💬</span>
            <span className="chat__launcher-text">Ask the counter</span>
          </>
        )}
      </button>
    </div>
  )
}

function Conversation({ user }: { user: User | null }) {
  const { setOpen, focusSignal, spotlight, showSpotlight, prefill } = useChat()
  const location = useLocation()
  const catalogue = useCatalogue()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [restored, setRestored] = useState(0)
  const [historyState, setHistoryState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [draft, setDraft] = useState(prefill ?? '')
  const [pending, setPending] = useState(false)
  // A message that didn't go through: kept on screen with a "Try again" button.
  const [failed, setFailed] = useState<{ message: string; error: string; canRetry: boolean } | null>(null)
  const [historyAttempt, setHistoryAttempt] = useState(0)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Product page the shopper is on, if any - shown as a chip and sent as page context.
  const productId = matchPath('/products/:id', location.pathname)?.params.id
  const pageProduct = productId && catalogue.status === 'ready'
    ? catalogue.products.find((p) => p.id === productId) ?? null
    : null
  const spotlightHere = spotlight && spotlight.locationKey === location.key ? spotlight : null

  /** Sent with every message so the assistant knows what "this" or "the second one" means. */
  function pageContext(): PageContext {
    return {
      path: location.pathname + location.search,
      spotlightProductIds: spotlightHere?.showcase.products.map((p) => p.id) ?? [],
      spotlightTitle: spotlightHere?.showcase.title ?? null,
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    fetchChatHistory(controller.signal)
      .then((history) => {
        setMessages(history.messages)
        setRestored(history.messages.length)
        setHistoryState('ready')
      })
      .catch((err) => { if ((err as Error).name !== 'AbortError') setHistoryState('error') })
    return () => controller.abort()
  }, [historyAttempt])

  function retryHistory() {
    setHistoryState('loading')
    setHistoryAttempt((n) => n + 1)
  }

  useEffect(() => { inputRef.current?.focus() }, [focusSignal])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, pending, historyState])

  useEffect(() => () => abortRef.current?.abort(), [])

  function putOnPage(showcase: Showcase, pageKey = location.key) {
    showSpotlight(showcase, pageKey)
    if (window.matchMedia(NARROW).matches) setOpen(false)
  }

  async function send(text: string) {
    const message = text.trim()
    if (!message || pending) return
    setMessages((m) => [...m, { role: 'user', content: message }])
    setDraft('')
    setFailed(null)
    setPending(true)

    abortRef.current = new AbortController()
    try {
      const pageKey = location.key
      const reply = await sendChatMessage({ message, page: pageContext() }, abortRef.current.signal)
      // Two separate parts: the text goes in the bubble, the products go on the page.
      setMessages((m) => [...m, { role: 'assistant', content: reply.message.content, showcase: reply.showcase }])
      if (reply.showcase) putOnPage(reply.showcase, pageKey)
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      // The server saves nothing for a failed turn: take the message out of the log and offer
      // to send it again (rate limits say when; retrying right away wouldn't help).
      setMessages((m) => m.slice(0, -1))
      const limited = err instanceof ApiError && err.status === 429
      setFailed({
        message,
        canRetry: !limited,
        error: err instanceof ApiError
          ? (err.status === 0 ? 'Couldn’t reach the shop - check your connection.' : err.message)
          : 'Sorry, the assistant couldn’t answer.',
      })
    } finally {
      setPending(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void send(draft)
  }

  function bubble(m: ChatMessage, key: string) {
    return (
      <div key={key} className={`bubble bubble--${m.role}`}>
        {m.role === 'assistant' ? <RichText text={m.content} /> : <p>{m.content}</p>}
        {m.showcase && (
          <ShowcaseChip
            showcase={m.showcase}
            onScreen={spotlightHere?.showcase === m.showcase}
            onShow={() => putOnPage(m.showcase!)}
          />
        )}
      </div>
    )
  }

  const greeting: ChatMessage = {
    role: 'assistant',
    content: user
      ? (restored > 0
        ? `Welcome back, ${user.first_name}! Your earlier chat is above. What can I help you find today?`
        : `Hi ${user.first_name}! I’m the Campus Customs shop assistant. Ask me about sizes, colors, stock, or gift ideas.`)
      : 'Hi there! I’m the Campus Customs shop assistant. Ask me about sizes, colors, stock, or gift ideas.',
  }
  const suggestions = pageProduct ? PRODUCT_SUGGESTIONS : SUGGESTIONS
  // After a reply that put products on the page, offer quick ways to narrow them down.
  const last = messages[messages.length - 1]
  const lastShowcase = messages.length > restored && last?.role === 'assistant' && !!last.showcase

  return (
    <>
      <div className="chat__log" ref={logRef} role="log" aria-live="polite" aria-busy={pending}>
        {messages.slice(0, restored).map((m, i) => bubble(m, `h${i}`))}
        {restored > 0 && <p className="chat__divider"><span>Earlier conversation ↑</span></p>}
        {bubble(greeting, 'greeting')}
        {messages.slice(restored).map((m, i) => bubble(m, `n${i}`))}
        {historyState === 'loading' && <p className="chat__note" role="status">Loading your conversation…</p>}
        {historyState === 'error' && (
          <div className="chat__error" role="alert">
            Couldn’t load your earlier messages.{' '}
            <button className="chat__retry" onClick={retryHistory}>Try again</button>
          </div>
        )}
        {pending && (
          <div className="bubble bubble--assistant bubble--typing" aria-label="Assistant is typing">
            <span>🐾</span><span>🐾</span><span>🐾</span>
          </div>
        )}
        {failed && (
          <div className="bubble bubble--user bubble--failed">
            <p>{failed.message}</p>
            <div className="chat__failnote" role="alert">
              <span>⚠ Not sent. {failed.error}</span>
              <span className="chat__failactions">
                {failed.canRetry && (
                  <button className="chat__retry" onClick={() => void send(failed.message)} disabled={pending}>↻ Try again</button>
                )}
                <button className="chat__retry chat__retry--quiet" onClick={() => { setDraft(failed.message); setFailed(null) }}>Edit</button>
              </span>
            </div>
          </div>
        )}
      </div>

      {lastShowcase && !pending && !failed && (
        <div className="chat__suggestions chat__suggestions--follow">
          {FOLLOW_UPS.map((s) => (
            <button key={s} className="chip" onClick={() => void send(s)}>{s}</button>
          ))}
        </div>
      )}

      {historyState === 'ready' && messages.length === restored && !pending && (
        <div className="chat__suggestions">
          {suggestions.map((s) => (
            <button key={s} className="chip" onClick={() => void send(s)}>{s}</button>
          ))}
        </div>
      )}

      {pageProduct && (
        <div className="chat__topic" title="The assistant knows which product page you're on">
          <img src={pageProduct.image} alt="" />
          <span>On this page: <strong>{pageProduct.name}</strong></span>
        </div>
      )}
      {!user && (
        <p className="chat__guest">
          Chatting as a guest. <Link to="/login" state={{ from: location.pathname }} onClick={() => setOpen(false)}>Log in</Link> to save this conversation.
        </p>
      )}

      <form className="chat__form" onSubmit={onSubmit}>
        <label htmlFor="chat-input" className="sr-only">Message</label>
        <textarea
          id="chat-input"
          ref={inputRef}
          rows={1}
          maxLength={1000}
          value={draft}
          placeholder={pageProduct ? `Ask about the ${pageProduct.name}…` : 'Ask about anything on the rack…'}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send(draft)
            }
          }}
        />
        <button type="submit" className="chat__send" disabled={!draft.trim() || pending} aria-label="Send message">
          ↑
        </button>
      </form>
    </>
  )
}

/** In the bubble, a showcase is just a pointer to the page - the cards live in the Spotlight. */
function ShowcaseChip({ showcase, onScreen, onShow }: { showcase: Showcase; onScreen: boolean; onShow: () => void }) {
  const thumbs = showcase.products.slice(0, 3)
  const n = showcase.products.length
  return (
    <button className={`showchip${onScreen ? ' is-on' : ''}`} onClick={onShow} aria-pressed={onScreen}>
      <span className="showchip__thumbs" aria-hidden="true">
        {thumbs.map((p) => <img key={p.id} src={p.image} alt="" />)}
      </span>
      <span className="showchip__text">
        <strong>{showcase.title}</strong>
        <small>{onScreen ? `${n} on your screen now` : `Show ${n} ${n === 1 ? 'item' : 'items'} on the page`}</small>
      </span>
      <span className="showchip__icon" aria-hidden="true">{onScreen ? '✦' : '↗'}</span>
    </button>
  )
}
