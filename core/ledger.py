from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from config import DATA_DIR, DB_PATH, CYCLE_TICKS

class Ledger:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:

        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT,
                    target TEXT,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS agent_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER NOT NULL,
                    agent_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    tokens INTEGER NOT NULL,
                    combat INTEGER NOT NULL,
                    alive INTEGER NOT NULL,
                    kills INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS graveyard (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL UNIQUE,
                    death_tick INTEGER NOT NULL,
                    cause TEXT NOT NULL,
                    killer TEXT,
                    final_tokens INTEGER NOT NULL,
                    final_kills INTEGER NOT NULL,
                    final_x INTEGER NOT NULL,
                    final_y INTEGER NOT NULL,
                    inventory TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS weapon_purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER NOT NULL,
                    agent_id TEXT NOT NULL,
                    weapon TEXT NOT NULL,
                    cost INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS arena_bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER NOT NULL,
                    challenger TEXT NOT NULL,
                    defender TEXT NOT NULL,
                    bet_amount INTEGER NOT NULL,
                    total_pool INTEGER NOT NULL,
                    winner TEXT,
                    payout INTEGER,
                    tax_burned INTEGER,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def append_event(
        self,
        tick: int,
        event_type: str,
        actor: str | None,
        target: str | None,
        details: dict[str, Any],
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO events (tick, event_type, actor, target, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tick, event_type, actor, target, json.dumps(details, sort_keys=True)),
            )

    def snapshot_agent(self, tick: int, agent: Any) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_snapshots
                (tick, agent_id, role, x, y, tokens, combat, alive, kills)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tick,
                    agent.agent_id,
                    "AGENT",
                    agent.position.x,
                    agent.position.y,
                    agent.tokens,
                    0,
                    int(agent.alive),
                    agent.kills,
                ),
            )

    def move_to_graveyard(
        self,
        agent: Any,
        death_tick: int,
        cause: str,
        killer: str | None = None,
    ) -> None:

        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO graveyard
                (agent_id, death_tick, cause, killer, final_tokens, final_kills,
                 final_x, final_y, inventory)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent.agent_id,
                    death_tick,
                    cause,
                    killer,
                    agent.tokens,
                    agent.kills,
                    agent.position.x,
                    agent.position.y,
                    json.dumps(getattr(agent, "inventory", [])),
                ),
            )

    def get_graveyard(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM graveyard ORDER BY death_tick DESC")
            return list(cursor.fetchall())

    def log_weapon_purchase(self, tick: int, agent_id: str, weapon: str, cost: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO weapon_purchases (tick, agent_id, weapon, cost) VALUES (?, ?, ?, ?)",
                (tick, agent_id, weapon, cost),
            )

    def log_arena_bet(
        self,
        tick: int,
        challenger: str,
        defender: str,
        bet_amount: int,
        total_pool: int,
    ) -> int:

        with self.connect() as conn:
            cursor = conn.execute(
                """INSERT INTO arena_bets
                   (tick, challenger, defender, bet_amount, total_pool, status)
                   VALUES (?, ?, ?, ?, ?, 'active')""",
                (tick, challenger, defender, bet_amount, total_pool),
            )
            return cursor.lastrowid

    def update_arena_bet(
        self,
        challenger: str,
        defender: str,
        winner: str | None,
        payout: int,
        tax_burned: int,
    ) -> None:

        with self.connect() as conn:
            conn.execute(
                """UPDATE arena_bets
                   SET winner = ?, payout = ?, tax_burned = ?, status = 'finished'
                   WHERE challenger = ? AND defender = ? AND status = 'active'""",
                (winner, payout, tax_burned, challenger, defender),
            )

    def broadcast_death(
        self,
        dead_agent_id: str,
        tick: int,
        all_agents: dict[str, Any],
        bounty_info: str = "",
    ) -> None:

        text = f"Agent {dead_agent_id} has been terminated."
        if bounty_info:
            text += f" {bounty_info}"

        self.append_event(tick, "system_announcement", None, dead_agent_id, {"text": text})

        for aid, agent in all_agents.items():
            if agent.alive and aid != dead_agent_id:
                agent.receive_message(tick, "SYSTEM", "system", text)

    def recent_events(self, limit: int = 50) -> list[sqlite3.Row]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return list(cursor.fetchall())

    def latest_agent_snapshots(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT s.*
                FROM agent_snapshots AS s
                INNER JOIN (
                    SELECT agent_id, MAX(id) AS latest_id
                    FROM agent_snapshots
                    GROUP BY agent_id
                ) AS latest
                    ON latest.latest_id = s.id
                ORDER BY s.agent_id
                """
            )
            return list(cursor.fetchall())

    def current_tick(self) -> int:
        with self.connect() as conn:
            cursor = conn.execute("SELECT COALESCE(MAX(tick), 0) FROM agent_snapshots")
            value = cursor.fetchone()
            return int(value[0] if value is not None else 0)

    def current_day(self) -> int:
        return self.current_tick() // CYCLE_TICKS
