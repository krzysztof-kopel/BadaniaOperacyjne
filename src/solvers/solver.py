from abc import ABC, abstractmethod

from src.class_def import Class
from src.evaluator import evaluate_solution
from src.problem_instance import ProblemInstance


class Solver(ABC):
    def __init__(self, problem_instance: ProblemInstance):
        self.problem_instance = problem_instance

    @abstractmethod
    def solve(self) -> list[Class] | None:
        raise NotImplementedError

    def evaluate_solution(self, solution: list[Class]) -> float:
        return evaluate_solution(solution, self.problem_instance)
