import pulp

from src.class_def import Class
from src.problem_instance import ProblemInstance
from src.solvers.solver import Solver
from src.validator import Validation, validate_solution


class LinearProgrammingSolver(Solver):
    def __init__(
        self,
        problem_instance: ProblemInstance,
        solver: pulp.LpSolver | None = None,
        time_limit: int | None = None,
    ):
        super().__init__(problem_instance)
        self.solver = solver
        self.time_limit = time_limit

    def solve(self) -> list[Class] | None:
        instance = self.problem_instance
        days = range(1, 6)
        hours = range(instance.time_slots_num)
        subjects = range(instance.subjects_num)
        teachers = range(instance.teacher_num)
        classrooms = range(instance.classrooms_num)

        x: dict[tuple[int, int, int, int, int], pulp.LpVariable] = {}
        for subject in subjects:
            if not instance.subject_teacher[subject] or not instance.subject_classroom[subject]:
                return None
            for teacher in instance.subject_teacher[subject]:
                for classroom in instance.subject_classroom[subject]:
                    for day in days:
                        for hour in hours:
                            name = f"i_t{teacher}_s{subject}_c{classroom}_d{day}_h{hour}"
                            x[(teacher, subject, classroom, day, hour)] = pulp.LpVariable(
                                name,
                                cat=pulp.LpBinary,
                            )

        if not x:
            return None

        model = pulp.LpProblem("Schedule_Optimization", pulp.LpMinimize)

        for subject in subjects:
            model += (
                pulp.lpSum(
                    var
                    for (teacher, s, classroom, day, hour), var in x.items()
                    if s == subject
                )
                == instance.subject_hours[subject]
            )

        for teacher in teachers:
            for day in days:
                for hour in hours:
                    model += (
                        pulp.lpSum(
                            var
                            for (t, s, classroom, d, h), var in x.items()
                            if t == teacher and d == day and h == hour
                        )
                        <= 1
                    )

        for classroom in classrooms:
            for day in days:
                for hour in hours:
                    model += (
                        pulp.lpSum(
                            var
                            for (teacher, s, c, d, h), var in x.items()
                            if c == classroom and d == day and h == hour
                        )
                        <= 1
                    )

        day_active = {
            (teacher, day): pulp.LpVariable(
                f"day_active_t{teacher}_d{day}",
                cat=pulp.LpBinary,
            )
            for teacher in teachers
            for day in days
        }
        free_day = {
            (teacher, day): pulp.LpVariable(
                f"free_day_t{teacher}_d{day}",
                cat=pulp.LpBinary,
            )
            for teacher in teachers
            for day in days
        }

        for teacher in teachers:
            for day in days:
                day_load = pulp.lpSum(
                    var
                    for (t, s, classroom, d, h), var in x.items()
                    if t == teacher and d == day
                )
                model += day_load <= instance.time_slots_num * day_active[(teacher, day)]
                model += day_load >= day_active[(teacher, day)]
                model += free_day[(teacher, day)] + day_active[(teacher, day)] == 1

        total_required = sum(instance.subject_hours)
        teacher_load = {
            teacher: pulp.LpVariable(
                f"w_t{teacher}",
                lowBound=0,
                upBound=total_required,
                cat=pulp.LpInteger,
            )
            for teacher in teachers
        }

        for teacher in teachers:
            model += (
                teacher_load[teacher]
                == pulp.lpSum(
                    var
                    for (t, s, classroom, d, h), var in x.items()
                    if t == teacher
                )
            )

        load_choice = {
            (teacher, load): pulp.LpVariable(
                f"load_t{teacher}_k{load}",
                cat=pulp.LpBinary,
            )
            for teacher in teachers
            for load in range(total_required + 1)
        }

        for teacher in teachers:
            model += (
                pulp.lpSum(load_choice[(teacher, load)] for load in range(total_required + 1))
                == 1
            )
            model += (
                teacher_load[teacher]
                == pulp.lpSum(load * load_choice[(teacher, load)] for load in range(total_required + 1))
            )

        model += (
            pulp.lpSum(
                ((load - instance.teacher_pensum[teacher]) ** 2) * load_choice[(teacher, load)]
                for teacher in teachers
                for load in range(total_required + 1)
            )
            + instance.lambda1
            * pulp.lpSum(free_day[(teacher, day)] for teacher in teachers for day in days)
        )

        solver = self.solver
        if solver is None:
            solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=self.time_limit)

        status = model.solve(solver)
        if pulp.LpStatus[status] != "Optimal":
            return None

        solution = [
            Class(teacher, subject, classroom, hour, day)
            for (teacher, subject, classroom, day, hour), var in x.items()
            if (var.value() or 0) > 0.5
        ]

        validation = validate_solution(solution, instance)
        if validation != Validation.CORRECT:
            return None

        instance.best_solution = solution
        instance.solutions.append(solution)
        return solution
