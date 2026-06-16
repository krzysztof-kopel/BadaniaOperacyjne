uv sync
set PYTHONPATH=set PYTHONPATH=%PYTHONPATH%;%~dp0
uv run streamlit run src/app.py
