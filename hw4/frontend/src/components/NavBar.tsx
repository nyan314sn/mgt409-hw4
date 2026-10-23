import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth.ts'
import { useCart } from '../lib/cart.ts'

const PAGES = [
  { to: '/', label: 'Home' },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const { user, logout } = useAuth()
  const { count } = useCart()
  const navigate = useNavigate()

  async function onLogout() {
    setOpen(false)
    await logout()
    navigate('/')
  }

  return (
    <header className="nav">
      <div className="nav__inner">
        <Link to="/" className="brand" aria-label="Campus Customs home">
          <span className="brand__mark" aria-hidden="true">CC</span>
          <span className="brand__text">
            Campus Customs
            <small>57 Broadway · New Haven</small>
          </span>
        </Link>

        <NavLink to="/cart" className="nav__cart" aria-label={`Cart, ${count} item${count === 1 ? '' : 's'}`}>
          <span aria-hidden="true">🛍</span>
          {count > 0 && <span className="nav__badge" aria-hidden="true">{count}</span>}
        </NavLink>

        <button
          className="nav__toggle"
          aria-expanded={open}
          aria-controls="nav-menu"
          onClick={() => setOpen((o) => !o)}
        >
          <span className="sr-only">{open ? 'Close menu' : 'Open menu'}</span>
          <span className="nav__burger" aria-hidden="true" />
        </button>

        <nav id="nav-menu" className={`nav__menu${open ? ' is-open' : ''}`} aria-label="Main"
          onClick={(e) => (e.target as HTMLElement).closest('a') && setOpen(false)}>
          <ul className="nav__links">
            {PAGES.map((p) => (
              <li key={p.to}>
                <NavLink to={p.to} end={p.to === '/'} className="nav__link">
                  {p.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="nav__account">
            {user ? (
              <>
                <span className="nav__user">
                  <span className="nav__avatar" aria-hidden="true">{user.first_name.charAt(0).toUpperCase()}</span>
                  Hi, {user.first_name}
                </span>
                <NavLink to="/orders" className="nav__link">My orders</NavLink>
                {user.is_admin && <NavLink to="/admin/usage" className="nav__link">Usage</NavLink>}
                <button className="btn btn--ghost btn--sm" onClick={onLogout}>Log out</button>
              </>
            ) : (
              <>
                <NavLink to="/login" className="nav__link">Log in</NavLink>
                <NavLink to="/register" className="btn btn--primary btn--sm">Create account</NavLink>
              </>
            )}
          </div>
        </nav>
      </div>
    </header>
  )
}
