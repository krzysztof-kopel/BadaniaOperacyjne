from enum import Enum
from collections import Counter
from typing import Any

from Class import Class
from ProblemInstance import ProblemInstance

class Validation(Enum):
    CORRECT = 0
    CLASSROOM_CONFLICT = 1
    TEACHER_CONFLICT = 2
    INCORRECT_DAY = 3
    INCORRECT_HOUR = 4
    INCORRECT_SUBJECT_COUNT = 5
    INCORRECT_TEACHER_SUBJECT = 6
    INCORRECT_CLASSROOM_SUBJECT = 7

def validate_solution(solution: list[Class], specification: ProblemInstance) -> tuple[Validation, Any, Any] | Validation:
    without_specs = validate_solution_without_specs(solution)
    if without_specs != Validation.CORRECT:
        return without_specs

    teacher_subject   = set((teacher,   subject) for teacher,   subjects in specification.teacher_subject.items()   for subject in subjects) 
    classroom_subject = set((classroom, subject) for classroom, subjects in specification.classroom_subject.items() for subject in subjects) 
    
    for class_unit in solution:
        if class_unit.hour < 0 or class_unit.hour >= specification.time_slots_num:
            return (Validation.INCORRECT_HOUR, (0, specification.time_slots_num - 1), class_unit)
        
        if (class_unit.teacher, class_unit.subject) not in teacher_subject:
            return (Validation.INCORRECT_TEACHER_SUBJECT, specification.teacher_subject[class_unit.teacher], class_unit)

        if (class_unit.classroom, class_unit.subject) not in classroom_subject:
            return (Validation.INCORRECT_CLASSROOM_SUBJECT, specification.classroom_subject[class_unit.classroom], class_unit)
        
    for subject, count in Counter(class_unit.subject for class_unit in solution).items():
        if count != specification.subject_hours[subject]:
            return (Validation.INCORRECT_SUBJECT_COUNT, specification.subject_hours[subject], (subject, count))

    return Validation.CORRECT
        
def validate_solution_without_specs(solution: list[Class]) -> tuple[Validation, Any, Any] | Validation:
    day_hour_classroom = {}
    day_hour_teacher = {}

    for class_unit in solution:
        if (class_unit.day, class_unit.hour, class_unit.classroom) in day_hour_classroom:
            return (Validation.CLASSROOM_CONFLICT, day_hour_classroom[(class_unit.day, class_unit.hour, class_unit.classroom)], class_unit)
        else:
            day_hour_classroom[(class_unit.day, class_unit.hour, class_unit.classroom)] = class_unit

        if (class_unit.day, class_unit.hour, class_unit.teacher) in day_hour_teacher:
            return (Validation.TEACHER_CONFLICT, day_hour_teacher[(class_unit.day, class_unit.hour, class_unit.teacher)], class_unit)
        else:
            day_hour_teacher[(class_unit.day, class_unit.hour, class_unit.teacher)] = class_unit
         
        if class_unit.day < 1 or class_unit.day > 5:
            return (Validation.INCORRECT_DAY, (1, 5), class_unit)

    return Validation.CORRECT
