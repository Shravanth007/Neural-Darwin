import { agentColor } from '../lib/colors'

export default function WealthChart({ agents }) {
  if (!agents || agents.length === 0) {
    return (
      <div className="panel">
        <div className="panel-header"><span className="panel-title">Wealth</span></div>
        <div className="loading-state">No data</div>
      </div>
    )
  }

  const living = agents.filter(a => a.alive).sort((a, b) => b.tokens - a.tokens)
  const maxTokens = Math.max(1, ...living.map(a => a.tokens))

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Wealth</span>
      </div>
      <div className="panel-body">
        <div className="wealth-chart">
          {living.map(a => {
            const pct = Math.max(3, (a.tokens / maxTokens) * 100)
            const color = agentColor(a.agent_id)
            return (
              <div key={a.agent_id} className="wealth-bar-container">
                <div className="wealth-bar-value">
                  {a.tokens >= 1000 ? `${(a.tokens / 1000).toFixed(1)}k` : a.tokens}
                </div>
                <div className="wealth-bar-track">
                  <div
                    className="wealth-bar"
                    style={{
                      height: `${pct}%`,
                      background: color,
                      opacity: 0.85,
                    }}
                  />
                </div>
                <div className="wealth-bar-label">
                  {a.agent_id.replace('Agent_', 'A').replace('Heir_', 'H')}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
