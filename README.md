# Badania Operacyjne

Jan Gawroński, Krzysztof Kopel, Witold Nieć, Jakub Szewczyk
---

Problem optymalizacyjny, rozwiązywany w ramach laboratoriów z przedmiotu "Badania Operacyjne" w semestrze letnim 25/26 - optymalizacja planu zajęć na uczelni.

---
Model matematyczny: [LINK](https://github.com/krzysztof-kopel/BadaniaOperacyjne/blob/main/model.pdf) 

## Wizualizacja planu zajęć

Skrypt `schedule_visualizer.py` generuje czytelny podgląd planu w HTML na podstawie pliku z rozwiązaniami, gdzie jedna linia to jedno rozwiązanie.

Przykład (z `generator_test.py`):

```bash
python schedule_visualizer.py \
	--instance generator_test:make_bigger_instance \
	--solutions solutions/test \
	--line 1 \
	--output schedule.html
```

Opcje:
- `--line` wybiera konkretną linię (1‑indeksowane).
- `--random` losuje linię.
- `--output` ustawia nazwę pliku HTML.

## Wizualizacja nauczycieli (matplotlib)

Skrypt `teacher_timetable_plot.py` generuje wykresy planu dla nauczycieli, z kolorami odpowiadającymi przedmiotom.

Najprościej:

```bash
python teacher_timetable_plot.py
```

Wersja z pełnymi opcjami:

```bash
python teacher_timetable_plot.py \
	--instance generator_test:make_dense_instance \
	--solutions solutions/test \
	--line 1 \
	--output teachers.png \
	--open
```

Opcje:
- `--line` wybiera konkretną linię (1‑indeksowane).
- `--random` losuje linię.
- `--output` ustawia nazwę pliku wynikowego.
- `--open` otwiera plik po wygenerowaniu.
