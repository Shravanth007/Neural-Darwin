from __future__ import annotations

from config import GRID_SIZE

def build_zone_grid(agents, zone_map: dict[str, str] | None = None) -> list[list[str]]:

    zones: dict[tuple[int, int], str] = {}
    if zone_map:
        for key, zname in zone_map.items():
            x_str, y_str = key.split(",")
            zones[(int(x_str), int(y_str))] = zname[:3]

    by_position: dict[tuple[int, int], str] = {}
    for agent in agents:
        if agent["alive"]:
            by_position[(agent["x"], agent["y"])] = agent["agent_id"]

    grid = []
    for y in range(GRID_SIZE):
        row = []
        for x in range(GRID_SIZE):
            agent_name = by_position.get((x, y))
            if agent_name:
                row.append(agent_name[:3].upper())
            else:
                row.append(zones.get((x, y), " . "))
        grid.append(row)
    return grid
