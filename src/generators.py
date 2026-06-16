from random import choice
from src.validator import *
from src.utils import encode_solution
import random

MAX_ITER = int(10e6)

class RandomGenerator:
    def __init__(self, problem_instance: ProblemInstance):
        self.problemInstance = problem_instance

    def generate(self):
        subjects_left_to_deal = {
            subject_num: self.problemInstance.subject_hours[subject_num]
            for subject_num in range(self.problemInstance.subjects_num)
            if self.problemInstance.subject_hours[subject_num] > 0
        }
        solution = []
        # Zajętość zasobów trzymamy w zbiorach, aby unikać kosztownego
        # przeszukiwania listy rozwiązań przy każdej decyzji.
        occupied_classroom: set[tuple[int, int, int]] = set()  # (day, hour, classroom)
        occupied_teacher: set[tuple[int, int, int]] = set()    # (day, hour, teacher)

        while subjects_left_to_deal:
            subject = choice(list(subjects_left_to_deal))
            available_teachers = self.problemInstance.subject_teacher[subject]
            if not available_teachers:
                return None
            teacher = choice(available_teachers)
            options = self.get_available_option_for_classes(
                occupied_classroom, occupied_teacher, subject, teacher
            )
            if not options:
                return None
            option = choice(options)
            occupied_classroom.add((option.day, option.hour, option.classroom))
            occupied_teacher.add((option.day, option.hour, option.teacher))
            subjects_left_to_deal[subject] -= 1
            if subjects_left_to_deal[subject] == 0:
                del subjects_left_to_deal[subject]
            solution.append(option)
        return solution

    def get_available_option_for_classes(self, occupied_classroom, occupied_teacher, subject, teacher):
        available_options = []
        for day in range(1, 6):
            for time_slot in range(self.problemInstance.time_slots_num):
                if (day, time_slot, teacher) in occupied_teacher:
                    continue
                for classroom in self.problemInstance.subject_classroom[subject]:
                    if (day, time_slot, classroom) not in occupied_classroom:
                        available_options.append(Class(teacher, subject, classroom, time_slot, day))
        return available_options


class OrdinalGenerator:
    def __init__(self, problem_instance: ProblemInstance):
        self.problem_instance = problem_instance

    def generate(self):
        instance = self.problem_instance
        subject_hours = list(instance.subject_hours)
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

            # Zamiast losować slot do skutku (kosztowne na ciasnych instancjach),
            # przeglądamy sloty w losowej kolejności i bierzemy pierwszy wolny.
            # Dzięki temu pojedyncza próba jest O(liczba slotów), a nie O(MAX_ITER).
            placed = False
            shuffled_slots = slots[:]
            random.shuffle(shuffled_slots)
            for day, hour in shuffled_slots:
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

    @staticmethod
    def canonical_key(sol: list[Class]) -> str:
        sol_sorted = sorted(sol, key=lambda x: (x.day, x.hour, x.classroom, x.teacher, x.subject))
        return encode_solution(sol_sorted)


# Zostawione na potrzeby testowania generatora 2
def main(problem: ProblemInstance, filename: str, want: int = 100, max_tries: int = 20000):
    open(filename, "w").close()
    seen: set[str] = set()
    tries = 0
    while len(seen) < want and tries < max_tries:
        tries += 1
        generator = OrdinalGenerator(problem)
        sol = generator.generate()
        if sol is None:
            continue

        key = generator.canonical_key(sol)
        if key in seen:
            continue

        seen.add(key)
        with open(filename, "a") as f:
            f.write(key + "\n")

    print(f"Saved {len(seen)} unique solutions in {tries} attempts.")
