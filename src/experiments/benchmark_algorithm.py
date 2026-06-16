from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from src.class_def import Class
from src.experiments.load_instance import load_instance, LoadedInstance
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

def _write_json(path: Path, rows: list[BenchmarkRow]) -> None:
    _ensure_parent(path)
    path.write_text(
        json.dumps([asdict(r) for r in rows], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_benchmark(
    *,
    loaded: LoadedInstance,
    solver: str,
    repeat: int = 1,
    seed: int | None = None,
    output_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    quiet: bool = False,
    # mrówki
    ant_count: int = 30,
    iterations: int = 80,
    alpha: float = 1.0,
    beta: float = 2.0,
    rho: float = 0.5,
    q: float = 1.0,
    tau0: float = 1.0,
    # lp
    time_limit: int | None = None,
    # genetyczny
    generations: int = 20,
    children_num: int = 10,
    accept_worse: bool = False,
    generator: str = "ordinal",
    gen_max_tries: int = 2000,
) -> list[BenchmarkRow]:

    if solver not in {"antcolony", "lp", "genetic"}:
        raise ValueError("solver must be one of: antcolony, lp, genetic")
    if generator not in {"ordinal", "random"}:
        raise ValueError("generator must be one of: ordinal, random")
    if repeat < 1:
        raise ValueError("repeat must be >= 1")

    inst = loaded.instance

    if output_path is None and output_dir is not None:
        output_path = Path(output_dir) / Path(loaded.instance_id + ".json" ).name

    rows: list[BenchmarkRow] = []

    for i in range(repeat):
        run_seed = None if seed is None else (seed + i)
        params: dict[str, Any] = {
            "instance": str(Path(loaded.instance_id)),
            "solver": solver,
            "repeat_index": i,
        }

        t0 = time.perf_counter()
        solution: list[Class] | None = None
        validation: Any = "NOT_RUN"
        cost: float | None = None

        try:
            if solver == "antcolony":
                solver_obj = AntColonySolver(
                    inst,
                    ant_count=ant_count,
                    iterations=iterations,
                    alpha=alpha,
                    beta=beta,
                    rho=rho,
                    q=q,
                    tau0=tau0,
                    seed=run_seed,
                )
                solution = solver_obj.solve()
                if solution is not None:
                    cost = float(solver_obj.evaluate_solution(solution))
                params.update(
                    {
                        "ant_count": ant_count,
                        "iterations": iterations,
                        "alpha": alpha,
                        "beta": beta,
                        "rho": rho,
                        "q": q,
                        "tau0": tau0,
                    }
                )

            elif solver == "lp":
                from src.solvers.linear_programming import LinearProgrammingSolver

                solver_obj = LinearProgrammingSolver(inst, time_limit=time_limit)
                solution = solver_obj.solve()
                if solution is not None:
                    cost = float(solver_obj.evaluate_solution(solution))
                params.update({"time_limit": time_limit})

            else:  # genetic
                if run_seed is not None:
                    random.seed(run_seed)

                if generator == "ordinal":
                    from src.generators import OrdinalGenerator

                    gen = OrdinalGenerator(inst)
                    init_sol = None
                    for _ in range(gen_max_tries):
                        init_sol = gen.generate()
                        if init_sol is not None:
                            break
                else:
                    from src.generators import RandomGenerator

                    gen = RandomGenerator(inst)
                    init_sol = None
                    for _ in range(gen_max_tries):
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
                        generations=generations,
                        children_num=children_num,
                        accept_worse=accept_worse,
                        verbose=not quiet,
                    )
                    cost = float(inst.cost_function(solution))

                params.update(
                    {
                        "generator": generator,
                        "gen_max_tries": gen_max_tries,
                        "generations": generations,
                        "children_num": children_num,
                        "accept_worse": accept_worse,
                    }
                )

            if solution is None:
                ok = False
                validation = "NO_SOLUTION"
            else:
                validation = validate_solution(solution, inst)
                ok = validation == Validation.CORRECT

        except Exception as e:
            ok = False
            validation = f"EXCEPTION: {type(e).__name__}: {e}"
            solution = None

        runtime_s = time.perf_counter() - t0
        solution_encoding = None if solution is None else encode_solution(_sorted_solution(solution))

        rows.append(
            BenchmarkRow(
                instance_id=loaded.instance_id,
                solver=solver,
                seed=run_seed,
                ok=ok,
                validation=_validation_to_str(validation),
                cost=cost,
                runtime_s=runtime_s,
                params_json=json.dumps(params, ensure_ascii=False),
                solution_encoding=solution_encoding,
            )
        )

    if output_path is not None and rows:
        out = Path(output_path)
        _write_json(out, rows)

    return rows


def rows_to_dicts(rows: list[BenchmarkRow]) -> list[dict[str, Any]]:
    return [asdict(r) for r in rows]


def benchmark_algorithm(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark scheduling algorithms on JSON instances.")
    parser.add_argument("--instance", required=True, help="Path to JSON instance file.")
    parser.add_argument("--solver", required=True, choices=["antcolony", "lp", "genetic"])
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", default=None, help="Optional output file (.jsonl append, or .json overwrite).")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory. If set and --output is not, output file name matches the instance filename.",
    )
    parser.add_argument("--quiet", action="store_true", default=False)
    #mrówki
    parser.add_argument("--ant-count", type=int, default=30)
    parser.add_argument("--iterations", type=int, default=80)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=2.0)
    parser.add_argument("--rho", type=float, default=0.5)
    parser.add_argument("--q", type=float, default=1.0)
    parser.add_argument("--tau0", type=float, default=1.0)
    #ilp
    parser.add_argument("--time-limit", type=int, default=None)
    #genetyczny
    parser.add_argument("--generations", type=int, default=20)
    parser.add_argument("--children-num", type=int, default=10)
    parser.add_argument("--accept-worse", action="store_true", default=False)
    parser.add_argument("--generator", choices=["ordinal", "random"], default="ordinal")
    parser.add_argument("--gen-max-tries", type=int, default=2000)

    args = parser.parse_args(argv)

    run_benchmark(
        instance_path=args.instance,
        solver=args.solver,
        repeat=args.repeat,
        seed=args.seed,
        output_path=args.output,
        output_dir=args.output_dir,
        quiet=args.quiet,
        ant_count=args.ant_count,
        iterations=args.iterations,
        alpha=args.alpha,
        beta=args.beta,
        rho=args.rho,
        q=args.q,
        tau0=args.tau0,
        time_limit=args.time_limit,
        generations=args.generations,
        children_num=args.children_num,
        accept_worse=args.accept_worse,
        generator=args.generator,
        gen_max_tries=args.gen_max_tries,
    )
    return 0


def benchmark_configuration(algorithms, instances, seed):

    for algorithm in algorithms:
        for instance in instances:
            run_benchmark(instance_path=instance, solver=algorithm, )

if __name__ == "__main__":
    raise SystemExit(benchmark_algorithm())