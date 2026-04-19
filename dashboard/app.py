from __future__ import annotations

from config import CYCLE_TICKS, DAY_TICKS, DB_PATH, TICK_INTERVAL_SECONDS
from core.ledger import Ledger
from dashboard.agent_view import agent_summary
from dashboard.charts_view import wealth_points
from dashboard.feed_view import format_event
from dashboard.map_view import build_zone_grid

def _phase_label(tick: int) -> str:
    phase_tick = tick % CYCLE_TICKS
    if phase_tick < DAY_TICKS:
        remaining = DAY_TICKS - phase_tick
        return f"DAY  (tax in {remaining} ticks)"
    else:
        remaining = CYCLE_TICKS - phase_tick
        return f"NIGHT  (reset pool in {remaining} ticks)"

def render_dashboard(st) -> None:
    ledger = Ledger(DB_PATH)
    snapshots = ledger.latest_agent_snapshots()
    current_tick = ledger.current_tick()
    current_day = ledger.current_day()

    st.title("Neural Darwin")
    st.caption(
        f"Tick {current_tick} | Day {current_day} | Phase: {_phase_label(current_tick)}"
    )
    st.markdown(
        f"<meta http-equiv='refresh' content='{TICK_INTERVAL_SECONDS}'>",
        unsafe_allow_html=True,
    )

    st.subheader("World Map")
    st.dataframe(build_zone_grid(snapshots), use_container_width=True)

    st.subheader("Agents")
    st.dataframe([agent_summary(agent) for agent in snapshots], use_container_width=True)

    st.subheader("Wealth")
    wealth = wealth_points(snapshots)
    st.bar_chart({name: tokens for name, tokens in wealth})

    st.subheader("Event Feed")
    for row in ledger.recent_events():
        st.text(format_event(row))
