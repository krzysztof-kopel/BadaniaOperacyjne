from src import generators
from src.problem_instance import ProblemInstance
from src.solvers.genetic import GeneticSolver
from src.validator import validate_solution

teacher_num = 7
subjects_num = 5
classrooms_num = 5
time_slots_num = 5
pensum_list = [3, 3, 3, 3, 3, 3, 3]
subject_hours = [3, 2, 4, 2, 3]

problem_instance = ProblemInstance(
    teacher_num=teacher_num,
    subjects_num=subjects_num,
    classrooms_num=classrooms_num,
    time_slots_num=time_slots_num,
    pensum_list=pensum_list,
    subject_hours=subject_hours
)

# Nauczyciel 0
problem_instance.add_teacher_subject_pair(0, 0)
problem_instance.add_teacher_subject_pair(0, 1)
# Nauczyciel 1
problem_instance.add_teacher_subject_pair(1, 0)
problem_instance.add_teacher_subject_pair(1, 2)
# Nauczyciel 2
problem_instance.add_teacher_subject_pair(2, 1)
problem_instance.add_teacher_subject_pair(2, 3)
# Nauczyciel 3
problem_instance.add_teacher_subject_pair(3, 0)
problem_instance.add_teacher_subject_pair(3, 2)
problem_instance.add_teacher_subject_pair(3, 4)
# Nauczyciel 4
problem_instance.add_teacher_subject_pair(4, 1)
problem_instance.add_teacher_subject_pair(4, 3)
# Nauczyciel 5
problem_instance.add_teacher_subject_pair(5, 2)
problem_instance.add_teacher_subject_pair(5, 4)
# Nauczyciel 6
problem_instance.add_teacher_subject_pair(6, 0)
problem_instance.add_teacher_subject_pair(6, 1)
problem_instance.add_teacher_subject_pair(6, 2)
problem_instance.add_teacher_subject_pair(6, 3)
problem_instance.add_teacher_subject_pair(6, 4) # Nauczyciel 6 może uczyć wszystkiego

print("Generowanie początkowego rozwiązania...")
generator = generators.RandomGenerator(problem_instance)
initial_solution = generator.generate()

print("Początkowe rozwiązanie wygenerowane.")

solver = GeneticSolver(problem_instance)

print(f"Koszt początkowego rozwiązania: {problem_instance.cost_function(initial_solution)}")
print("Rozpoczynam optymalizację...")
optimized_solution = solver.optimize(initial_solution, generations=20, children_num=10, accept_worse=True, verbose=True)
print("Optymalizacja zakończona.")

print("\nZoptymalizowane rozwiązanie:")
for cls in optimized_solution:
    print(cls)
print(f"Koszt zoptymalizowanego rozwiązania: {problem_instance.cost_function(optimized_solution)}")

if not validate_solution(optimized_solution, problem_instance):
    print("Zoptymalizowane rozwiązanie jest niepoprawne!")
else:
    print("Zoptymalizowane rozwiązanie jest poprawne.")
