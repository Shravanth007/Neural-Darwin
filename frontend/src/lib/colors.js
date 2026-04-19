export const ZONE_COLORS = {
  MARKET:    { fill: '#dbeafe', border: '#2563eb', label: 'Market' },
  ARENA:     { fill: '#fee2e2', border: '#dc2626', label: 'Arena' },
  SANCTUARY: { fill: '#d1fae5', border: '#059669', label: 'Sanctuary' },
  VAULT:     { fill: '#f3e8ff', border: '#7c3aed', label: 'Vault' },
  WASTELAND: { fill: '#f9fafb', border: null,      label: 'Wasteland' },
}

const AGENT_PALETTE = [
  '#e11d48',
  '#2563eb',
  '#059669',
  '#d97706',
  '#7c3aed',
  '#0d9488',
  '#c026d3',
  '#ea580c',
  '#0284c7',
  '#65a30d',
]

function hashStr(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

export function agentColor(agentId) {
  return AGENT_PALETTE[hashStr(agentId) % AGENT_PALETTE.length]
}

export function zoneFill(zoneType) {
  return ZONE_COLORS[zoneType]?.fill || ZONE_COLORS.WASTELAND.fill
}

export function zoneBorder(zoneType) {
  return ZONE_COLORS[zoneType]?.border || null
}
