from abc import ABC, abstractmethod

from src.class_def import Class
from src.problem_instance import ProblemInstance


class Solver(ABC):
    def __init__(self, problem_instance: ProblemInstance):
        self.problem_instance = problem_instance

    @abstractmethod
    def solve(self) -> list[Class] | None:
        raise NotImplementedError

    def evaluate_solution(self, solution: list[Class]) -> float:
        return self.problem_instance.cost_function(solution)
