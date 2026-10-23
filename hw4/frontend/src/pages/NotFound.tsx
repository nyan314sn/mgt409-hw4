import { Link } from 'react-router-dom'
import { useTitle } from '../lib/useTitle.ts'

export default function NotFound() {
  useTitle('Page not found')
  return (
    <div className="page page--center">
      <p className="eyebrow">404</p>
      <h1>Handsome Dan buried this page.</h1>
      <p className="muted">The page you’re looking for isn’t here.</p>
      <Link to="/" className="btn btn--primary">Back to home</Link>
    </div>
  )
}
