import { useEffect, useState } from 'react'
import { useChat } from '../lib/chat.ts'

const PROMPTS = [
  { teaser: 'Shopping for Mom? I’ll pick 3 in your budget.', ask: 'Gift ideas for my mom under $60' },
  { teaser: 'Not sure of your size? Ask me what’s left.', ask: 'Which hoodies are still in stock in medium?' },
  { teaser: 'Which college are you? I’ll find your crest.', ask: 'What do you have for my residential college?' },
  { teaser: 'Game this weekend? Let’s get you loud.', ask: 'What should I wear to the next football game?' },
]
const SEEN_KEY = 'cc-teaser-dismissed'

function dismissedBefore(): boolean {
  try {
    return window.sessionStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return false
  }
}

/** A small speech bubble beside the chat launcher, shown once per visit after a few
 *  seconds. Its question rotates; tapping it opens the chat with that question ready. */
export default function ChatTeaser() {
  const { openChat } = useChat()
  const [visible, setVisible] = useState(false)
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (dismissedBefore()) return
    const show = window.setTimeout(() => setVisible(true), 6000)
    const rotate = window.setInterval(() => setIndex((i) => (i + 1) % PROMPTS.length), 4500)
    return () => {
      window.clearTimeout(show)
      window.clearInterval(rotate)
    }
  }, [])

  function dismiss() {
    setVisible(false)
    try {
      window.sessionStorage.setItem(SEEN_KEY, '1')
    } catch {
      // storage blocked - it just shows again next visit
    }
  }

  if (!visible) return null
  const prompt = PROMPTS[index]
  return (
    <div className="teaser" role="complementary" aria-label="Shop assistant suggestion">
      <button className="teaser__body" onClick={() => { dismiss(); openChat(prompt.ask) }}>
        <span className="teaser__who">The Counter</span>
        <span key={index} className="teaser__text">{prompt.teaser}</span>
      </button>
      <button className="teaser__x" onClick={dismiss} aria-label="Dismiss suggestion">×</button>
    </div>
  )
}
