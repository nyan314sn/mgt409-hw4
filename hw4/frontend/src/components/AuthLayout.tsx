import type { ReactNode } from 'react'

type Props = { eyebrow: string; title: string; aside: ReactNode; children: ReactNode }

export default function AuthLayout({ eyebrow, title, aside, children }: Props) {
  return (
    <div className="auth">
      <section className="auth__panel">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {children}
      </section>
      <aside className="auth__aside">{aside}</aside>
    </div>
  )
}
