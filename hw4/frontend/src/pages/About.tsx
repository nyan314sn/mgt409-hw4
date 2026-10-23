import { Link } from 'react-router-dom'
import { useTitle } from '../lib/useTitle.ts'

const CHAPTERS = [
  {
    when: 'The 1970s',
    title: 'A storefront on Broadway',
    body: 'Campus Customs opened its doors on Broadway when bell-bottoms were still a thing, and it has been dressing Bulldogs from the same corner of New Haven ever since.',
  },
  {
    when: 'Along the way',
    title: 'Ink and thread, close to home',
    body: 'The family behind the shop added its own screen printing and embroidery, so team shirts, club gear, and reunion orders could come together without leaving Connecticut.',
  },
  {
    when: 'Today',
    title: 'Gear for every Yale chapter',
    body: 'First-years, grad students, alumni, coaches, and the grandparents who drive in for The Game. If you have a Yale story, there’s something on the rack for it.',
  },
]

const VALUES = [
  { icon: '✦', title: 'Officially licensed', body: 'Real crests, real marks, done right. No knock-offs, no guesswork.' },
  { icon: '♥', title: 'Family-run', body: 'A local family business, not a faceless warehouse. You can walk in and say hello.' },
  { icon: '✂', title: 'Made nearby', body: 'Printing and embroidery from a Connecticut production shop, ready for teams and events.' },
  { icon: '★', title: 'For everyone', body: 'Students, parents, alumni, and fans — sized XS to XXL, with tees, crews, and layers at every price point.' },
]

export default function About() {
  useTitle('About us')
  return (
    <div className="page">
      <header className="page__head page__head--wide">
        <p className="eyebrow">About us</p>
        <h1>A Broadway shop with a <span className="accent">Bulldog</span> heart.</h1>
        <p className="lede">
          We’re the shop you walk past on the way to class, the one with the hoodie wall you’ve
          been eyeing since move-in. For decades we’ve been outfitting Yale students, families,
          and alumni with gear that feels like home, whether home is a dorm in Old Campus or a
          living room three time zones away.
        </p>
      </header>

      <section className="section section--flush">
        <ol className="timeline">
          {CHAPTERS.map((c) => (
            <li key={c.title} className="timeline__item">
              <p className="timeline__when">{c.when}</p>
              <h2>{c.title}</h2>
              <p>{c.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="section section--flush">
        <h2 className="section__title">What we stand for</h2>
        <div className="values">
          {VALUES.map((v) => (
            <div key={v.title} className="value">
              <span className="value__icon" aria-hidden="true">{v.icon}</span>
              <h3>{v.title}</h3>
              <p>{v.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section section--flush">
        <blockquote className="pull">
          “A sweatshirt is never just a sweatshirt. It’s the one you wore to The Game, to the
          library at 2 a.m., and to your kid’s move-in day twenty years later.”
          <cite>— the Campus Customs way of thinking</cite>
        </blockquote>
      </section>

      <section className="section section--flush visit">
        <div>
          <h2>Visit the shop</h2>
          <p>
            Find us at 57 Broadway, a few minutes from Old Campus. Need shirts for a team, club, or
            reunion? Ask us about custom printing and embroidery.
          </p>
          <Link to="/products" className="btn btn--primary">Browse products</Link>
        </div>
        <address className="visit__card">
          <strong>Campus Customs</strong>
          57 Broadway<br />New Haven, CT
          <a href="https://maps.google.com/?q=57+Broadway+New+Haven+CT" target="_blank" rel="noreferrer">
            Get directions ↗
          </a>
        </address>
      </section>
    </div>
  )
}
