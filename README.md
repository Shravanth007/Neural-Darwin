# Neural Darwin

Neural Darwin is a real-time multi-agent survival simulation with a token economy.

The current codebase runs a simulation loop in Python, exposes state through FastAPI, and visualizes the world in a React dashboard.

## What This Project Covers

- Tick-based world simulation on a 50x50 grid
- Economy loop with income, expenses, and elimination
- Combat systems (knife kills, bounty hunting, arena duels)
- Persistent event and snapshot logging in SQLite
- Live frontend map, agent table, wealth chart, and event feed

## Quick Start

## 1) Backend

From the project root:

```powershell
python -m pip install fastapi "uvicorn[standard]" streamlit
python main.py
```

Backend health endpoint:

- http://localhost:8000/api/health

## 2) Frontend

In a new terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

- http://localhost:5173

## API Keys

This repository includes an LLM integration stub for future add-ons.

If you want to enable future LLM-backed behavior, paste your key into .env:

```env
GROQ_API_KEY=your_real_api_key
```

You can also set it in the current PowerShell session:

```powershell
$env:GROQ_API_KEY="your_key_here"
```

Tracked template and ignored local file:

- .env.example is committed with placeholders
- .env is ignored by git

Current status:

- Core simulation works without API keys
- LLM usage is optional and intended for later expansion

## Economy Overview

### Time and cycle

- 1 tick = 5 seconds
- Day = 120 ticks
- Night = 120 ticks
- Full cycle = 240 ticks

### Starting state

- Default agents: 6
- Starting balance per agent: 20,000 tokens

### Core expenses

- Daily tax: 800 tokens (end of day)
- Move action: 10 tokens
- Trade action: 50 tokens (discount in market zone via multiplier 0.7)
- Broadcast message: 50 tokens
- Knife purchase: 6,000 tokens
- Murder attempt cost: 500 tokens (paid even on failure)
- Arena minimum bet: 1,000 tokens
- Sanctuary rent: charged per tick while in sanctuary

### Core income

- Night reset pool: 8,000 tokens total, split among survivors
- Murder loot: 40% of target tokens
- Bounty collection: reward based on bounty board posting
- Arena winner payout: 85% of duel pool

### Elimination and population pressure

- Agents can die in combat or from economy pressure (token threshold)
- If living population drops below minimum, heir agents are spawned

## Zones and Their Effect

- MARKET: discounted trade cost, knife purchase point
- ARENA: formal duel zone
- SANCTUARY: safe zone with rent drain
- VAULT: reserved for future mechanics
- WASTELAND: default world behavior

Special zone coordinates are randomized at day-cycle boundaries.

## API Endpoints (Read-Only)

- GET /api/health
- GET /api/state/summary
- GET /api/state/map
- GET /api/agents
- GET /api/agents/{agent_id}
- GET /api/events
- GET /api/graveyard
- GET /api/bounties



