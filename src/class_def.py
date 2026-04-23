from typing import Literal

class Class:
    """
    Klasa reprezentująca pojedyncze zajęcia (połączenie nauczyciel-przedmiot-sala-godzina-dzień, małe "i" w naszym
    modelu).
    """
    def __init__(self, teacher: int, subject: int, classroom: int, hour: int, day: Literal[1, 2, 3, 4, 5]):
        self.teacher = teacher
        self.subject = subject
        self.classroom = classroom
        self.hour = hour
        self.day = day

    def __str__(self):
        return f""

    def __repr__(self):
        return f"Class(teacher={self.teacher}, subject={self.subject}, classroom={self.classroom}, hour={self.hour}, day={self.day})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Class):
            return NotImplemented
        return (self.teacher == other.teacher and
                self.subject == other.subject and
                self.classroom == other.classroom and
                self.hour == other.hour and
                self.day == other.day)

    def __hash__(self) -> int:
        return hash((self.teacher, self.subject, self.classroom, self.hour, self.day))
