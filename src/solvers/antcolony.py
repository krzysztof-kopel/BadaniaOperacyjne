import random

from src.class_def import Class
from src.problem_instance import ProblemInstance
from src.solvers.solver import Solver
from src.validator import Validation, validate_solution


class AntColonySolver(Solver):
    def __init__(
        self,
        problem_instance: ProblemInstance,
        ant_count: int = 30,
        iterations: int = 80,
        alpha: float = 1.0,
        beta: float = 2.0,
        rho: float = 0.5,
        q: float = 1.0,
        tau0: float = 1.0,
        seed: int | None = None,
        min_pheromone: float = 1e-6,
    ):
        super().__init__(problem_instance)
        self.ant_count = ant_count
        self.iterations = iterations
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.q = q
        self.tau0 = tau0
        self.min_pheromone = min_pheromone
        self.rng = random.Random(seed)

        self._subject_slots = self._prepare_subject_slots()
        self._pheromone = self._init_pheromone()

    def solve(self) -> list[Class] | None:
        best_solution: list[Class] | None = None
        best_cost = float("inf")

        for _ in range(self.iterations):
            iteration_best: list[Class] | None = None
            iteration_best_cost = float("inf")

            for _ in range(self.ant_count):
                solution = self._build_solution()
                if solution is None:
                    continue

                validation = validate_solution(solution, self.problem_instance)
                if validation != Validation.CORRECT:
                    continue

                cost = self.evaluate_solution(solution)
                if cost < iteration_best_cost:
                    iteration_best_cost = cost
                    iteration_best = solution
                if cost < best_cost:
                    best_cost = cost
                    best_solution = solution

            self._evaporate_pheromone()
            if iteration_best is not None:
                self._deposit_pheromone(iteration_best, iteration_best_cost)

        if best_solution is not None:
            self.problem_instance.best_solution = best_solution
            self.problem_instance.solutions.append(best_solution)

        return best_solution

    def _prepare_subject_slots(self) -> dict[int, list[tuple[int, int, int, int]]]:
        slots: dict[int, list[tuple[int, int, int, int]]] = {}
        for subject in range(self.problem_instance.subjects_num):
            subject_slots: list[tuple[int, int, int, int]] = []
            for teacher in self.problem_instance.subject_teacher[subject]:
                for classroom in self.problem_instance.subject_classroom[subject]:
                    for day in range(1, 6):
                        for hour in range(self.problem_instance.time_slots_num):
                            subject_slots.append((teacher, classroom, day, hour))
            slots[subject] = subject_slots
        return slots

    def _init_pheromone(self) -> dict[tuple[int, int, int, int, int], float]:
        pheromone: dict[tuple[int, int, int, int, int], float] = {}
        for subject, slots in self._subject_slots.items():
            for teacher, classroom, day, hour in slots:
                pheromone[(teacher, subject, classroom, day, hour)] = self.tau0
        return pheromone

    def _build_solution(self) -> list[Class] | None:
        subjects_left = list(self.problem_instance.subject_hours)
        total_required = sum(subjects_left)

        teacher_slots = [
            [[True for _ in range(self.problem_instance.time_slots_num)] for _ in range(5)]
            for _ in range(self.problem_instance.teacher_num)
        ]
        classroom_slots = [
            [[True for _ in range(self.problem_instance.time_slots_num)] for _ in range(5)]
            for _ in range(self.problem_instance.classrooms_num)
        ]
        teacher_load = [0 for _ in range(self.problem_instance.teacher_num)]
        teacher_days = [set() for _ in range(self.problem_instance.teacher_num)]

        solution: list[Class] = []

        for _ in range(total_required):
            subject_options: dict[int, list[tuple[int, int, int, int]]] = {}
            min_options = None

            for subject, remaining in enumerate(subjects_left):
                if remaining <= 0:
                    continue

                options = []
                for teacher, classroom, day, hour in self._subject_slots[subject]:
                    day_idx = day - 1
                    if teacher_slots[teacher][day_idx][hour] and classroom_slots[classroom][day_idx][hour]:
                        options.append((teacher, classroom, day, hour))

                if not options:
                    return None

                subject_options[subject] = options
                if min_options is None or len(options) < min_options:
                    min_options = len(options)

            if not subject_options:
                return None

            constrained_subjects = [s for s, opts in subject_options.items() if len(opts) == min_options]
            subject = self.rng.choice(constrained_subjects)
            options = subject_options[subject]

            weights = []
            for teacher, classroom, day, hour in options:
                tau = self._pheromone[(teacher, subject, classroom, day, hour)]
                eta = self._heuristic(teacher, day, teacher_load, teacher_days)
                weights.append((tau ** self.alpha) * (eta ** self.beta))

            choice_index = self._roulette_select(weights)
            teacher, classroom, day, hour = options[choice_index]
            day_idx = day - 1

            teacher_slots[teacher][day_idx][hour] = False
            classroom_slots[classroom][day_idx][hour] = False
            teacher_load[teacher] += 1
            teacher_days[teacher].add(day)
            subjects_left[subject] -= 1
            solution.append(Class(teacher, subject, classroom, hour, day))

        return solution

    def _heuristic(
        self,
        teacher: int,
        day: int,
        teacher_load: list[int],
        teacher_days: list[set[int]],
    ) -> float:
        current_load = teacher_load[teacher]
        pensum = self.problem_instance.teacher_pensum[teacher]
        delta_sq = (current_load + 1 - pensum) ** 2 - (current_load - pensum) ** 2
        delta_free = -1 if day not in teacher_days[teacher] else 0
        delta = delta_sq + self.problem_instance.lambda1 * delta_free

        if delta <= 0:
            eta = 1.0 + (-delta)
        else:
            eta = 1.0 / (1.0 + delta)

        return max(eta, 1e-6)

    def _roulette_select(self, weights: list[float]) -> int:
        total = sum(weights)
        if total <= 0:
            return self.rng.randrange(len(weights))

        threshold = self.rng.random() * total
        cumulative = 0.0
        for idx, weight in enumerate(weights):
            cumulative += weight
            if cumulative >= threshold:
                return idx
        return len(weights) - 1

    def _evaporate_pheromone(self) -> None:
        for key in self._pheromone:
            self._pheromone[key] = max(self.min_pheromone, (1.0 - self.rho) * self._pheromone[key])

    def _deposit_pheromone(self, solution: list[Class], cost: float) -> None:
        min_cost_bound = min(
            0.0,
            self.problem_instance.lambda1 * 5 * self.problem_instance.teacher_num,
        )
        adjusted_cost = cost - min_cost_bound + 1.0
        deposit = self.q / adjusted_cost

        for class_unit in solution:
            key = (class_unit.teacher, class_unit.subject, class_unit.classroom, class_unit.day, class_unit.hour)
            self._pheromone[key] = max(self.min_pheromone, self._pheromone[key] + deposit)

