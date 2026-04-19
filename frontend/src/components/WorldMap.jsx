import { useRef, useEffect, useState, useCallback } from 'react'
import { zoneFill, zoneBorder, agentColor } from '../lib/colors'
import MapLegend from './MapLegend'

export default function WorldMap({ map }) {
  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [tooltip, setTooltip] = useState(null)
  const sizeRef = useRef({ w: 0, h: 0 })
  const rafRef = useRef(null)
  const dragRef = useRef({ dragging: false, startX: 0, startY: 0, origOx: 0, origOy: 0 })

  const gridSize = map?.size || 50

  const scheduleDraw = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = requestAnimationFrame(() => {
      const canvas = canvasRef.current
      const container = containerRef.current
      if (!canvas || !container || !map) return

      const w = container.clientWidth
      const h = container.clientHeight
      if (w < 10 || h < 10) return

      sizeRef.current = { w, h }

      const dpr = window.devicePixelRatio || 1
      canvas.width = Math.round(w * dpr)
      canvas.height = Math.round(h * dpr)

      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      const cellSize = (Math.min(w, h) / gridSize) * zoom
      const gridPx = cellSize * gridSize
      const ox = (w - gridPx) / 2 + offset.x
      const oy = (h - gridPx) / 2 + offset.y

      ctx.fillStyle = '#f5f6f8'
      ctx.fillRect(0, 0, w, h)

      const zoneMap = map.zones || {}

      for (let gy = 0; gy < gridSize; gy++) {
        for (let gx = 0; gx < gridSize; gx++) {
          const px = ox + gx * cellSize
          const py = oy + gy * cellSize
          if (px + cellSize < 0 || py + cellSize < 0 || px > w || py > h) continue

          const key = `${gx},${gy}`
          const zone = zoneMap[key] || 'WASTELAND'

          ctx.fillStyle = zoneFill(zone)
          ctx.fillRect(px, py, cellSize, cellSize)

          ctx.strokeStyle = '#e2e5ea'
          ctx.lineWidth = 0.5
          ctx.strokeRect(px + 0.25, py + 0.25, cellSize - 0.5, cellSize - 0.5)

          const bdr = zoneBorder(zone)
          if (bdr) {
            ctx.strokeStyle = bdr
            ctx.lineWidth = Math.max(2, cellSize * 0.12)
            ctx.strokeRect(px + 1.5, py + 1.5, cellSize - 3, cellSize - 3)
          }
        }
      }

      const agents = map.agents || []
      const r = Math.max(3.5, cellSize * 0.32)
      for (const a of agents) {
        const cx = ox + a.x * cellSize + cellSize / 2
        const cy = oy + a.y * cellSize + cellSize / 2
        if (cx + r < 0 || cy + r < 0 || cx - r > w || cy - r > h) continue

        const color = agentColor(a.agent_id)

        ctx.beginPath()
        ctx.arc(cx, cy, r + 2, 0, Math.PI * 2)
        ctx.fillStyle = color + '25'
        ctx.fill()

        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.fillStyle = color
        ctx.fill()
        ctx.strokeStyle = '#ffffff'
        ctx.lineWidth = Math.max(1, cellSize * 0.06)
        ctx.stroke()

        if (cellSize > 20) {
          ctx.fillStyle = '#1a1d24'
          ctx.font = `700 ${Math.max(8, cellSize * 0.2)}px Inter,sans-serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'top'
          ctx.fillText(a.agent_id.replace('Agent_', 'A').replace('Heir_', 'H'), cx, cy + r + 2)
        }
      }
    })
  }, [map, zoom, offset, gridSize])

  useEffect(() => { scheduleDraw() }, [scheduleDraw])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(() => scheduleDraw())
    ro.observe(el)
    return () => ro.disconnect()
  }, [scheduleDraw])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const fn = (e) => {
      e.preventDefault()
      setZoom(z => Math.max(0.5, Math.min(8, z * (e.deltaY < 0 ? 1.15 : 0.87))))
    }
    el.addEventListener('wheel', fn, { passive: false })
    return () => el.removeEventListener('wheel', fn)
  }, [])

  const onDown = useCallback(e => {
    dragRef.current = { dragging: true, startX: e.clientX, startY: e.clientY, origOx: offset.x, origOy: offset.y }
  }, [offset])

  const onMove = useCallback(e => {
    const d = dragRef.current
    if (d.dragging) {
      setOffset({ x: d.origOx + (e.clientX - d.startX), y: d.origOy + (e.clientY - d.startY) })
      return
    }

    const el = containerRef.current
    if (!el || !map) return
    const { w, h } = sizeRef.current
    if (w < 10) return
    const cellSize = (Math.min(w, h) / gridSize) * zoom
    const gridPx = cellSize * gridSize
    const mox = (w - gridPx) / 2 + offset.x
    const moy = (h - gridPx) / 2 + offset.y
    const rect = el.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const gx = Math.floor((mx - mox) / cellSize)
    const gy = Math.floor((my - moy) / cellSize)
    if (gx >= 0 && gx < gridSize && gy >= 0 && gy < gridSize) {
      const key = `${gx},${gy}`
      const zone = map.zones?.[key] || 'WASTELAND'
      const ags = map.agents?.filter(a => a.x === gx && a.y === gy) || []
      setTooltip({ x: mx, y: my, text: [`(${gx},${gy}) ${zone}`, ...ags.map(a => a.agent_id)].join(' · ') })
    } else setTooltip(null)
  }, [map, zoom, offset, gridSize])

  const onUp = useCallback(() => { dragRef.current.dragging = false }, [])
  const onLeave = useCallback(() => { dragRef.current.dragging = false; setTooltip(null) }, [])

  return (
    <div className="panel map-section">
      <div className="panel-header">
        <span className="panel-title">World Map</span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {gridSize}×{gridSize} · {zoom.toFixed(1)}×
        </span>
      </div>
      <div className="map-container" ref={containerRef}
        onMouseDown={onDown} onMouseMove={onMove} onMouseUp={onUp} onMouseLeave={onLeave}>
        <canvas ref={canvasRef} style={{ position: 'absolute', top: 0, left: 0, display: 'block' }} />
        <div className="map-controls">
          <button className="map-btn" onClick={() => setZoom(z => Math.min(8, z * 1.3))}>+</button>
          <button className="map-btn" onClick={() => setZoom(z => Math.max(0.5, z * 0.7))}>−</button>
          <button className="map-btn" onClick={() => { setZoom(1); setOffset({x:0,y:0}) }}>⌂</button>
        </div>
        {tooltip && <div className="map-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>{tooltip.text}</div>}
      </div>
      <MapLegend />
    </div>
  )
}
