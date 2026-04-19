import { ZONE_COLORS } from '../lib/colors'

const LEGEND_ITEMS = [
  { key: 'MARKET',    ...ZONE_COLORS.MARKET },
  { key: 'ARENA',     ...ZONE_COLORS.ARENA },
  { key: 'SANCTUARY', ...ZONE_COLORS.SANCTUARY },
  { key: 'VAULT',     ...ZONE_COLORS.VAULT },
]

export default function MapLegend() {
  return (
    <div className="map-legend">
      {LEGEND_ITEMS.map(z => (
        <div key={z.key} className="legend-item">
          <span className="legend-swatch" style={{ background: z.border }} />
          {z.label}
        </div>
      ))}
      <div className="legend-item" style={{ marginLeft: 'auto', fontWeight: 400, color: 'var(--text-muted)' }}>
        Zones re-randomize each dawn
      </div>
    </div>
  )
}
