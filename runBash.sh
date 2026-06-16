#!/bin/bash
uv sync
PYTHONPATH=. uv run streamlit run src/app.py
