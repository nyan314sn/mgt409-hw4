import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { ChatContext, type Spotlight } from '../lib/chat.ts'
import type { Showcase } from '../lib/chatApi.ts'

export default function ChatProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [focusSignal, setFocusSignal] = useState(0)
  const [prefill, setPrefill] = useState<string | null>(null)
  const [spotlight, setSpotlight] = useState<Spotlight | null>(null)
  const nextId = useRef(1)

  const openChat = useCallback((text?: string) => {
    setPrefill(text ?? null)
    setOpen(true)
    setFocusSignal((n) => n + 1)
  }, [])

  const showSpotlight = useCallback((showcase: Showcase, locationKey: string) => {
    // A fresh id replays the entrance animation even for the same products.
    setSpotlight({ showcase, locationKey, id: nextId.current++ })
  }, [])
  const closeSpotlight = useCallback(() => setSpotlight(null), [])

  const value = useMemo(
    () => ({ open, setOpen, openChat, prefill, focusSignal, spotlight, showSpotlight, closeSpotlight }),
    [open, openChat, prefill, focusSignal, spotlight, showSpotlight, closeSpotlight],
  )
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}
