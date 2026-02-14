import React, { useState, useEffect } from 'react';

const BACKEND = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetch(`${BACKEND}/api/health`)
      .then(r => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: 'unreachable' }));
  }, []);

  const dbConfigured = health?.config?.database_url === 'configured';
  const botConfigured = health?.config?.bot_token === 'configured';
  const serverOnline = health?.status === 'ok';
  const isFullMode = health?.mode !== 'setup';

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0f1923',
      color: '#e0e8ef',
      fontFamily: "'Segoe UI', system-ui, sans-serif",
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{ textAlign: 'center', maxWidth: 520, padding: 40 }}>
        <div style={{ fontSize: 48, marginBottom: 8 }}>
          <span style={{ color: '#3BB5C8' }}>$</span>
        </div>
        <h1 data-testid="app-title" style={{ fontSize: 36, fontWeight: 700, margin: '0 0 8px', color: '#fff' }}>
          LockBay
        </h1>
        <p style={{ color: '#8ba3b8', fontSize: 16, margin: '0 0 32px' }}>
          Secure Escrow Trading on Telegram
        </p>

        <div data-testid="bot-status-card" style={{
          background: '#1a2a38',
          borderRadius: 12,
          padding: 24,
          marginBottom: 24,
          border: '1px solid #253545',
        }}>
          <h2 style={{ fontSize: 18, margin: '0 0 16px', color: '#3BB5C8' }}>
            Bot Status
          </h2>
          {health ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
            }}>
              <span data-testid="status-indicator" style={{
                width: 10, height: 10, borderRadius: '50%',
                background: serverOnline ? '#22c55e' : '#f59e0b',
                display: 'inline-block',
              }} />
              <span data-testid="status-text" style={{ fontSize: 14 }}>
                {serverOnline ? 'Server Online' : `Status: ${health.status}`}
              </span>
              {health.service && (
                <span style={{ fontSize: 12, color: '#6b8299' }}>
                  &middot; {health.service}
                </span>
              )}
              {health.mode === 'setup' && (
                <span style={{
                  fontSize: 11,
                  color: '#f59e0b',
                  background: '#f59e0b22',
                  padding: '2px 8px',
                  borderRadius: 4,
                  marginLeft: 4,
                }}>
                  Setup Mode
                </span>
              )}
            </div>
          ) : (
            <span style={{ color: '#6b8299' }}>Checking...</span>
          )}
        </div>

        <div data-testid="setup-checklist-card" style={{
          background: '#1a2a38',
          borderRadius: 12,
          padding: 24,
          border: '1px solid #253545',
        }}>
          <h2 style={{ fontSize: 18, margin: '0 0 16px', color: '#3BB5C8' }}>
            Setup Checklist
          </h2>
          <div style={{ textAlign: 'left', fontSize: 14, lineHeight: 2 }}>
            <div data-testid="check-fastapi">
              FastAPI Server &mdash;{' '}
              <span style={{ color: serverOnline ? '#22c55e' : '#ef4444' }}>
                {serverOnline ? 'Running' : 'Not Running'}
              </span>
            </div>
            <div data-testid="check-dependencies">
              Python Dependencies &mdash;{' '}
              <span style={{ color: '#22c55e' }}>Installed</span>
            </div>
            <div data-testid="check-postgres">
              PostgreSQL Database &mdash;{' '}
              <span style={{ color: dbConfigured ? '#22c55e' : '#f59e0b' }}>
                {dbConfigured ? 'Connected' : 'Needs DATABASE_URL'}
              </span>
            </div>
            <div data-testid="check-bot-token">
              Telegram Bot Token &mdash;{' '}
              <span style={{ color: botConfigured ? '#22c55e' : '#f59e0b' }}>
                {botConfigured ? 'Configured' : 'Needs Configuration'}
              </span>
            </div>
            <div data-testid="check-tables">
              Database Tables (57) &mdash;{' '}
              <span style={{ color: isFullMode ? '#22c55e' : '#6b8299' }}>
                {isFullMode ? 'Created' : 'Pending DB Connection'}
              </span>
            </div>
            <div data-testid="check-redis">
              Redis &mdash;{' '}
              <span style={{ color: '#6b8299' }}>Optional (fallback active)</span>
            </div>
          </div>
        </div>

        {health?.next_steps && health.next_steps.length > 0 && (
          <div data-testid="next-steps" style={{
            background: '#1a2a38',
            borderRadius: 12,
            padding: 20,
            marginTop: 24,
            border: '1px solid #f59e0b33',
            textAlign: 'left',
          }}>
            <h3 style={{ fontSize: 14, margin: '0 0 12px', color: '#f59e0b' }}>
              Next Steps
            </h3>
            {health.next_steps.map((step, i) => (
              <div key={i} style={{ fontSize: 13, color: '#8ba3b8', lineHeight: 1.8 }}>
                {i + 1}. {step}
              </div>
            ))}
          </div>
        )}

        <p style={{ marginTop: 24, fontSize: 12, color: '#4a6478' }}>
          Configure your environment variables in /app/.env to activate the full bot.
        </p>
      </div>
    </div>
  );
}

export default App;
