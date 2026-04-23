from src.generator1 import Generator
from src.problem_instance import ProblemInstance

TEACHER_COUNT = 4
SUBJECT_COUNT = 8
TIME_SLOTS_COUNT = 6
CLASSROOM_COUNT = 5

problemInstance = ProblemInstance(TEACHER_COUNT, SUBJECT_COUNT, CLASSROOM_COUNT, TIME_SLOTS_COUNT)

for i in range(SUBJECT_COUNT):
    problemInstance.add_teacher_subject_pair(i // 2, i)
for i in range(2, SUBJECT_COUNT, 2):
    problemInstance.add_teacher_subject_pair(i//2 - 1, i)
    problemInstance.add_teacher_subject_pair(i//2, i - 1)
generator = Generator(problemInstance)

solution = generator.generateBaseSolution()
solution.sort(key=lambda x: 100 * x.day + x.hour)

print("Wygenerowany plan:")
for lesson in solution:
    print(lesson)