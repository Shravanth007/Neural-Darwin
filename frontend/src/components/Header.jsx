export default function Header({ summary }) {
  if (!summary) return null

  const phase = summary.phase.toLowerCase()

  return (
    <header className="header">
      <span className="header-brand">Neural Darwin</span>

      <div className={`phase-badge ${phase}`}>
        <span className="pulse-dot" />
        {summary.phase}
      </div>

      <div className="header-stats">
        <div className="header-stat">
          <span className="header-stat-label">Tick</span>
          <span className="header-stat-value">{summary.tick}</span>
        </div>
        <div className="header-stat">
          <span className="header-stat-label">Day</span>
          <span className="header-stat-value">{summary.day}</span>
        </div>
        <div className="header-stat">
          <span className="header-stat-label">Alive</span>
          <span className="header-stat-value">{summary.living_count}</span>
        </div>
        <div className="header-stat">
          <span className="header-stat-label">Dead</span>
          <span className="header-stat-value">{summary.dead_count}</span>
        </div>
        <div className="header-stat">
          <span className="header-stat-label">Economy</span>
          <span className="header-stat-value">
            {summary.total_tokens?.toLocaleString()} ¤
          </span>
        </div>
        {summary.arena_busy && (
          <div className="header-stat">
            <span className="header-stat-label" style={{ color: '#dc2626', fontWeight: 700 }}>
              ⚔ DUEL
            </span>
          </div>
        )}
      </div>
    </header>
  )
}
