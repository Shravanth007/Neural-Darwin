import { agentColor } from '../lib/colors'

export default function AgentTable({ agents }) {
  if (!agents || agents.length === 0) {
    return <div className="panel agents-section"><div className="loading-state">No agents</div></div>
  }

  const sorted = [...agents].sort((a, b) => {
    if (a.alive !== b.alive) return a.alive ? -1 : 1
    return b.tokens - a.tokens
  })

  return (
    <div className="panel agents-section">
      <div className="panel-header">
        <span className="panel-title">Agents</span>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {agents.filter(a => a.alive).length} alive
        </span>
      </div>
      <div className="panel-body">
        <ul className="agent-list">
          {sorted.map(a => (
            <li key={a.agent_id} className={`agent-row ${a.alive ? '' : 'dead-row'}`}>
              <span
                className="agent-color-bar"
                style={{ background: agentColor(a.agent_id) }}
              />
              <span className="agent-name">
                {a.agent_id}
                <span className="agent-pos">({a.x},{a.y})</span>
                {a.inventory?.includes('Knife') && (
                  <span title="Has Knife" style={{ marginLeft: 4, fontSize: '11px' }}>🔪</span>
                )}
              </span>
              <span className="agent-tokens">{a.tokens.toLocaleString()}</span>
              <span className="agent-kills">{a.kills > 0 ? `${a.kills}K` : '–'}</span>
              <span className="agent-status">
                <span className={`status-dot ${a.alive ? 'alive' : 'dead'}`} />
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
