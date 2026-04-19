const TYPE_CLASSES = new Set([
  'spawn', 'death', 'murder', 'bounty_kill',
  'daily_tax', 'daily_reset_pool', 'phase_change', 'heir_spawn',
])

function typeClass(eventType) {
  return TYPE_CLASSES.has(eventType) ? eventType : 'default'
}

function eventSummary(ev) {
  const parts = []
  if (ev.actor) parts.push(ev.actor)
  if (ev.target) parts.push('→ ' + ev.target)

  const d = ev.details || {}
  if (d.loot) parts.push(`loot: ${d.loot}`)
  if (d.delta) parts.push(`${d.delta > 0 ? '+' : ''}${d.delta}`)
  if (d.phase) parts.push(d.phase)
  if (d.reason) parts.push(d.reason)
  if (d.weapon) parts.push(d.weapon)
  if (d.bet) parts.push(`bet: ${d.bet}`)
  if (d.payout) parts.push(`payout: ${d.payout}`)

  return parts.join(' · ') || '—'
}

export default function EventFeed({ events }) {
  if (!events || events.length === 0) {
    return (
      <div className="panel">
        <div className="panel-header"><span className="panel-title">Event Feed</span></div>
        <div className="loading-state">No events yet</div>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Event Feed</span>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {events.length} events
        </span>
      </div>
      <div className="panel-body">
        <ul className="event-list">
          {events.map(ev => (
            <li key={ev.id} className="event-row">
              <span className="event-tick">t{ev.tick}</span>
              <span className={`event-type ${typeClass(ev.event_type)}`}>
                {ev.event_type.replace(/_/g, ' ')}
              </span>
              <span className="event-text">{eventSummary(ev)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
