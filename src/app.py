"""
Run with:
    uv run streamlit run src/app.py

    it's possible you need to set PYTHONPATH to root project directory
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import altair as alt

from src.benchmark import run_benchmark


# --------------------------------------------------------------------------- #
# Page config
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="Badania Operacyjne - optymalizacja planu zajęć",
    layout="wide",
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _default_spec() -> dict:
    return {
        "teacher_num": 4,
        "subjects_num": 4,
        "classrooms_num": 3,
        "time_slots_num": 4,
        "lambda1": -1,
        "default_classrooms": True,
        "pensum_list": [3, 3, 3, 3],
        "subject_hours": [3, 3, 3, 3],
        "teacher_subject": [[t, s] for t in range(4) for s in range(4)],
        "subject_classroom": [],
    }


def _big_spec() -> dict:
    return {
        "teacher_num": 8,
        "subjects_num": 10,
        "classrooms_num": 4,
        "time_slots_num": 6,
        "lambda1": -1,
        "default_classrooms": True,
        "pensum_list": [10] * 8,
        "subject_hours": [4, 4, 3, 3, 2, 2, 2, 3, 4, 3],
        "teacher_subject": [
            (0, 0), (0, 1), (0, 2),
            (1, 0), (1, 3), (1, 4),
            (2, 1), (2, 3), (2, 5),
            (3, 2), (3, 4), (3, 6),
            (4, 5), (4, 6), (4, 7),
            (5, 7), (5, 8), (5, 9),
            (6, 0), (6, 8), (6, 9),
            (7, 1), (7, 2), (7, 8),
        ],
        "subject_classroom": [],
    }


PRESETS = {
    "Mały (domyślny)": _default_spec,
    "Duży": _big_spec,
}

def _spec_to_pills(spec: dict) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nauczyciele", spec["teacher_num"])
    c2.metric("Przedmioty", spec["subjects_num"])
    c3.metric("Sale", spec["classrooms_num"])
    c4.metric("Sloty czasowe", spec["time_slots_num"])

    c1, c2, c3 = st.columns(3)
    c1.metric("λ₁", spec.get("lambda1", -1))
    c2.metric("Łączna liczba godzin",
              sum(spec.get("subject_hours") or [1] * spec["subjects_num"]))
    c3.metric("Suma pensum",
              sum(spec.get("pensum_list") or [6] * spec["teacher_num"]))

# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #

if "spec" not in st.session_state:
    st.session_state.spec = _default_spec()
if "results" not in st.session_state:
    st.session_state.results = []


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #

with st.sidebar:
    st.header("Rozmiar problemu")
    preset = st.selectbox("Preset", list(PRESETS.keys()))
    if st.button("Wczytaj", use_container_width=True):
        st.session_state.spec = PRESETS[preset]()
        st.success(f"Loaded preset: {preset}")

    st.divider()
    seed_val = st.number_input(
        "Globalna wartość seeda (0 - losowy)",
        min_value=0, value=0, step=1,
        key="global_seed",
    )
    global_seed = int(seed_val) if seed_val else None
    st.divider()


# --------------------------------------------------------------------------- #
# Title
# --------------------------------------------------------------------------- #

st.title("Badania Operacyjne - optymalizacja planu zajęć")
# st.caption("")


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #

tab_input, tab_run, tab_compare, tab_schedule = st.tabs(
    ["Dane wejściowe", "Uruchom solver", "Porównanie solverów", "Najlepszy plan"]
)


# --------------------------------------------------------------------------- #
# Input tab
# --------------------------------------------------------------------------- #

with tab_input:
    spec = st.session_state.spec

    st.subheader("Definicja problemu")
    c1, c2, c3, c4 = st.columns(4)
    spec["teacher_num"] = c1.number_input("Liczba nauczycieli", 1, 50, int(spec["teacher_num"]))
    spec["subjects_num"] = c2.number_input("Liczba przedmiotów", 1, 50, int(spec["subjects_num"]))
    spec["classrooms_num"] = c3.number_input("Liczba sal", 1, 50, int(spec["classrooms_num"]))
    spec["time_slots_num"] = c4.number_input("Liczba slotów czasowych w dniu", 1, 12, int(spec["time_slots_num"]))
    spec["lambda1"] = c1.number_input("λ₁", -100, 100, int(spec.get("lambda1", -1)))
    spec["default_classrooms"] = c2.checkbox(
        "Wszystkie przedmioty mogą być nauczane w wszystkich salach",
        value=bool(spec.get("default_classrooms", True)),
    )

    st.divider()
    st.subheader("Pensum nauczycieli (godziny w tygodniu)")
    pensum_txt = st.text_area(
        "Wpisz wartość dla każdego nauczyciela oddzielone przecinkami",
        value=", ".join(str(x) for x in spec.get("pensum_list", [6] * spec["teacher_num"])),
        height=80,
    )
    try:
        spec["pensum_list"] = [int(x.strip()) for x in pensum_txt.split(",") if x.strip()]
    except ValueError:
        st.error("Nieprawidłowe dane. Upewnij się, że wartości są numeryczne")

    st.subheader("Godziny na przedmiot (tygodniowo)")
    hours_txt = st.text_area(
        "Wpisz wartość dla każdego przedmiotu, oddzielone przecinkami",
        value=", ".join(str(x) for x in spec.get("subject_hours", [1] * spec["subjects_num"])),
        height=80,
    )
    try:
        spec["subject_hours"] = [int(x.strip()) for x in hours_txt.split(",") if x.strip()]
    except ValueError:
        st.error("Subject hours must be integers separated by commas.")

    st.subheader("Pary nauczyciel-przedmiot (jedna na linię, format: `t,s`)")
    ts_txt = st.text_area(
        "Każda para oznacza że nauczyciel `t` może nauczać przedmiotu `s`",
        value="\n".join(f"{t},{s}" for t, s in spec.get("teacher_subject", [])),
        height=120,
    )
    pairs_ts: list[list[int]] = []
    for line in ts_txt.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            t, s = [int(x.strip()) for x in line.split(",")]
            pairs_ts.append([t, s])
        except ValueError:
            st.error(f"Could not parse pair: {line!r}")
    spec["teacher_subject"] = pairs_ts

    st.subheader("Pary przedmiot-sala (jedna na linię, format: `s,c`)")
    sc_txt = st.text_area(
        "Każda para oznacza że przedmiot `s` musi być nauczany w sali `c`",
        value="\n".join(f"{s},{c}" for s, c in spec.get("subject_classroom", [])),
        height=120,
    )
    pairs_sc: list[list[int]] = []
    for line in sc_txt.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            s, c = [int(x.strip()) for x in line.split(",")]
            pairs_sc.append([s, c])
        except ValueError:
            st.error(f"Could not parse pair: {line!r}")
    spec["subject_classroom"] = pairs_sc

    st.divider()
    _spec_to_pills(spec)


# --------------------------------------------------------------------------- #
# Run tab — run a single solver
# --------------------------------------------------------------------------- #

with tab_run:
    st.subheader("Uruchom wybrany solver")
    solver = st.selectbox("Solver", ["antcolony", "genetic", "lp"], format_func=lambda x: {
        "antcolony": "Kolonia mrówek",
        "genetic": "Algorytm genetyczny",
        "lp": "Programowanie liniowe",
    }[x])

    st.markdown("**Parametry algorytmu**")
    if solver == "antcolony":
        a1, a2, a3 = st.columns(3)
        ant_count = a1.slider("Liczba mrówek", 5, 200, 30)
        iterations = a2.slider("Iteracje", 5, 500, 80)
        alpha = a3.slider("α (pheromone weight)", 0.1, 5.0, 1.0)
        b1, b2, b3, b4 = st.columns(4)
        beta = b1.slider("β (heuristic weight)", 0.1, 5.0, 2.0)
        rho = b2.slider("ρ (evaporation)", 0.0, 1.0, 0.5)
        q = b3.slider("q (deposit)", 0.1, 5.0, 1.0)
        tau0 = b4.slider("τ₀ (initial)", 0.01, 5.0, 1.0)
        
        params = dict(ant_count=ant_count, iterations=iterations,
                      alpha=alpha, beta=beta, rho=rho, q=q, tau0=tau0,
                      seed=int(global_seed) if global_seed else None)
    elif solver == "genetic":
        g1, g2, g3 = st.columns(3)
        generations = g1.slider("Liczba pokoleń", 1, 200, 20)
        children_num = g2.slider("Dzieci na pokolenie", 1, 100, 10)
        accept_worse = g3.checkbox("Akceptuj gorsze rozwiązania", value=True)
        params = dict(generations=generations, children_num=children_num,
                      accept_worse=accept_worse)
    else:  # lp
        time_limit = st.number_input("Limit czasu (sekundy, brak limitu dla wartości 0)",
                                     value=0, step=1)
        params = dict(time_limit=int(time_limit) if time_limit else None)

    if st.button(f"Uruchom {solver}", type="primary"):
        with st.spinner(f"Uruchamiam solver {solver}…"):
            try:
                results = run_benchmark(st.session_state.spec,
                                        [{"name": solver, "params": params,
                                          "label": solver}])
                st.session_state.results = results
            except Exception as e:
                st.error(f"Run failed: {e}")
            else:
                r = results[0]
                if r.cost is None:
                    st.error(f"No feasible solution found. runtime={r.runtime_sec:.2f}s")
                else:
                    st.success(
                        f"Wartość funkcji kosztu: {r.cost:.2f}," + 
                        f" czas działania: {r.runtime_sec:.2f}s,"
                        f" Czy rozwiązanie jest poprawne: {r.valid}"
                    )

                if r.cost_curve:
                    df = pd.DataFrame({"iteration": range(1, len(r.cost_curve) + 1),
                                       "best cost": r.cost_curve})
                    chart = alt.Chart(df).mark_line(point=True).encode(
                        x=alt.X("iteration:Q", title="Iteration"),
                        y=alt.Y("best cost:Q",
                                title="Best cost",
                                scale=alt.Scale(zero=False),
                                axis=alt.Axis(tickCount=8)),
                        tooltip=["iteration", "best cost"],
                    ).properties(height=300, title="Genetic algorithm")
                    st.altair_chart(chart, use_container_width=True)


# --------------------------------------------------------------------------- #
# Compare tab
# --------------------------------------------------------------------------- #

with tab_compare:
    st.subheader("Porównanie wszystkich solverów")

    with st.expander("Kolonia mrówek", expanded=True):
        a1, a2, a3 = st.columns(3)
        ac_ant = a1.slider("Liczba mrówek", 5, 200, 30, key="cmp_ac_ant")
        ac_iter = a2.slider("Liczba iteracji", 5, 500, 80, key="cmp_ac_iter")
        ac_alpha = a3.slider("α", 0.1, 5.0, 1.0, key="cmp_ac_alpha")
        b1, b2, b3, b4 = st.columns(4)
        ac_beta = b1.slider("β", 0.1, 5.0, 2.0, key="cmp_ac_beta")
        ac_rho = b2.slider("ρ", 0.0, 1.0, 0.5, key="cmp_ac_rho")
        ac_q = b3.slider("q", 0.1, 5.0, 1.0, key="cmp_ac_q")
        ac_tau0 = b4.slider("τ₀", 0.01, 5.0, 1.0, key="cmp_ac_tau0")

    with st.expander("Algorytm genetyczny", expanded=True):
        g1, g2, g3 = st.columns(3)
        ga_gen = g1.slider("Liczba pokoleń", 1, 200, 20, key="cmp_ga_gen")
        ga_kids = g2.slider("Dzieci na pokolenie", 1, 100, 10, key="cmp_ga_kids")
        ga_worse = g3.checkbox("Akceptuj gorsze rozwiązania", value=True, key="cmp_ga_worse")

    with st.expander("Algorytm LP", expanded=True):
        lp_tl = st.number_input("Limit czasu (s, 0 - brak limitu)", value=0,
                                step=1, key="cmp_lp_tl")

    if st.button("Uruchom", type="primary"):
        configs = [
            {"name": "antcolony", "label": "Kolonia mrówek",
             "params": dict(ant_count=ac_ant, iterations=ac_iter, alpha=ac_alpha,
                            beta=ac_beta, rho=ac_rho, q=ac_q, tau0=ac_tau0, seed=global_seed)},
            {"name": "genetic", "label": "Genetyczny",
             "params": dict(generations=ga_gen, children_num=ga_kids,
                            accept_worse=ga_worse)},
            {"name": "lp", "label": "LP",
             "params": dict(time_limit=int(lp_tl) if lp_tl else None)},
        ]
        with st.spinner("Uruchamiam…"):
            try:
                results = run_benchmark(st.session_state.spec, configs)
            except Exception as e:
                st.error(f"Benchmark failed: {e}")
                results = []
            st.session_state.results = results

    # Render previous results (if any)
    if st.session_state.results:
        results = st.session_state.results
        df = pd.DataFrame([
            {
                "Solver": r.name,
                "Koszt": r.cost if r.cost is not None else float("nan"),
                "Czas działania (s)": round(r.runtime_sec, 3),
                "Poprawne": r.valid,
            }
            for r in results
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Bar charts
        bar_cost = (
            alt.Chart(df.dropna(subset=["Koszt"]))
            .mark_bar()
            .encode(x="Solver:N", y=alt.Y("Koszt:Q", title="Koszt",
                    scale=alt.Scale(zero=False),
                    axis=alt.Axis(tickCount=6)),
                    color="Solver:N",
                    tooltip=["Solver", "Koszt", "Czas działania (s)"])
            .properties(title="Najlepsze wartości", height=280)
        )
        bar_time = (
            alt.Chart(df)
            .mark_bar()
            .encode(x="Solver:N", y=alt.Y("Czas działania (s):Q", title="Czas działania (s)", scale=alt.Scale(zero=True, padding=10)),
                    color="Solver:N",
                    tooltip=["Solver", "Koszt", "Czas działania (s)"])
            .properties(title="Czasy działania", height=285)
        )
        c1, c2 = st.columns(2)
        c1.altair_chart(bar_cost, use_container_width=True)
        c2.altair_chart(bar_time, use_container_width=True)

        # Combined cost curve for the iterative ones
        curves = []
        for r in results:
            for i, c in enumerate(r.cost_curve, start=1):
                curves.append({"Solver": r.name, "Iteracja": i, "Najlepszy koszt": c})
        if curves:
            df_c = pd.DataFrame(curves)
            line = (
                alt.Chart(df_c)
                .mark_line(point=True)
                .encode(
                    x=alt.X("Iteracja:Q", title="Iteracja"),
                    y=alt.Y("Najlepszy koszt:Q",
                            title="Najlepszy koszt",
                            scale=alt.Scale(zero=False),
                            axis=alt.Axis(tickCount=8)),
                    color="Solver:N",
                    tooltip=["Solver", "Iteracja", "Najlepszy koszt"],
                )
                .properties(title="Wykres zbieżności (dla algorytmów iteracyjnych)", height=320)
            )
            st.altair_chart(line, use_container_width=True)


# --------------------------------------------------------------------------- #
# Best schedule tab
# --------------------------------------------------------------------------- #

with tab_schedule:
    st.subheader("Najlepszy plan od ostatniego uruchomienia")
    if not st.session_state.results:
        st.info("Najpierw uruchom solver (lub porównanie solverów)")
    else:
        best = min(
            (r for r in st.session_state.results if r.cost is not None),
            key=lambda r: r.cost,  # type: ignore[arg-type]
            default=None,
        )
        if best is None:
            st.warning("Nie znaleziono żadnego poprawnego planu wśród rozwiązań.")
        else:
            st.success(
                f"Najlepszy algorytm: **{best.name}**, najlepszy koszt: **{best.cost:.2f}** "
                f"(czas działania {best.runtime_sec:.2f}s)"
            )
            sol = best.extra.get("solution")
            if sol is None:
                # We didn't store the solution in the dispatcher. Recompute
                # the cheapest one here, against the current spec.
                st.caption("Uruchamiam ponownie solver w celu pokazania planu…")
                from src.benchmark import build_problem, run_solver
                inst = build_problem(st.session_state.spec)
                rr = run_solver(best.name, inst, best.params)
                sol = getattr(inst, "best_solution", None)
                best_cost = rr.cost
            if not sol:
                st.warning("Brak rozwiązania.")
            else:
                weekdays = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri"}
                rows = [
                    {
                        "Day": weekdays.get(c.day, c.day),
                        "Slot": c.hour,
                        "Teacher": f"T{c.teacher}",
                        "Subject": f"S{c.subject}",
                        "Classroom": f"R{c.classroom}",
                    }
                    for c in sol
                ]
                df = pd.DataFrame(rows).sort_values(["Day", "Slot", "Classroom"])
                st.dataframe(df, use_container_width=True, hide_index=True)
