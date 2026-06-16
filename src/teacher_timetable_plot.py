import argparse
import importlib
import os
import random
import subprocess
import sys

# Ensure the project root is importable so that `from src...` works regardless
# of the current working directory or how the script is launched.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from src.class_def import Class
from src.problem_instance import ProblemInstance
from src.utils import encode_solution

DEMO_SOLUTION = (
    "3,6,0,0,1;0,1,0,1,1;1,3,1,1,1;4,5,0,2,1;0,0,1,2,1;3,2,0,3,1;1,3,0,4,1;4,5,1,4,1;"
    "5,7,0,0,2;2,1,0,1,2;5,2,1,1,2;5,0,0,2,2;5,7,0,3,2;4,6,0,4,2;0,2,1,4,2;3,4,0,0,3;"
    "4,5,1,0,3;2,1,0,1,3;3,4,1,1,3;1,3,0,2,3;4,6,1,2,3;2,3,0,3,3;0,0,1,3,3;3,4,0,4,3;"
    "5,7,1,4,3;2,1,0,0,4;5,7,1,0,4;3,4,0,1,4;5,7,1,1,4;4,5,0,2,4;1,0,1,2,4;3,6,0,3,4;"
    "4,6,1,3,4;0,0,0,4,4;5,2,1,4,4;0,1,0,0,5;4,5,1,0,5;3,4,0,1,5;5,2,1,1,5;5,0,0,2,5;"
    "0,1,0,3,5;1,3,1,3,5;1,3,0,4,5;0,2,1,4,5"
)


def parse_solution_line(line: str) -> list[Class]:
    classes: list[Class] = []
    line = line.strip()
    if not line:
        return classes
    for item in line.split(";"):
        parts = item.split(",")
        if len(parts) != 5:
            raise ValueError(f"Invalid class encoding: {item}")
        teacher, subject, classroom, hour, day = map(int, parts)
        classes.append(Class(teacher, subject, classroom, hour, day))
    return classes


def derive_dimensions(classes: list[Class]) -> tuple[int, int, int]:
    teacher_num = max((c.teacher for c in classes), default=-1) + 1
    subjects_num = max((c.subject for c in classes), default=-1) + 1
    time_slots_num = max((c.hour for c in classes), default=-1) + 1
    return teacher_num, subjects_num, time_slots_num


def build_teacher_grid(classes: list[Class], teacher_num: int, time_slots_num: int) -> dict[int, dict[int, dict[int, list[Class]]]]:
    grid: dict[int, dict[int, dict[int, list[Class]]]] = {
        teacher: {day: {hour: [] for hour in range(time_slots_num)} for day in range(1, 6)}
        for teacher in range(teacher_num)
    }
    for cls in classes:
        grid[cls.teacher][cls.day][cls.hour].append(cls)
    return grid


def get_subject_colors(subjects_num: int) -> dict[int, tuple[float, float, float, float]]:
    cmap = plt.get_cmap("tab20", max(subjects_num, 1))
    return {subject: cmap(subject) for subject in range(subjects_num)}


def plot_teacher_timetables(
    classes: list[Class],
    output: str,
    teacher_num: int | None = None,
    subjects_num: int | None = None,
    time_slots_num: int | None = None,
) -> None:
    derived_teacher, derived_subjects, derived_slots = derive_dimensions(classes)
    teacher_num = teacher_num if teacher_num is not None else derived_teacher
    subjects_num = subjects_num if subjects_num is not None else derived_subjects
    time_slots_num = time_slots_num if time_slots_num is not None else derived_slots
    teacher_num = max(teacher_num, derived_teacher)
    subjects_num = max(subjects_num, derived_subjects)
    time_slots_num = max(time_slots_num, derived_slots)

    grid = build_teacher_grid(classes, teacher_num, time_slots_num)
    colors = get_subject_colors(subjects_num)

    cols = 2 if teacher_num > 1 else 1
    rows = (teacher_num + cols - 1) // cols if teacher_num > 0 else 1
    fig, axes = plt.subplots(rows, cols, figsize=(7 * cols, 2.5 * rows))
    axes = np.atleast_1d(axes).flatten().tolist()

    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]

    for teacher in range(teacher_num):
        ax = axes[teacher]
        ax.set_title(f"Teacher {teacher}")
        ax.set_xlim(0, 5)
        ax.set_ylim(0, time_slots_num)
        ax.set_xticks([i + 0.5 for i in range(5)], days)
        ax.set_yticks([i + 0.5 for i in range(time_slots_num)],
                     [f"Slot {i}" for i in range(time_slots_num)])
        ax.invert_yaxis()
        ax.set_aspect("auto")
        ax.grid(True, which="both", axis="both", linestyle="--", linewidth=0.5, alpha=0.4)

        for day in range(1, 6):
            for hour in range(time_slots_num):
                items = grid[teacher][day][hour]
                if not items:
                    continue
                cls = items[0]
                color = colors[cls.subject]
                rect = patches.Rectangle((day - 1, hour), 1, 1, facecolor=color, edgecolor="black", alpha=0.8)
                ax.add_patch(rect)
                label = f"S{cls.subject}\nR{cls.classroom}"
                ax.text(day - 0.5, hour + 0.5, label, ha="center", va="center", fontsize=8, color="black")

    for extra in range(teacher_num, len(axes)):
        axes[extra].axis("off")

    legend_handles = [patches.Patch(color=colors[s], label=f"Subject {s}") for s in range(subjects_num)]
    if legend_handles:
        fig.legend(handles=legend_handles, loc="lower center", ncol=min(subjects_num, 6), bbox_to_anchor=(0.5, 0.02))
    fig.suptitle("Teachers timetable", fontsize=14)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))

    output_dir = os.path.dirname(output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    fig.savefig(output, dpi=200)
    plt.close(fig)


def teacher_timetable_plot(solution: str, output: str = "teachers.png") -> None:
    output = "plots/" + output
    classes = parse_solution_line(solution)
    plot_teacher_timetables(classes, output)


def load_instance(spec: str) -> ProblemInstance:
    """Load a ProblemInstance from a ``module:function`` specification."""
    if ":" not in spec:
        raise ValueError(
            f"Invalid --instance value '{spec}'. Expected format 'module:function', "
            "e.g. 'generator_test:make_dense_instance'."
        )
    module_name, func_name = spec.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            f"Could not import instance module '{module_name}'. "
            f"Run from the project root (or with PYTHONPATH set to it). Original error: {exc}"
        ) from exc
    if not hasattr(module, func_name):
        raise AttributeError(f"Module '{module_name}' has no attribute '{func_name}'.")
    instance = getattr(module, func_name)()
    if not isinstance(instance, ProblemInstance):
        raise TypeError(f"'{spec}' did not return a ProblemInstance (got {type(instance).__name__}).")
    return instance


def generate_solutions(instance: ProblemInstance, want: int, max_tries: int = 20000) -> list[str]:
    from src.generators import OrdinalGenerator

    seen: list[str] = []
    seen_keys: set[str] = set()
    tries = 0
    while len(seen) < want and tries < max_tries:
        tries += 1
        generator = OrdinalGenerator(instance)
        sol = generator.generate()
        if sol is None:
            continue
        key = generator.canonical_key(sol)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        seen.append(key)
    return seen


def read_solution_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def select_line(lines: list[str], line_no: int | None, use_random: bool) -> tuple[str, int]:
    if not lines:
        raise ValueError("No solutions available to plot.")
    if use_random:
        idx = random.randrange(len(lines))
        return lines[idx], idx + 1
    line_no = line_no or 1
    if line_no < 1 or line_no > len(lines):
        raise IndexError(f"--line {line_no} is out of range (only {len(lines)} solution(s) available).")
    return lines[line_no - 1], line_no


def open_file(path: str) -> None:
    try:
        if sys.platform.startswith("darwin"):
            subprocess.run(["open", path], check=False)
        elif os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception as exc:  # noqa: BLE001 - opening is best-effort
        print(f"Could not open '{path}' automatically: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Plot per-teacher timetables from an encoded solution."
    )
    parser.add_argument(
        "--instance",
        help="Instance builder as 'module:function', e.g. 'generator_test:make_dense_instance'.",
    )
    parser.add_argument(
        "--solutions",
        help="Path to a solutions file (one encoded solution per line). "
        "If it does not exist and --instance is given, it will be generated.",
    )
    parser.add_argument("--line", type=int, default=None, help="1-indexed solution line to plot (default: 1).")
    parser.add_argument("--random", action="store_true", help="Pick a random solution line.")
    parser.add_argument("--output", default="teachers.png", help="Output image path (default: teachers.png).")
    parser.add_argument("--open", dest="open_after", action="store_true", help="Open the image after generating it.")
    args = parser.parse_args(argv)

    instance = load_instance(args.instance) if args.instance else None
    if args.solutions:
        if os.path.exists(args.solutions):
            lines = read_solution_lines(args.solutions)
        else:
            if instance is None:
                parser.error(
                    f"Solutions file '{args.solutions}' does not exist and no --instance "
                    "was provided to generate one."
                )
            want = max(args.line or 1, 20 if args.random else (args.line or 1))
            lines = generate_solutions(instance, want=want)
            if not lines:
                parser.error("Failed to generate any valid solution for the given instance.")
            out_dir = os.path.dirname(args.solutions)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.solutions, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print(f"Generated {len(lines)} solution(s) -> {args.solutions}")
    elif instance is not None:
        want = max(args.line or 1, 20 if args.random else (args.line or 1))
        lines = generate_solutions(instance, want=want)
        if not lines:
            parser.error("Failed to generate any valid solution for the given instance.")
    else:
        lines = [DEMO_SOLUTION]

    solution_line, chosen = select_line(lines, args.line, args.random)
    classes = parse_solution_line(solution_line)

    teacher_num = instance.teacher_num if instance else None
    subjects_num = instance.subjects_num if instance else None
    time_slots_num = instance.time_slots_num if instance else None

    plot_teacher_timetables(
        classes,
        args.output,
        teacher_num=teacher_num,
        subjects_num=subjects_num,
        time_slots_num=time_slots_num,
    )
    print(f"Plotted solution line {chosen} -> {args.output}")

    if args.open_after:
        open_file(args.output)


if __name__ == "__main__":
    main()
