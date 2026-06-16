from __future__ import annotations

import argparse
import csv
import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from src.class_def import Class
from src.experiments.load_instance import load_instance
from src.solvers.antcolony import AntColonySolver
from src.utils import encode_solution
from src.validator import Validation, validate_solution


@dataclass(frozen=True)
class BenchmarkRow:
    instance_id: str
    solver: str
    seed: int | None
    ok: bool
    validation: str
    cost: float | None
    runtime_s: float
    params_json: str
    solution_encoding: str | None


def _sorted_solution(sol: list[Class]) -> list[Class]:
    return sorted(sol, key=lambda x: (x.day, x.hour, x.classroom, x.teacher, x.subject))


def _validation_to_str(v: Any) -> str:
    if isinstance(v, Validation):
        return v.name
    if isinstance(v, tuple) and v and isinstance(v[0], Validation):
        return v[0].name
    return str(v)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_jsonl(path: Path, rows: Iterable[BenchmarkRow]) -> None:
    _ensure_parent(path)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def _write_csv(path: Path, rows: list[BenchmarkRow]) -> None:
    _ensure_parent(path)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def benchmark_algorithm(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark scheduling algorithms on JSON instances.")
    parser.add_argument("--instance", required=True, help="Path to JSON instance file.")
    parser.add_argument("--solver", required=True, choices=["antcolony", "lp", "genetic"])
    parser.add_argument("--repeat", type=int, default=1, help="How many runs to execute.")
    parser.add_argument("--seed", type=int, default=None, help="Seed for stochastic solvers (base seed).")
    parser.add_argument(
        "--output",
        default="results/benchmark.jsonl",
        help="Output file (.jsonl or .csv). Rows are appended.",
    )


    parser.add_argument("--ant-count", type=int, default=30)
    parser.add_argument("--iterations", type=int, default=80)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=2.0)
    parser.add_argument("--rho", type=float, default=0.5)
    parser.add_argument("--q", type=float, default=1.0)
    parser.add_argument("--tau0", type=float, default=1.0)

    parser.add_argument("--time-limit", type=int, default=None, help="Time limit for LP solver (seconds).")

    parser.add_argument("--generations", type=int, default=20)
    parser.add_argument("--children-num", type=int, default=10)
    parser.add_argument("--accept-worse", action="store_true", default=False)
    parser.add_argument("--generator", choices=["ordinal", "random"], default="ordinal")
    parser.add_argument("--gen-max-tries", type=int, default=2000, help="Max tries to get an initial valid solution.")
    parser.add_argument("--quiet", action="store_true", help="Reduce console output (best-effort).")

    args = parser.parse_args(argv)
    loaded = load_instance(args.instance)
    inst = loaded.instance
    print("DEBUG:", args.output)
    out_path = Path(args.output)
    rows: list[BenchmarkRow] = []

    for i in range(args.repeat):
        run_seed = None if args.seed is None else (args.seed + i)

        params: dict[str, Any] = {
            "instance": str(Path(args.instance)),
            "solver": args.solver,
            "repeat_index": i,
        }

        t0 = time.perf_counter()
        solution: list[Class] | None = None
        validation: Any = "NOT_RUN"
        cost: float | None = None

        try:
            if args.solver == "antcolony":
                solver = AntColonySolver(
                    inst,
                    ant_count=args.ant_count,
                    iterations=args.iterations,
                    alpha=args.alpha,
                    beta=args.beta,
                    rho=args.rho,
                    q=args.q,
                    tau0=args.tau0,
                    seed=run_seed,
                )
                solution = solver.solve()
                if solution is not None:
                    cost = float(solver.evaluate_solution(solution))

                params.update(
                    {
                        "ant_count": args.ant_count,
                        "iterations": args.iterations,
                        "alpha": args.alpha,
                        "beta": args.beta,
                        "rho": args.rho,
                        "q": args.q,
                        "tau0": args.tau0,
                    }
                )

            elif args.solver == "lp":
                from src.solvers.linear_programming import LinearProgrammingSolver

                solver = LinearProgrammingSolver(inst, time_limit=args.time_limit)
                solution = solver.solve()
                if solution is not None:
                    cost = float(solver.evaluate_solution(solution))
                params.update({"time_limit": args.time_limit})

            else:  # genetic
                if run_seed is not None:
                    random.seed(run_seed)

                if args.generator == "ordinal":
                    from src.generators import OrdinalGenerator

                    gen = OrdinalGenerator(inst)
                    init_sol = None
                    for _ in range(args.gen_max_tries):
                        init_sol = gen.generate_one()
                        if init_sol is not None:
                            break
                else:
                    from src.generators import RandomGenerator

                    gen = RandomGenerator(inst)
                    init_sol = None
                    for _ in range(args.gen_max_tries):
                        init_sol = gen.generate()
                        if init_sol is not None:
                            break

                if init_sol is None:
                    solution = None
                else:
                    from src.solvers.genetic import GeneticSolver

                    ga = GeneticSolver(inst)
                    solution = ga.optimize(
                        init_sol,
                        generations=args.generations,
                        children_num=args.children_num,
                        accept_worse=args.accept_worse,
                        verbose=not args.quiet,
                    )
                    cost = float(inst.cost_function(solution))

                params.update(
                    {
                        "generator": args.generator,
                        "gen_max_tries": args.gen_max_tries,
                        "generations": args.generations,
                        "children_num": args.children_num,
                        "accept_worse": args.accept_worse,
                    }
                )

            if solution is None:
                ok = False
                validation = "NO_SOLUTION"
            else:
                validation = validate_solution(solution, inst)
                ok = (validation == Validation.CORRECT)  # validator returns either enum or tuple

        except Exception as e:
            ok = False
            validation = f"EXCEPTION: {type(e).__name__}: {e}"
            solution = None

        runtime_s = time.perf_counter() - t0

        solution_encoding = None
        if solution is not None:
            solution_encoding = encode_solution(_sorted_solution(solution))

        rows.append(
            BenchmarkRow(
                instance_id=loaded.instance_id,
                solver=args.solver,
                seed=run_seed,
                ok=ok,
                validation=_validation_to_str(validation),
                cost=cost,
                runtime_s=runtime_s,
                params_json=json.dumps(params, ensure_ascii=False),
                solution_encoding=solution_encoding,
            )
        )

    if not rows:
        return 2

    if out_path.suffix.lower() == ".csv":
        _write_csv(out_path, rows)
    else:
        _write_jsonl(out_path, rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(benchmark_algorithm())