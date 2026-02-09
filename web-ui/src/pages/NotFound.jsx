import { Link } from 'react-router-dom';

function NotFound() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
      <div className="card" style={{ textAlign: 'center', maxWidth: 380, padding: 40 }}>
        <div style={{ fontSize: 48, fontWeight: 800, color: 'var(--text-muted)', marginBottom: 4, letterSpacing: '-0.04em' }}>404</div>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 20, fontSize: 14 }}>Page not found.</p>
        <Link to="/" className="btn btn-primary" style={{ textDecoration: 'none' }}>Dashboard</Link>
      </div>
    </div>
  );
}

export default NotFound;
