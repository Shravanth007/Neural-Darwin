const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  health:    () => get('/health'),
  summary:   () => get('/state/summary'),
  map:       () => get('/state/map'),
  agents:    () => get('/agents'),
  agent:     (id) => get(`/agents/${id}`),
  events:    (limit = 50) => get(`/events?limit=${limit}`),
  graveyard: () => get('/graveyard'),
  bounties:  () => get('/bounties'),
}
