from random import choice
from src.validator import *
from src.utils import encode_solution
from copy import deepcopy
import random

MAX_ITER = int(10e6)

class RandomGenerator:
    def __init__(self, problem_instance: ProblemInstance):
        self.problemInstance = problem_instance
    def generate(self):
        subjects_left_to_deal = dict()
        for subject_num in range(self.problemInstance.subjects_num):
            subjects_left_to_deal[subject_num] = self.problemInstance.subject_hours[subject_num]
        solution = []
        iteration_count = 0
        while len(subjects_left_to_deal.keys()) > 0 or iteration_count > MAX_ITER:
            print("Subjects left to deal:", sum(subjects_left_to_deal.values()))
            print("Picking random subject")
            subject = choice(list(subjects_left_to_deal))
            print("Chose subject", subject)
            available_teachers = self.problemInstance.subject_teacher[subject]
            print("Available teachers for this subject:", available_teachers)
            teacher = choice(available_teachers)
            print("Chose teacher:", teacher)
            options = self.get_available_option_for_classes(solution, subject, teacher)
            print(f"Found {len(options)} valid options")
            if len(options) == 0:
                print(f"Reached a deadend during generation! Try redrawing.")
                return None
            option = choice(options)
            print(f"Chose day {option.day} in time slot number {option.hour}")
            subjects_left_to_deal[subject] -= 1
            self.clear_fully_assigned_subjects(subjects_left_to_deal)
            solution.append(option)
        if len(subjects_left_to_deal.keys()) > 0:
            print(f"Generator made too many iterations (more than {MAX_ITER} iterations)")
            return None
        return solution

    def get_available_option_for_classes(self, current_solution, subject, teacher):
        available_options = []
        for day in range(1, 6):
            for time_slot in range(self.problemInstance.time_slots_num):
                for classroom in self.problemInstance.subject_classroom[subject]:
                    teachers_assigned_to_slot = 0
                    for teacher_in_slot in range(self.problemInstance.teacher_num):
                        for subject_in_slot in range(self.problemInstance.subjects_num):
                            if Class(teacher_in_slot, subject_in_slot, classroom, time_slot, day) in current_solution:
                                teachers_assigned_to_slot += 1
                    if teachers_assigned_to_slot == 0:
                        available_options.append(Class(teacher, subject, classroom, time_slot, day))
        return available_options

    @staticmethod
    def clear_fully_assigned_subjects(subjects: dict):
       for subject_num in list(subjects):
           if subjects[subject_num] == 0:
            del subjects[subject_num]


class OrdinalGenerator:
    def __init__(self, problem_instance: ProblemInstance):
        self.problem_instance = problem_instance

    def generate(self):
        instance = deepcopy(self.problem_instance)
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
            for _ in range(MAX_ITER):
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
