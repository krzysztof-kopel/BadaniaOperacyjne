from src.class_def import Class


class ProblemInstance:
    def __init__(self, teacher_num: int, subjects_num: int, classrooms_num: int, time_slots_num: int,
                 lambda_1: int = -1, default_classrooms: bool = True, pensum_list: list[int] | None = None,
                 subject_hours: list[int] | None = None):
        """
        Konfiguracja najprostszych parametrów problemu.
        :param teacher_num: Liczba nauczycieli, numerujemy ich od 0 do teachers_num.
        :param subjects_num: Jak wyżej, ale dla przedmiotów.
        :param classrooms_num: Jak wyżej, ale dla klas.
        :param time_slots_num: Liczba slotów czasowych, np. 8:00 - 9:30 to 0, 9:45 - 11:15 to 1 itd.
        :param lambda_1: Parametr lambda_1 z naszego modelu.
        :param default_classrooms: True, jeśli domyślnie w każdej sali można uczyć każdego przedmiotu.
        :param pensum_list: Lista godzin, które nauczyciele mają przepracować w tygodniu.
        :param subject_hours: Lista godzin, które trzeba przeprowadzić dla każdego przedmiotu.
        """
        self.teacher_num = teacher_num
        self.subjects_num = subjects_num
        self.classrooms_num = classrooms_num
        self.time_slots_num = time_slots_num

        self.teacher_subject = {t: [] for t in range(teacher_num)}
        self.subject_teacher = {s: [] for s in range(subjects_num)}

        if default_classrooms:
            self.subject_classroom = {s: [c for c in range(classrooms_num)] for s in range(subjects_num)}
            self.classroom_subject = {c: [s for s in range(subjects_num)] for c in range(classrooms_num)}
        else:
            self.subject_classroom = {s: [] for s in range(subjects_num)}
            self.classroom_subject = {c: [] for c in range(classrooms_num)}

        if pensum_list is not None:
            self.teacher_pensum = pensum_list
        else:
            # Domyślnie 6 zajęć w tygodniu dla wszystkich
            self.teacher_pensum = [6] * teacher_num

        if subject_hours is not None:
            self.subject_hours = subject_hours
        else:
            # Domyślnie 1 godzina w tygodniu dla każdego przedmiotu
            self.subject_hours = [1] * subjects_num

        # Parametr lambda_1 z naszego modelu, na razie jakaś domyślna wartość
        self.lambda1 = lambda_1

        self.solutions: list[list[Class]] = []
        self.best_solution: list[Class] | None = None

    def add_teacher_subject_pair(self, teacher: int, subject: int) -> None:
        """
        Dodaje nauczycielowi możliwość uczenia przedmiotu.
        :param teacher: Nauczyciel, któremu pozwalamy uczyć.
        :param subject: Przedmiot, którego ten nauczyciel może uczyć.
        """
        if teacher < 0 or teacher >= self.teacher_num:
            raise ValueError(f"Teacher index {teacher} is out of bounds.")
        if subject < 0 or subject >= self.subjects_num:
            raise ValueError(f"Subject index {subject} is out of bounds.")
        self.teacher_subject[teacher].append(subject)
        self.subject_teacher[subject].append(teacher)

    def add_subject_classroom_pair(self, subject: int, classroom: int) -> None:
        """
        Dodaje przedmiotowi salę, w której można go uczyć.
        :param subject: Przedmiot, do którego dodajemy salę.
        :param classroom: Sala, którą dodajemy do przedmiotu
        """
        if subject < 0 or subject >= self.subjects_num:
            raise ValueError(f"Subject index {subject} is out of bounds.")
        if classroom < 0 or classroom >= self.classrooms_num:
            raise ValueError(f"Classroom index {classroom} is out of bounds.")
        self.subject_classroom[subject].append(classroom)
        self.classroom_subject[classroom].append(subject)

    def __str__(self):
        return f"ProblemInstance(teacher_num={self.teacher_num}, subjects_num={self.subjects_num}, classrooms_num={self.classrooms_num}, time_slots_num={self.time_slots_num})"
