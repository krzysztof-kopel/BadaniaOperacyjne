import numpy as np
import random

from src.problem_instance import ProblemInstance, Class
from src.validator import validate_solution


class Solver:
    def __init__(self, initial_problem: ProblemInstance):
        self.problem_instance = initial_problem

    def optimize(self, initial_solution: list[Class], generations: int=10, children_num: int=5, accept_worse: bool=True) -> list[Class]:
        """
        Optymalizuje plan lekcji za pomocą algorytmu genetycznego.
        :param initial_solution: Początkowe rozwiązanie, które będzie ulepszane.
        :param generations: Liczba pokoleń do wygenerowania.
        :param children_num: Liczba nowych rozwiązań do wygenerowania w każdym pokoleniu.
        :param accept_worse: Czy akceptować rozwiązania o większej wartości funkcji kosztu?
        :return: Najlepsze znalezione rozwiązanie.
        """
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

        children_results = [(s, self.optimize(s, generations - 1, children_num, accept_worse)) for s in better_solutions]

        best_child_solution = min(children_results, key=lambda r: self.problem_instance.cost_function(r[1]))[1]
        if self.problem_instance.cost_function(best_child_solution) < self.problem_instance.cost_function(current_solution):
            current_solution = best_child_solution
            self.problem_instance.best_solution = current_solution
        return current_solution

    def get_next_generation(self, current_solution: list[Class], children_num: int, accept_worse: bool=True, class_matrix: np.ndarray | None = None) -> list[list[Class]]:
        """
        Generuje następne pokolenie w algorytmie genetycznym.
        :param current_solution: Obecne rozwiązanie, na podstawie którego generujemy nowe.
        :param children_num: Liczba nowych rozwiązań do wygenerowania.
        :param accept_worse: Czy zwracać rozwiązania o większej wartości funkcji kosztu?
        :param class_matrix: Opcjonalna macierz logiczna, która przyspieszy sprawdzanie, czy dana lekcja jest już w planie.
        :return: Lista nowych rozwiązań.
        """
        if class_matrix is None:
            class_matrix = np.zeros((self.problem_instance.teacher_num, self.problem_instance.subjects_num,
                                     self.problem_instance.classrooms_num, self.problem_instance.time_slots_num, 5),
                                    dtype=bool)
            for c in current_solution:
                class_matrix[c.teacher][c.subject][c.classroom][c.hour][c.day - 1] = True

        new_solutions = []
        iter_count = 0
        while len(new_solutions) < children_num and iter_count < 100:
            iter_count += 1
            new_solution = []

            class_to_change = random.choice(current_solution)
            element_to_change = random.choice(['teacher', 'classroom', 'hour', 'day'])

            match element_to_change:
                case 'teacher':
                    if len(self.problem_instance.subject_teacher[class_to_change.subject]) <= 1:
                        continue
                    new_teacher = random.choice(self.problem_instance.subject_teacher[class_to_change.subject])
                    if (new_teacher == class_to_change.teacher
                           or any(class_matrix[new_teacher, :, :, class_to_change.hour, class_to_change.day - 1])):
                        continue

                    class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][class_to_change.day - 1] = False
                    class_matrix[new_teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][class_to_change.day - 1] = True
                    new_solution = [c if c != class_to_change else Class(new_teacher, c.subject, c.classroom, c.hour, c.day) for c in current_solution]
                case 'classroom':
                    if len(self.problem_instance.subject_classroom[class_to_change.subject]) <= 1:
                        continue
                    new_classroom = random.choice(self.problem_instance.subject_classroom[class_to_change.subject])
                    if (new_classroom == class_to_change.classroom
                           or any(class_matrix[:, :, new_classroom, class_to_change.hour, class_to_change.day - 1])):
                        continue

                    class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][class_to_change.day - 1] = False
                    class_matrix[class_to_change.teacher][class_to_change.subject][new_classroom][class_to_change.hour][class_to_change.day - 1] = True
                    new_solution = [c if c != class_to_change else Class(c.teacher, c.subject, new_classroom, c.hour, c.day) for c in current_solution]
                case 'hour':
                    new_hour = random.randint(0, self.problem_instance.time_slots_num - 1)
                    if (new_hour == class_to_change.hour
                            or any(class_matrix[class_to_change.teacher, :, :, new_hour, class_to_change.day - 1])
                            or any(class_matrix[:, :, class_to_change.classroom, new_hour, class_to_change.day - 1])):
                        continue
                    class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][class_to_change.day - 1] = False
                    class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][new_hour, class_to_change.day - 1] = True
                    new_solution = [c if c != class_to_change else Class(c.teacher, c.subject , c.classroom, new_hour, c.day) for c in current_solution]
                case 'day':
                    new_day = random.randint(1, 5)
                    if (new_day == class_to_change.day
                            or any(class_matrix[class_to_change.teacher, :, :, class_to_change.hour, new_day - 1])
                            or any(class_matrix[:, :, class_to_change.classroom, class_to_change.hour, new_day - 1])):
                            continue
                    class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][class_to_change.day - 1] = False
                    class_matrix[class_to_change.teacher][class_to_change.subject][class_to_change.classroom][class_to_change.hour][new_day - 1] = True
                    new_solution = [c if c != class_to_change else Class(c.teacher, c.subject , c.classroom, c.hour, new_day) for c in current_solution]

            if accept_worse or self.problem_instance.cost_function(new_solution) <= self.problem_instance.cost_function(current_solution):
                new_solutions.append(new_solution)

        return new_solutions
