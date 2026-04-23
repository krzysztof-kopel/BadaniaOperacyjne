from validator import *
from utils import encode_solution
from copy import deepcopy
import random

MAXITER = 1000

def generate(problem: ProblemInstance):
    instance = deepcopy(problem)
    subject_hours = deepcopy(instance.subject_hours)
    solution = []
    days = range(1, 6)
    slots = [(d, h) for d in days for h in range(instance.time_slots_num)]
    teacher_slots = [[[True for _ in range(instance.time_slots_num)] for _ in days] for _ in range(instance.teacher_num)]
    classroom_slots = [[[True for _ in range(instance.time_slots_num)] for _ in days] for _ in range(instance.classrooms_num)]
    teacher_load = [0 for _ in range(instance.teacher_num)]
    subjects = list(range(instance.subjects_num))
    subjects.sort(key=lambda s: (len(instance.subject_teacher[s]) * len(instance.subject_classroom[s]) or 10**9))

    while any(subject_hours):
        subject = next((s for s in subjects if subject_hours[s] > 0), None)
        if subject is None:
            break

        eligible_teachers = [t for t in instance.subject_teacher[subject] if instance.teacher_pensum[t] > 0]
        if not eligible_teachers:
            return None

        teacher = min(eligible_teachers, key=lambda t: teacher_load[t] / instance.teacher_pensum[t])
        classrooms = instance.subject_classroom[subject]
        if not classrooms:
            return None

        placed = False
        for _ in range(MAXITER):
            day, hour = random.choice(slots)
            day_idx = day - 1

            if not teacher_slots[teacher][day_idx][hour]:
                continue

            classroom = None
            for c in classrooms:
                if classroom_slots[c][day_idx][hour]:
                    classroom = c
                    break
            if classroom is None:
                continue

            teacher_slots[teacher][day_idx][hour] = False
            classroom_slots[classroom][day_idx][hour] = False
            teacher_load[teacher] += 1
            subject_hours[subject] -= 1
            solution.append(Class(teacher, subject, classroom, hour, day))
            placed = True
            break
        if not placed:
            return None

    if validate_solution(solution, instance) == Validation.CORRECT:
        return solution

    return None

def canonical_key(sol: list[Class]) -> str:
    sol_sorted = sorted(sol, key=lambda x: (x.day, x.hour, x.classroom, x.teacher, x.subject))
    return encode_solution(sol_sorted)


def main(problem: ProblemInstance, filename: str, want: int = 100, max_tries: int = 20000):
    open(filename, "w").close()
    seen: set[str] = set()
    tries = 0
    while len(seen) < want and tries < max_tries:
        tries += 1
        sol = generate(problem)
        if sol is None:
            continue

        key = canonical_key(sol)
        if key in seen:
            continue

        seen.add(key)
        with open(filename, "a") as f:
            f.write(key + "\n")

    print(f"Saved {len(seen)} unique solutions in {tries} attempts.")

