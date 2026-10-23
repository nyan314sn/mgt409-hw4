import { createContext, useContext } from 'react'
import type { Showcase } from './chatApi.ts'

/** A showcase on screen, tied to the page (location key) it was opened on. */
export type Spotlight = { showcase: Showcase; locationKey: string; id: number }

export type ChatContextValue = {
  open: boolean
  setOpen: (open: boolean) => void
  /** Open the chat panel (e.g. "Ask about this item" on a product page). The page itself
   *  tells the assistant which product "this" is - see ChatWidget's page context. */
  openChat: (prefill?: string) => void
  /** Text to put in the message box when the chat opens (e.g. from the teaser bubble). */
  prefill: string | null
  /** Bumped by openChat so the panel can focus its input. */
  focusSignal: number
  /** Products the assistant put on the page (the Spotlight), or null. */
  spotlight: Spotlight | null
  showSpotlight: (showcase: Showcase, locationKey: string) => void
  closeSpotlight: () => void
}

export const ChatContext = createContext<ChatContextValue | null>(null)

export function useChat(): ChatContextValue {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used inside <ChatProvider>')
  return ctx
}
