import os

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from src.class_def import Class


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


def plot_teacher_timetables(classes: list[Class], output: str) -> None:
    teacher_num, subjects_num, time_slots_num = derive_dimensions(classes)
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
    fig.savefig(output, dpi=200)
    plt.close(fig)


def teacher_timetable_plot(solution: str, output: str = "teachers.png") -> None:
    output = "plots/" + output
    classes = parse_solution_line(solution)
    output_dir = os.path.dirname(output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    plot_teacher_timetables(classes, output)


if __name__ == "__main__":
    teacher_timetable_plot("3,6,0,0,1;0,1,0,1,1;1,3,1,1,1;4,5,0,2,1;0,0,1,2,1;3,2,0,3,1;1,3,0,4,1;4,5,1,4,1;5,7,0,0,2;2,1,0,1,2;5,2,1,1,2;5,0,0,2,2;5,7,0,3,2;4,6,0,4,2;0,2,1,4,2;3,4,0,0,3;4,5,1,0,3;2,1,0,1,3;3,4,1,1,3;1,3,0,2,3;4,6,1,2,3;2,3,0,3,3;0,0,1,3,3;3,4,0,4,3;5,7,1,4,3;2,1,0,0,4;5,7,1,0,4;3,4,0,1,4;5,7,1,1,4;4,5,0,2,4;1,0,1,2,4;3,6,0,3,4;4,6,1,3,4;0,0,0,4,4;5,2,1,4,4;0,1,0,0,5;4,5,1,0,5;3,4,0,1,5;5,2,1,1,5;5,0,0,2,5;0,1,0,3,5;1,3,1,3,5;1,3,0,4,5;0,2,1,4,5")