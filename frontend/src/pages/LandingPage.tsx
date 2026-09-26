import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

export default function LandingPage() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.analyze(url.trim());
      if (result.project_id) {
        navigate(`/projects/${result.project_id}`);
      } else {
        setError(result.detail ?? result.error ?? 'Failed to start analysis.');
      }
    } catch (err) {
      setError('Network error. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="landing">
      <div className="landing-inner">
        <div className="landing-logo">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
            <circle cx="24" cy="24" r="22" stroke="var(--accent)" strokeWidth="2" />
            <circle cx="24" cy="24" r="8" fill="var(--accent)" opacity="0.25" />
            <circle cx="24" cy="24" r="3" fill="var(--accent)" />
            <line x1="24" y1="2" x2="24" y2="14" stroke="var(--accent)" strokeWidth="1.5" />
            <line x1="24" y1="34" x2="24" y2="46" stroke="var(--accent)" strokeWidth="1.5" />
            <line x1="2" y1="24" x2="14" y2="24" stroke="var(--accent)" strokeWidth="1.5" />
            <line x1="34" y1="24" x2="46" y2="24" stroke="var(--accent)" strokeWidth="1.5" />
            <line x1="7.76" y1="7.76" x2="16.34" y2="16.34" stroke="var(--accent)" strokeWidth="1.5" />
            <line x1="31.66" y1="31.66" x2="40.24" y2="40.24" stroke="var(--accent)" strokeWidth="1.5" />
            <line x1="40.24" y1="7.76" x2="31.66" y2="16.34" stroke="var(--accent)" strokeWidth="1.5" />
            <line x1="16.34" y1="31.66" x2="7.76" y2="40.24" stroke="var(--accent)" strokeWidth="1.5" />
          </svg>
          <span className="landing-brand">CodeAtlas</span>
        </div>
        <p className="landing-tagline">Map any codebase. Understand any issue.</p>
        <form className="landing-form" onSubmit={handleSubmit}>
          <input
            className="landing-input"
            type="url"
            placeholder="https://github.com/owner/repo"
            value={url}
            onChange={e => setUrl(e.target.value)}
            disabled={loading}
            required
            aria-label="GitHub repository URL"
          />
          <button className="landing-btn" type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : 'Analyze'}
          </button>
        </form>
        {error && <div className="landing-error">{error}</div>}
      </div>
    </div>
  );
}
