import { useEffect } from 'react'

const SITE = 'Campus Customs'

/** Sets the browser-tab title, e.g. "Saybrook College Crewneck · $58 | Campus Customs". */
export function useTitle(title?: string | null) {
  useEffect(() => {
    document.title = title ? `${title} | ${SITE}` : `${SITE} · Yale gear on Broadway`
  }, [title])
}
