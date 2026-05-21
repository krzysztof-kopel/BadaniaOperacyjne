import argparse

from src.problem_instance import ProblemInstance
from src.solvers.antcolony import AntColonySolver
from src.solvers.linear_programming import LinearProgrammingSolver
from src.validator import Validation, validate_solution


def make_demo_instance() -> ProblemInstance:
    inst = ProblemInstance(
        teacher_num=8,
        subjects_num=10,
        classrooms_num=4,
        time_slots_num=6,
        default_classrooms=True,
        pensum_list=[10, 10, 10, 10, 10, 10, 10, 10],
        subject_hours=[4, 4, 3, 3, 2, 2, 2, 3, 4, 3],
    )

    for s in [0, 1, 2]:
        inst.add_teacher_subject_pair(0, s)
    for s in [0, 3, 4]:
        inst.add_teacher_subject_pair(1, s)
    for s in [1, 3, 5]:
        inst.add_teacher_subject_pair(2, s)
    for s in [2, 4, 6]:
        inst.add_teacher_subject_pair(3, s)
    for s in [5, 6, 7]:
        inst.add_teacher_subject_pair(4, s)
    for s in [7, 8, 9]:
        inst.add_teacher_subject_pair(5, s)
    for s in [0, 8, 9]:
        inst.add_teacher_subject_pair(6, s)
    for s in [1, 2, 8]:
        inst.add_teacher_subject_pair(7, s)

    return inst


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scheduling solvers.")
    parser.add_argument(
        "--solver",
        choices=["antcolony", "lp"],
        default="antcolony",
        help="Solver to run (default: antcolony).",
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--ant-count", type=int, default=30)
    parser.add_argument("--iterations", type=int, default=80)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=2.0)
    parser.add_argument("--rho", type=float, default=0.5)
    parser.add_argument("--q", type=float, default=1.0)
    parser.add_argument("--tau0", type=float, default=1.0)
    parser.add_argument("--time-limit", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    instance = make_demo_instance()

    if args.solver == "antcolony":
        solver = AntColonySolver(
            instance,
            ant_count=args.ant_count,
            iterations=args.iterations,
            alpha=args.alpha,
            beta=args.beta,
            rho=args.rho,
            q=args.q,
            tau0=args.tau0,
            seed=args.seed,
        )
    else:
        solver = LinearProgrammingSolver(instance, time_limit=args.time_limit)

    solution = solver.solve()
    if solution is None:
        print("No feasible solution found.")
        return 1

    validation = validate_solution(solution, instance)
    if validation != Validation.CORRECT:
        print("Solution failed validation:", validation)
        return 1

    cost = solver.evaluate_solution(solution)
    print(f"Solution cost: {cost}")
    for lesson in sorted(solution, key=lambda x: (x.day, x.hour, x.classroom, x.teacher, x.subject)):
        print(lesson)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
