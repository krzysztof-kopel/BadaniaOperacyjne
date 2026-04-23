from src.problem_instance import ProblemInstance
from random import choice
from src.class_def import Class
MAX_GEN_ITERATIONS = 10e6

class Generator:
    def __init__(self, problemInstance: ProblemInstance):
        self.problemInstance = problemInstance
    def generateBaseSolution(self):
        subjects_left_to_deal = dict()
        for subject_num in range(self.problemInstance.subjects_num):
            subjects_left_to_deal[subject_num] = self.problemInstance.subject_hours[subject_num]
        solution = []
        iteration_count = 0
        while len(subjects_left_to_deal.keys()) > 0 or iteration_count > MAX_GEN_ITERATIONS:
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
            print(f"Generator made too many iterations (more than {MAX_GEN_ITERATIONS} iterations)")
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

    def clear_fully_assigned_subjects(self, subjects: dict):
       for subject_num in list(subjects):
           if subjects[subject_num] == 0:
            del subjects[subject_num]
