# Badania Operacyjne

Jan Gawroński, Krzysztof Kopel, Witold Nieć, Jakub Szewczyk
---

Problem optymalizacyjny, rozwiązywany w ramach laboratoriów z przedmiotu "Badania Operacyjne" w semestrze letnim 25/26 - optymalizacja planu zajęć na uczelni.

---
Model matematyczny: [LINK](https://github.com/krzysztof-kopel/BadaniaOperacyjne/blob/main/model.pdf) 

---
## Uruchomienie interfejsu graficznego: 
Aplikacja graficzna wykorzystuje framework Streamlit, który uruchamia aplikację w przeglądarce. Do konfiguracji i uruchomienia programu wymagana jest biblioteka `uv` (menedżer projektów i zależności Pythona).

### System Windows

**Skrypt uruchomieniowy**

Aby uruchomić aplikację, wystarczy uruchomić plik `runWindows.cmd` (klikając plik dwukrotnie lub wykorzystując wiersz poleceń), znajdujący się w katalogu głównym projektu. Aplikacja uruchomi się w przeglądarce.

**Ręczne uruchomienie**

Najpierw należy w wierszu poleceń uruchomić następującą komendę w celu zsynchronizowania zależności projektu (ważne, aby znajdować się w katalogu głównym projektu):

```bash
C:\Users\User\Desktop\BadaniaOperacyjne> uv sync
```

Następnie, aby aplikacja uruchomiła się poprawnie, należy dodać katalog główny projektu do zmiennej środowiskowej `PYTHONPATH`:

```bash
set PYTHONPATH=%PYTHONPATH%;C:\Users\User\Desktop\BadaniaOperacyjne
```

Potem można już uruchomić aplikację:

```bash
C:\Users\User\Desktop\BadaniaOperacyjne> uv run streamlit run src/app.py
```

### System Linux / macOS

**Skrypt uruchomieniowy**

Aby uruchomić aplikację, wystarczy w terminalu wykonać:

```bash
~/BadaniaOperacyjne $ sh runBash.sh
```

Aplikacja uruchomi się automatycznie w przeglądarce.

**Ręczne uruchomienie**

Aby zsynchronizować zależności projektu (ważne, aby znajdować się w katalogu głównym projektu):

```bash
~/BadaniaOperacyjne $ uv sync
```

Następnie w celu uruchomienia aplikacji:

```bash
~/BadaniaOperacyjne $ PYTHONPATH=. uv run streamlit run src/app.py
```

Aplikacja powinna uruchomić się automatycznie w przeglądarce.

---
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
