from src.class_def import Class
from src.problem_instance import ProblemInstance

def evaluate_solution(solution: list[Class], problem_instance: ProblemInstance) -> float:
    teacher_load = [0 for _ in range(problem_instance.teacher_num)]
    teacher_days = [set() for _ in range(problem_instance.teacher_num)]

    for class_unit in solution:
        teacher_load[class_unit.teacher] += 1
        teacher_days[class_unit.teacher].add(class_unit.day)

    cost = 0.0
    for teacher in range(problem_instance.teacher_num):
        load = teacher_load[teacher]
        pensum = problem_instance.teacher_pensum[teacher]
        cost += (load - pensum) ** 2
        free_days = 5 - len(teacher_days[teacher])
        cost += problem_instance.lambda1 * free_days
        
    return cost

