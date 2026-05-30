import { Link, useLocation } from 'react-router-dom';

export default function Header() {
  const location = useLocation();

  return (
    <header className="app-header">
      <div className="header-container">
        <div className="header-brand">
          <Link to="/" className="brand-logo">
            <div className="logo-mark"></div>
            <span>SmartOnboard</span>
          </Link>
        </div>
        <nav className="header-nav">
          <Link 
            to="/dashboard" 
            className={`nav-link ${location.pathname === '/dashboard' ? 'active' : ''}`}
          >
            HR Dashboard
          </Link>
        </nav>
      </div>
    </header>
  );
}
