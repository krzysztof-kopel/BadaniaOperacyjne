import numpy as np
import random

from src.generators import RandomGenerator
from src.solvers.solver import Solver
from src.problem_instance import ProblemInstance, Class
from src.validator import validate_solution, Validation


class GeneticSolver(Solver):
    def __init__(self, problem_instance: ProblemInstance):
        super().__init__(problem_instance)

    def solve(self) -> list[Class] | None:
        """
        Implementacja solve z oryginalnej klasy Solver.
        """
        initial_solution = self.problem_instance.best_solution
        if initial_solution is None:
            generator = RandomGenerator(self.problem_instance)
            initial_solution = generator.generate()
        optimized_solution = self.optimize(initial_solution=initial_solution)
        return optimized_solution

    def optimize(self, initial_solution: list[Class], generations: int=10, children_num: int=5, accept_worse: bool=True,
                 verbose: bool=False) -> list[Class]:
        """
        Optymalizuje plan lekcji za pomocą algorytmu genetycznego.
        :param initial_solution: Początkowe rozwiązanie, które będzie ulepszane.
        :param generations: Liczba pokoleń do wygenerowania.
        :param children_num: Liczba nowych rozwiązań do wygenerowania w każdym pokoleniu.
        :param accept_worse: Czy akceptować rozwiązania o większej wartości funkcji kosztu?
        :param verbose: Czy wypisywać stan obliczeń?
        :return: Najlepsze znalezione rozwiązanie.
        """
        if generations == 0:
            print(f"Znaleziono rozwiązanie o koszcie {self.problem_instance.cost_function(initial_solution)}")
            return initial_solution

        current_solution = initial_solution
        if not validate_solution(current_solution, self.problem_instance):
            raise ValueError("Initial solution is not valid.")

        new_solutions = self.get_next_generation(current_solution, children_num, accept_worse)
        if not new_solutions:
            return current_solution

        better_solutions = [s for s in new_solutions if self.problem_instance.cost_function(s) < self.problem_instance.cost_function(current_solution)]
        better_solutions = better_solutions[:3]
        if not better_solutions:
            better_solutions = [min(new_solutions, key=lambda s: self.problem_instance.cost_function(s))]
        if verbose:
            print(f"Koszty rozwiązań na {generations} generacji przed końcem: {[self.problem_instance.cost_function(i) for i in better_solutions]}")

        children_results = [(s, self.optimize(s, generations - 1, children_num, accept_worse, verbose=verbose)) for s in better_solutions]

        best_child_solution = min(children_results, key=lambda r: self.problem_instance.cost_function(r[1]))[1]
        if self.problem_instance.cost_function(best_child_solution) < self.problem_instance.cost_function(current_solution):
            current_solution = best_child_solution
            if not self.problem_instance.best_solution or self.problem_instance.cost_function(self.problem_instance.best_solution) > self.problem_instance.cost_function(current_solution):
                self.problem_instance.best_solution = current_solution
        return current_solution

    def get_next_generation(self, current_solution: list[Class], children_num: int, accept_worse: bool=True) -> list[list[Class]]:
        """
        Generuje następne pokolenie w algorytmie genetycznym.
        :param current_solution: Obecne rozwiązanie, na podstawie którego generujemy nowe.
        :param children_num: Liczba nowych rozwiązań do wygenerowania.
        :param accept_worse: Czy zwracać rozwiązania o większej wartości funkcji kosztu?
        :return: Lista nowych rozwiązań.
        """
        initial_class_matrix = np.zeros((self.problem_instance.teacher_num, self.problem_instance.subjects_num,
                                         self.problem_instance.classrooms_num, self.problem_instance.time_slots_num, 5),
                                        dtype=bool)
        for c in current_solution:
            initial_class_matrix[c.teacher][c.subject][c.classroom][c.hour][c.day - 1] = True

        new_solutions = []
        iter_count = 0
        while len(new_solutions) < children_num and iter_count < 100:
            iter_count += 1
            
            temp_solution = list(current_solution)
            temp_class_matrix = np.copy(initial_class_matrix)

            class_to_change = random.choice(temp_solution)
            element_to_change = random.choice(['teacher', 'classroom', 'hour', 'day'])

            try:
                idx_to_change = temp_solution.index(class_to_change)
            except ValueError:
                continue

            mutated_class = None

            match element_to_change:
                case 'teacher':
                    if len(self.problem_instance.subject_teacher[class_to_change.subject]) <= 1:
                        continue
                    new_teacher = random.choice(self.problem_instance.subject_teacher[class_to_change.subject])
                    if (new_teacher == class_to_change.teacher
                           or temp_class_matrix[new_teacher, :, :, class_to_change.hour, class_to_change.day - 1].any()):
                        continue

                    temp_class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][class_to_change.day - 1] = False
                    temp_class_matrix[new_teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][class_to_change.day - 1] = True
                    mutated_class = Class(new_teacher, class_to_change.subject, class_to_change.classroom, class_to_change.hour, class_to_change.day)
                case 'classroom':
                    if len(self.problem_instance.subject_classroom[class_to_change.subject]) <= 1:
                        continue
                    new_classroom = random.choice(self.problem_instance.subject_classroom[class_to_change.subject])
                    if (new_classroom == class_to_change.classroom
                           or temp_class_matrix[:, :, new_classroom, class_to_change.hour, class_to_change.day - 1].any()):
                        continue

                    temp_class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][class_to_change.day - 1] = False
                    temp_class_matrix[class_to_change.teacher][class_to_change.subject][new_classroom][class_to_change.hour][class_to_change.day - 1] = True
                    mutated_class = Class(class_to_change.teacher, class_to_change.subject, new_classroom, class_to_change.hour, class_to_change.day)
                case 'hour':
                    new_hour = random.randint(0, self.problem_instance.time_slots_num - 1)
                    if (new_hour == class_to_change.hour
                            or temp_class_matrix[class_to_change.teacher, :, :, new_hour, class_to_change.day - 1].any()
                            or temp_class_matrix[:, :, class_to_change.classroom, new_hour, class_to_change.day - 1].any()):
                        continue
                    temp_class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][class_to_change.day - 1] = False
                    temp_class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][new_hour, class_to_change.day - 1] = True
                    mutated_class = Class(class_to_change.teacher, class_to_change.subject , class_to_change.classroom, new_hour, class_to_change.day)
                case 'day':
                    new_day = random.randint(1, 5)
                    if (new_day == class_to_change.day
                            or temp_class_matrix[class_to_change.teacher, :, :, class_to_change.hour, new_day - 1].any()
                            or temp_class_matrix[:, :, class_to_change.classroom, class_to_change.hour, new_day - 1].any()):
                            continue
                    temp_class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][class_to_change.day - 1] = False
                    temp_class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][new_day - 1] = True
                    mutated_class = Class(class_to_change.teacher, class_to_change.subject , class_to_change.classroom, class_to_change.hour, new_day)

            if mutated_class:
                temp_solution[idx_to_change] = mutated_class
                if validate_solution(temp_solution, self.problem_instance) == Validation.CORRECT and (accept_worse or self.problem_instance.cost_function(temp_solution) <= self.problem_instance.cost_function(current_solution)):
                    new_solutions.append(temp_solution)

        return new_solutions