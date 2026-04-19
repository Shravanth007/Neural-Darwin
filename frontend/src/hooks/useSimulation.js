import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../lib/api'

export function useSimulation(interval = 3000) {
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const timerRef = useRef(null)

  const fetchAll = useCallback(async () => {
    try {
      const [summary, map, agents, events] = await Promise.all([
        api.summary(),
        api.map(),
        api.agents(),
        api.events(80),
      ])
      setState({ summary, map, agents, events })
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    timerRef.current = setInterval(fetchAll, interval)
    return () => clearInterval(timerRef.current)
  }, [fetchAll, interval])

  return { state, loading, error }
}
