import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <div>
          <p className="footer__brand">Campus Customs</p>
          <p className="muted">57 Broadway, New Haven, CT</p>
        </div>
        <nav aria-label="Footer">
          <ul className="footer__links">
            <li><Link to="/products">Shop all</Link></li>
            <li><Link to="/about">Our story</Link></li>
            <li><Link to="/login">Log in</Link></li>
            <li><Link to="/register">Create account</Link></li>
          </ul>
        </nav>
      </div>
      <p className="footer__note">
        A class project for Yale SOM MGT 409. Campus Customs and Yale Bulldog Blue are a local
        setting for the course. This site is not affiliated with or endorsed by Campus Customs
        or Yale University.
      </p>
    </footer>
  )
}
