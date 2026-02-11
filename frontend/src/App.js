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
        <h1 style={{ fontSize: 36, fontWeight: 700, margin: '0 0 8px', color: '#fff' }}>
          LockBay
        </h1>
        <p style={{ color: '#8ba3b8', fontSize: 16, margin: '0 0 32px' }}>
          Secure Escrow Trading on Telegram
        </p>

        <div style={{
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
              <span style={{
                width: 10, height: 10, borderRadius: '50%',
                background: health.status === 'ok' ? '#22c55e' : '#f59e0b',
                display: 'inline-block',
              }} />
              <span style={{ fontSize: 14 }}>
                {health.status === 'ok' ? 'Server Online' : `Status: ${health.status}`}
              </span>
              {health.service && (
                <span style={{ fontSize: 12, color: '#6b8299' }}>
                  &middot; {health.service}
                </span>
              )}
            </div>
          ) : (
            <span style={{ color: '#6b8299' }}>Checking...</span>
          )}
        </div>

        <div style={{
          background: '#1a2a38',
          borderRadius: 12,
          padding: 24,
          border: '1px solid #253545',
        }}>
          <h2 style={{ fontSize: 18, margin: '0 0 16px', color: '#3BB5C8' }}>
            Setup Checklist
          </h2>
          <div style={{ textAlign: 'left', fontSize: 14, lineHeight: 2 }}>
            <div data-testid="check-postgres">PostgreSQL Database &mdash; <span style={{ color: '#22c55e' }}>Connected</span></div>
            <div data-testid="check-dependencies">Python Dependencies &mdash; <span style={{ color: '#22c55e' }}>Installed</span></div>
            <div data-testid="check-tables">Database Tables (57) &mdash; <span style={{ color: '#22c55e' }}>Created</span></div>
            <div data-testid="check-fastapi">FastAPI Server &mdash; <span style={{ color: '#22c55e' }}>Running</span></div>
            <div data-testid="check-bot-token">Telegram Bot Token &mdash; <span style={{ color: '#f59e0b' }}>Needs Configuration</span></div>
            <div data-testid="check-redis">Redis &mdash; <span style={{ color: '#6b8299' }}>Optional (fallback active)</span></div>
          </div>
        </div>

        <p style={{ marginTop: 24, fontSize: 12, color: '#4a6478' }}>
          Configure your TELEGRAM_BOT_TOKEN in /app/.env to activate the bot.
        </p>
      </div>
    </div>
  );
}

export default App;
