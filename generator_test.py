from ProblemInstance import ProblemInstance
from solution_generator import main as generate

def make_bigger_instance() -> ProblemInstance:
    # Bigger but still easy-feasible:
    # 8 teachers, 10 subjects, 4 classrooms, 6 slots/day => 5*6 = 30 time slots per classroom
    # Total capacity = 4 classrooms * 30 = 120 class-meetings/week (way more than we need)
    inst = ProblemInstance(
        teacher_num=8,
        subjects_num=10,
        classrooms_num=4,
        time_slots_num=6,
        default_classrooms=True,
        pensum_list=[10, 10, 10, 10, 10, 10, 10, 10],             # not tight
        subject_hours=[4, 4, 3, 3, 2, 2, 2, 3, 4, 3]              # total = 30 classes
    )

    # Make sure every subject has multiple eligible teachers
    # t0: s0 s1 s2
    for s in [0, 1, 2]:
        inst.add_teacher_subject_pair(0, s)

    # t1: s0 s3 s4
    for s in [0, 3, 4]:
        inst.add_teacher_subject_pair(1, s)

    # t2: s1 s3 s5
    for s in [1, 3, 5]:
        inst.add_teacher_subject_pair(2, s)

    # t3: s2 s4 s6
    for s in [2, 4, 6]:
        inst.add_teacher_subject_pair(3, s)

    # t4: s5 s6 s7
    for s in [5, 6, 7]:
        inst.add_teacher_subject_pair(4, s)

    # t5: s7 s8 s9
    for s in [7, 8, 9]:
        inst.add_teacher_subject_pair(5, s)

    # t6: s0 s8 s9
    for s in [0, 8, 9]:
        inst.add_teacher_subject_pair(6, s)

    # t7: s1 s2 s8
    for s in [1, 2, 8]:
        inst.add_teacher_subject_pair(7, s)

    # Optional: room restrictions (kept mild so it's still easy)
    # Uncomment to test that part of the model too.
    # inst.subject_classroom = {s: [] for s in range(inst.subjects_num)}
    # inst.classroom_subject = {c: [] for c in range(inst.classrooms_num)}
    # inst.add_subject_classroom_pair(0, 0); inst.add_subject_classroom_pair(0, 1)
    # inst.add_subject_classroom_pair(1, 0); inst.add_subject_classroom_pair(1, 2)
    # inst.add_subject_classroom_pair(2, 1); inst.add_subject_classroom_pair(2, 3)
    # inst.add_subject_classroom_pair(3, 2); inst.add_subject_classroom_pair(3, 3)
    # inst.add_subject_classroom_pair(4, 0); inst.add_subject_classroom_pair(4, 3)
    # inst.add_subject_classroom_pair(5, 1); inst.add_subject_classroom_pair(5, 2)
    # inst.add_subject_classroom_pair(6, 0); inst.add_subject_classroom_pair(6, 2)
    # inst.add_subject_classroom_pair(7, 1); inst.add_subject_classroom_pair(7, 3)
    # inst.add_subject_classroom_pair(8, 2); inst.add_subject_classroom_pair(8, 3)
    # inst.add_subject_classroom_pair(9, 0); inst.add_subject_classroom_pair(9, 1)

    return inst


if __name__ == "__main__":
    inst = make_bigger_instance()
    print(inst)
    generate(inst, filename="solutions/test")