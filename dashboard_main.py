from __future__ import annotations

from dashboard.app import render_dashboard

def main() -> None:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Streamlit is required to run the dashboard. Install it with `pip install streamlit`."
        ) from exc

    render_dashboard(st)

if __name__ == "__main__":
    main()
