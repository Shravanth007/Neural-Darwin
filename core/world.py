from __future__ import annotations

import random
import threading
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from config import (
    BROADCAST_COST,
    CHAT_PROXIMITY,
    GRID_SIZE,
    VISION_RADIUS,
    ZONE_CELL_COUNTS,
    ZONE_LAYOUT,
)

class ZoneType(str, Enum):
    MARKET    = "MARKET"
    ARENA     = "ARENA"
    SANCTUARY = "SANCTUARY"
    VAULT     = "VAULT"
    WASTELAND = "WASTELAND"

_ZONE_COST_MODIFIERS: dict[ZoneType, float] = {
    ZoneType.MARKET:    0.7,
    ZoneType.ARENA:     1.0,
    ZoneType.SANCTUARY: 1.0,
    ZoneType.VAULT:     1.0,
    ZoneType.WASTELAND: 1.0,
}

@dataclass(frozen=True)
class Position:
    x: int
    y: int

    def as_tuple(self) -> tuple[int, int]:
        return self.x, self.y

def chebyshev_distance(a: Position, b: Position) -> int:

    return max(abs(a.x - b.x), abs(a.y - b.y))

def chebyshev_distance_xy(x1: int, y1: int, x2: int, y2: int) -> int:
    return max(abs(x1 - x2), abs(y1 - y2))

class World:

    def __init__(self, size: int = GRID_SIZE) -> None:
        self.size = size
        self._lock = threading.RLock()
        self._zones: dict[tuple[int, int], ZoneType] = self._build_zones()
        self._agent_positions: dict[str, tuple[int, int]] = {}
        self._cell_agents: dict[tuple[int, int], set[str]] = defaultdict(set)

    def _build_zones(self) -> dict[tuple[int, int], ZoneType]:

        zones: dict[tuple[int, int], ZoneType] = {}
        for zone_name, cells in ZONE_LAYOUT.items():
            zone = ZoneType[zone_name]
            for cell in cells:
                zones[tuple(cell)] = zone
        return zones

    _ZONE_SHAPES: dict[int, tuple[int, int]] = {
        1: (1, 1),
        2: (1, 2),
        3: (1, 3),
        4: (2, 2),
        6: (2, 3),
        8: (2, 4),
        9: (3, 3),
    }

    def randomize_zones(self, rng: random.Random | None = None) -> None:

        roller = rng or random.Random()
        with self._lock:
            new_zones: dict[tuple[int, int], ZoneType] = {}
            used_cells: set[tuple[int, int]] = set()

            for zone_name in ("MARKET", "ARENA", "SANCTUARY", "VAULT"):
                count = ZONE_CELL_COUNTS[zone_name]
                zone_type = ZoneType[zone_name]
                rows, cols = self._ZONE_SHAPES.get(count, (1, count))

                placed = False
                for _ in range(500):

                    x0 = roller.randint(1, self.size - cols - 1)
                    y0 = roller.randint(1, self.size - rows - 1)

                    rect = [
                        (x0 + dx, y0 + dy)
                        for dy in range(rows)
                        for dx in range(cols)
                    ]
                    if any(c in used_cells for c in rect):
                        continue

                    for cell in rect:
                        new_zones[cell] = zone_type
                        used_cells.add(cell)
                    placed = True
                    break

                if not placed:

                    for _ in range(count * 200):
                        cx = roller.randint(1, self.size - 2)
                        cy = roller.randint(1, self.size - 2)
                        if (cx, cy) not in used_cells:
                            new_zones[(cx, cy)] = zone_type
                            used_cells.add((cx, cy))
                            if sum(1 for c in new_zones.values() if c == zone_type) >= count:
                                break

            self._zones = new_zones

    def get_zone_cells(self, zone_type: ZoneType) -> list[tuple[int, int]]:

        with self._lock:
            return [pos for pos, z in self._zones.items() if z == zone_type]

    def in_bounds(self, position: Position) -> bool:
        return 0 <= position.x < self.size and 0 <= position.y < self.size

    def _in_bounds_xy(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def get_zone(self, x_or_pos: "int | Position", y: int | None = None) -> ZoneType:
        with self._lock:
            if isinstance(x_or_pos, Position):
                return self._zones.get(x_or_pos.as_tuple(), ZoneType.WASTELAND)
            if y is None:
                raise TypeError("get_zone(x, y) requires both arguments when x is an int")
            return self._zones.get((x_or_pos, y), ZoneType.WASTELAND)

    def is_market(self, position: Position) -> bool:
        return self.get_zone(position) == ZoneType.MARKET

    def is_sanctuary(self, position: Position) -> bool:
        return self.get_zone(position) == ZoneType.SANCTUARY

    def is_arena(self, position: Position) -> bool:
        return self.get_zone(position) == ZoneType.ARENA

    def is_vault(self, position: Position) -> bool:
        return self.get_zone(position) == ZoneType.VAULT

    def is_combat_allowed(self, x: int, y: int) -> bool:

        return self.get_zone(x, y) not in (ZoneType.SANCTUARY, ZoneType.ARENA)

    def get_zone_cost_modifier(self, x: int, y: int) -> float:

        return _ZONE_COST_MODIFIERS.get(self.get_zone(x, y), 1.0)

    def neighbors(self, position: Position) -> list[Position]:

        deltas = ((1, 0), (-1, 0), (0, 1), (0, -1))
        return [
            Position(position.x + dx, position.y + dy)
            for dx, dy in deltas
            if self._in_bounds_xy(position.x + dx, position.y + dy)
        ]

    def get_neighbors(self, x: int, y: int, radius: int = 2) -> list[tuple[int, int]]:

        return [
            (x + dx, y + dy)
            for dx in range(-radius, radius + 1)
            for dy in range(-radius, radius + 1)
            if (dx != 0 or dy != 0) and self._in_bounds_xy(x + dx, y + dy)
        ]

    def positions_by_zone(self, zone: ZoneType) -> Iterable[Position]:
        with self._lock:
            return [Position(*coords) for coords, mapped_zone in self._zones.items() if mapped_zone == zone]

    def zone_counts(self) -> dict[ZoneType, int]:
        counts = {zone: 0 for zone in ZoneType}
        with self._lock:
            for zone in self._zones.values():
                counts[zone] += 1
        special_total = sum(v for z, v in counts.items() if z is not ZoneType.WASTELAND)
        counts[ZoneType.WASTELAND] = (self.size * self.size) - special_total
        return counts

    def get_visible_entities(self, agent_id: str) -> list[dict[str, Any]]:
        with self._lock:
            pos = self._agent_positions.get(agent_id)
            if pos is None:
                return []

            ax, ay = pos
            visible: list[dict[str, Any]] = []

            for other_id, (ox, oy) in self._agent_positions.items():
                if other_id == agent_id:
                    continue
                dist = chebyshev_distance_xy(ax, ay, ox, oy)
                if dist <= VISION_RADIUS:
                    visible.append({
                        "agent_id": other_id,
                        "x": ox,
                        "y": oy,
                        "distance": dist,
                    })

            return visible

    def send_personal_message(
        self,
        sender,
        receiver,
        text: str,
        tick: int,
    ) -> tuple[bool, str]:

        dist = chebyshev_distance(sender.position, receiver.position)
        if dist > CHAT_PROXIMITY:
            return False, f"too far (distance {dist}, max {CHAT_PROXIMITY})"
        receiver.receive_message(tick, sender.agent_id, "personal", text)
        return True, "sent"

    def send_broadcast_message(
        self,
        sender,
        text: str,
        tick: int,
        all_agents: dict,
    ) -> tuple[bool, str]:

        if not sender.can_afford(BROADCAST_COST):
            return False, "cannot afford broadcast cost"
        sender.debit(BROADCAST_COST)
        for aid, agent in all_agents.items():
            if aid != sender.agent_id and agent.alive:
                agent.receive_message(tick, sender.agent_id, "broadcast", text)
        return True, "broadcast sent"

    def register_agent(self, agent_id: str, x: int, y: int) -> None:

        with self._lock:
            old = self._agent_positions.get(agent_id)
            if old is not None:
                self._cell_agents[old].discard(agent_id)
            self._agent_positions[agent_id] = (x, y)
            self._cell_agents[(x, y)].add(agent_id)

    def deregister_agent(self, agent_id: str) -> None:

        with self._lock:
            pos = self._agent_positions.pop(agent_id, None)
            if pos is not None:
                self._cell_agents[pos].discard(agent_id)

    def sync_agents_from_db(self, ledger: Any) -> None:

        for row in ledger.latest_agent_snapshots():
            if row["alive"]:
                self.register_agent(row["agent_id"], row["x"], row["y"])

    def get_agents_at(self, x: int, y: int) -> list[str]:
        with self._lock:
            return list(self._cell_agents.get((x, y), set()))

    def get_agent_position(self, agent_id: str) -> tuple[int, int] | None:
        with self._lock:
            return self._agent_positions.get(agent_id)

    def move_agent(self, agent_id: str, new_x: int, new_y: int) -> bool:
        with self._lock:
            if not self._in_bounds_xy(new_x, new_y):
                return False
            self.register_agent(agent_id, new_x, new_y)
            return True

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            zones_out = {
                f"{x},{y}": zone.value
                for (x, y), zone in self._zones.items()
            }
            agents_out = {
                aid: {"x": x, "y": y}
                for aid, (x, y) in self._agent_positions.items()
            }
            cells = [
                [
                    {
                        "x":      col_x,
                        "y":      row_y,
                        "zone":   self.get_zone(col_x, row_y).value,
                        "agents": self.get_agents_at(col_x, row_y),
                    }
                    for col_x in range(self.size)
                ]
                for row_y in range(self.size)
            ]
            return {"size": self.size, "zones": zones_out, "agents": agents_out, "cells": cells}
