from __future__ import annotations

import time
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Callable

from src.problem_instance import ProblemInstance
from src.solvers.antcolony import AntColonySolver
from src.solvers.genetic import GeneticSolver
from src.solvers.linear_programming import LinearProgrammingSolver
from src.validator import Validation, validate_solution


# --------------------------------------------------------------------------- #
# Result type
# --------------------------------------------------------------------------- #

@dataclass
class SolverResult:
    name: str
    params: dict[str, Any]
    cost: float | None
    runtime_sec: float
    valid: bool
    cost_curve: list[float] = field(default_factory=list)  # per-iter best cost
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "solver": self.name,
            "params": self.params,
            "cost": self.cost,
            "runtime_sec": self.runtime_sec,
            "valid": self.valid,
            "cost_curve": self.cost_curve,
            "extra": self.extra,
        }


def _is_valid(solution: Any, inst: ProblemInstance) -> bool:
    return solution is not None and validate_solution(solution, inst) == Validation.CORRECT


# --------------------------------------------------------------------------- #
# Problem builder
# --------------------------------------------------------------------------- #

def build_problem(spec: dict[str, Any]) -> ProblemInstance:
    """
    Build a ProblemInstance from a JSON-like spec.

    spec = {
      "teacher_num": int,
      "subjects_num": int,
      "classrooms_num": int,
      "time_slots_num": int,
      "lambda1": int,                    # default -1
      "default_classrooms": bool,        # default True
      "pensum_list": list[int] | None,   # default 6 per teacher
      "subject_hours": list[int] | None, # default 1 per subject
      "teacher_subject": list[[t,s],..]  # optional explicit pairs
      "subject_classroom": list[[s,c],..]
    }
    """
    inst = ProblemInstance(
        teacher_num=int(spec["teacher_num"]),
        subjects_num=int(spec["subjects_num"]),
        classrooms_num=int(spec["classrooms_num"]),
        time_slots_num=int(spec["time_slots_num"]),
        lambda_1=int(spec.get("lambda1", -1)),
        default_classrooms=bool(spec.get("default_classrooms", True)),
        pensum_list=spec.get("pensum_list"),
        subject_hours=spec.get("subject_hours"),
    )

    pairs_ts = spec.get("teacher_subject") or []
    if not pairs_ts:
        pairs_ts = [
            (teacher, subject)
            for teacher in range(inst.teacher_num)
            for subject in range(inst.subjects_num)
        ]
    for t, s in pairs_ts:
        inst.add_teacher_subject_pair(int(t), int(s))

    if not bool(spec.get("default_classrooms", True)):
        # caller disabled default class assignment; honor explicit pairs only
        inst.subject_classroom = {s: [] for s in range(inst.subjects_num)}
        inst.classroom_subject = {c: [] for c in range(inst.classrooms_num)}

    pairs_sc = spec.get("subject_classroom") or []
    for s, c in pairs_sc:
        inst.add_subject_classroom_pair(int(s), int(c))

    return inst


# --------------------------------------------------------------------------- #
# Per-solver runners
# --------------------------------------------------------------------------- #

def _run_antcolony(inst: ProblemInstance, params: dict[str, Any]) -> SolverResult:
    solver = AntColonySolver(
        inst,
        ant_count=int(params.get("ant_count", 30)),
        iterations=int(params.get("iterations", 80)),
        alpha=float(params.get("alpha", 1.0)),
        beta=float(params.get("beta", 2.0)),
        rho=float(params.get("rho", 0.5)),
        q=float(params.get("q", 1.0)),
        tau0=float(params.get("tau0", 1.0)),
        seed=params.get("seed"),
    )

    # We instrument the solver to record a per-iteration best cost.
    # This mirrors AntColonySolver.solve(), but keeps the convergence curve.
    t0 = time.perf_counter()
    curve: list[float] = []

    best_solution = None
    best_cost = float("inf")

    for _ in range(solver.iterations):
        iter_best = None
        iter_best_cost = float("inf")

        for _ in range(solver.ant_count):
            sol = solver._build_solution()
            if sol is None:
                continue
            if not _is_valid(sol, solver.problem_instance):
                continue
            cost = solver.evaluate_solution(sol)
            if cost < iter_best_cost:
                iter_best_cost = cost
                iter_best = sol
            if cost < best_cost:
                best_cost = cost
                best_solution = sol

        curve.append(best_cost if best_cost != float("inf") else iter_best_cost)
        solver._evaporate_pheromone()
        if iter_best is not None:
            solver._deposit_pheromone(iter_best, iter_best_cost)
    runtime = time.perf_counter() - t0

    if best_solution is not None:
        solver.problem_instance.best_solution = best_solution
        solver.problem_instance.solutions.append(best_solution)
        cost = best_cost
    else:
        cost = None

    valid = _is_valid(best_solution, inst)

    return SolverResult(
        name="AntColony",
        params=params,
        cost=cost,
        runtime_sec=runtime,
        valid=valid,
        cost_curve=curve,
        extra={"solution": best_solution},
    )


def _run_genetic(inst: ProblemInstance, params: dict[str, Any]) -> SolverResult:
    # Genetic needs an initial feasible solution. OrdinalGenerator validates
    # its output; RandomGenerator is kept as a fallback for tougher inputs.
    from src.generators import OrdinalGenerator, RandomGenerator

    initial = OrdinalGenerator(inst).generate()
    if initial is None:
        with redirect_stdout(StringIO()):
            for _ in range(25):
                candidate = RandomGenerator(inst).generate()
                if _is_valid(candidate, inst):
                    initial = candidate
                    break
    if initial is None:
        return SolverResult(
            name="Genetic",
            params=params,
            cost=None,
            runtime_sec=0.0,
            valid=False,
            cost_curve=[],
            extra={"reason": "could not generate initial feasible solution"},
        )

    generations = int(params.get("generations", 20))
    children_num = int(params.get("children_num", 10))
    accept_worse = bool(params.get("accept_worse", True))

    solver = GeneticSolver(inst)
    curve: list[float] = []
    curve.append(inst.cost_function(initial))

    # We replicate the recursive descent with cost tracking. The existing
    # optimize() does not expose a curve, so we run a loop that matches its
    # contract: take the best of N children each generation.
    t0 = time.perf_counter()
    current = initial
    for _ in range(generations):
        children = solver.get_next_generation(
            current, children_num, accept_worse=accept_worse
        )
        children = [child for child in children if _is_valid(child, inst)]
        if not children:
            break
        best_child = min(children, key=inst.cost_function)
        if inst.cost_function(best_child) < inst.cost_function(current):
            current = best_child
        curve.append(inst.cost_function(current))
    runtime = time.perf_counter() - t0

    final = current
    inst.best_solution = final
    inst.solutions.append(final)
    cost = inst.cost_function(final)
    valid = _is_valid(final, inst)

    return SolverResult(
        name="Genetic",
        params=params,
        cost=cost,
        runtime_sec=runtime,
        valid=valid,
        cost_curve=curve,
        extra={"solution": final},
    )


def _run_lp(inst: ProblemInstance, params: dict[str, Any]) -> SolverResult:
    solver = LinearProgrammingSolver(
        inst,
        time_limit=params.get("time_limit"),
    )
    t0 = time.perf_counter()
    solution = solver.solve()
    runtime = time.perf_counter() - t0

    if solution is None:
        return SolverResult(
            name="LP",
            params=params,
            cost=None,
            runtime_sec=runtime,
            valid=False,
            cost_curve=[],
        )

    cost = inst.cost_function(solution)
    valid = _is_valid(solution, inst)
    return SolverResult(
        name="LP",
        params=params,
        cost=cost,
        runtime_sec=runtime,
        valid=valid,
        cost_curve=[],
        extra={"solution": solution},
    )


_RUNNERS: dict[str, Callable[[ProblemInstance, dict[str, Any]], SolverResult]] = {
    "antcolony": _run_antcolony,
    "genetic": _run_genetic,
    "lp": _run_lp,
}


def run_solver(name: str, inst: ProblemInstance,
               params: dict[str, Any] | None = None) -> SolverResult:
    key = name.lower()
    if key not in _RUNNERS:
        raise ValueError(f"Unknown solver '{name}'. "
                         f"Available: {sorted(_RUNNERS)}")
    return _RUNNERS[key](inst, params or {})


def run_benchmark(spec: dict[str, Any],
                  configs: list[dict[str, Any]]) -> list[SolverResult]:
    """
    Run a list of solver configs against the same problem spec.
    Each config = {"name": "antcolony|genetic|lp", "params": {...}, "label": "..."}
    """
    inst = build_problem(spec)
    results: list[SolverResult] = []
    for cfg in configs:
        r = run_solver(cfg["name"], inst, cfg.get("params") or {})
        if "label" in cfg:
            r.name = cfg["label"]
        results.append(r)
    return results
