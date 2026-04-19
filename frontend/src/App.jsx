import { useSimulation } from './hooks/useSimulation'
import Header from './components/Header'
import WorldMap from './components/WorldMap'
import AgentTable from './components/AgentTable'
import EventFeed from './components/EventFeed'
import WealthChart from './components/WealthChart'

export default function App() {
  const { state, loading, error } = useSimulation(3000)

  if (loading && !state) {
    return (
      <div className="app-shell">
        <div className="loading-state" style={{ height: '100vh' }}>
          <span className="spinner" />
          Connecting to simulation…
        </div>
      </div>
    )
  }

  if (error && !state) {
    return (
      <div className="app-shell">
        <div className="error-state" style={{ height: '100vh', flexDirection: 'column', gap: 8 }}>
          <span>Connection failed: {error}</span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Make sure the backend is running: python main.py
          </span>
        </div>
      </div>
    )
  }

  const { summary, map, agents, events } = state

  return (
    <div className="app-shell">
      <Header summary={summary} />

      <div className="dashboard">
        <WorldMap map={map} />

        <AgentTable agents={agents} />

        <div className="bottom-right">
          <WealthChart agents={agents} />
          <EventFeed events={events} />
        </div>
      </div>
    </div>
  )
}
