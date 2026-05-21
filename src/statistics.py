"""
Genetic Algorithm Statistics Dashboard — Timetable Scheduling
Compatible with Python 3.8+ and tkinter + matplotlib
Install deps: pip install matplotlib
"""

import tkinter as tk
from tkinter import ttk, font
import random
from collections import defaultdict

# ── optional matplotlib ──────────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# ── colour palette ────────────────────────────────────────────────────────────
BG        = "#0f1117"
PANEL     = "#1a1d27"
BORDER    = "#2a2d3e"
ACCENT    = "#5b8dee"
ACCENT2   = "#e05b7a"
ACCENT3   = "#5be0b3"
ACCENT4   = "#e0b85b"
TEXT      = "#e8eaf0"
TEXT_DIM  = "#6b6f85"
GREEN     = "#4caf7d"
RED       = "#e05b5b"
YELLOW    = "#e0c05b"


# ── solution file parser ──────────────────────────────────────────────────────
def parse_line(line: str):
    """
    Parse one line of the solutions file.
    Format per slot: day,hour,classroom,teacher,subject
    Returns list of dicts, one per slot.
    """
    slots = []
    for token in line.strip().split(";"):
        token = token.strip()
        if not token:
            continue
        parts = token.split(",")
        if len(parts) != 5:
            continue
        day, hour, classroom, teacher, subject = map(int, parts)
        slots.append({
            "day": day, "hour": hour,
            "classroom": classroom, "teacher": teacher, "subject": subject,
        })
    return slots


def analyse_schedule(slots, generation, history, pensum_target=6):
    """
    Derive all dashboard statistics from a raw list of slot dicts.
    pensum_target: expected hours per teacher per week (rough default).
    """
    # ── collision detection ───────────────────────────────────────────────────
    teacher_slots  = defaultdict(list)   # teacher  -> [(day,hour)]
    classroom_slots = defaultdict(list)  # classroom -> [(day,hour)]
    teacher_hours  = defaultdict(int)    # teacher  -> total hours
    teacher_days   = defaultdict(set)    # teacher  -> days worked

    for s in slots:
        key = (s["day"], s["hour"])
        teacher_slots[s["teacher"]].append(key)
        classroom_slots[s["classroom"]].append(key)
        teacher_hours[s["teacher"]] += 1
        teacher_days[s["teacher"]].add(s["day"])

    v_teacher_coll = sum(
        len(times) - len(set(times))
        for times in teacher_slots.values()
    )
    v_room_coll = sum(
        len(times) - len(set(times))
        for times in classroom_slots.values()
    )

    # ── pensum deviation (squared sum) ───────────────────────────────────────
    all_teachers = sorted(teacher_hours.keys())
    pensum_sq = sum((teacher_hours[t] - pensum_target) ** 2 for t in all_teachers)

    # ── free days (days with zero classes) ───────────────────────────────────
    ALL_DAYS = {1, 2, 3, 4, 5}
    total_free = sum(len(ALL_DAYS - teacher_days[t]) for t in all_teachers)

    # λ₁ is negative in the model; we store the raw free-day count as magnitude
    LAMBDA1 = -1.0
    fitness = pensum_sq + LAMBDA1 * total_free

    # ── diversity vs previous solution (Hamming on slot sets) ────────────────
    current_set = frozenset(
        (s["day"], s["hour"], s["classroom"], s["teacher"], s["subject"])
        for s in slots
    )
    prev_set = history.get("prev_slot_set", current_set)
    union = current_set | prev_set
    intersect = current_set & prev_set
    diversity = 1.0 - (len(intersect) / len(union)) if union else 0.0
    history["prev_slot_set"] = current_set

    # ── rolling best / mean / worst ──────────────────────────────────────────
    history.setdefault("all_fitness", [])
    history["all_fitness"].append(fitness)
    best  = min(history["all_fitness"])
    worst = max(history["all_fitness"])
    mean  = sum(history["all_fitness"]) / len(history["all_fitness"])

    # ── append to series ──────────────────────────────────────────────────────
    history.setdefault("best_history",    []);  history["best_history"].append(best)
    history.setdefault("mean_history",    []);  history["mean_history"].append(mean)
    history.setdefault("worst_history",   []);  history["worst_history"].append(worst)
    history.setdefault("pensum_history",  []);  history["pensum_history"].append(pensum_sq)
    history.setdefault("freeday_history", []);  history["freeday_history"].append(total_free)
    history.setdefault("diversity_history", []); history["diversity_history"].append(diversity)

    # ── stagnation counter ────────────────────────────────────────────────────
    if len(history["best_history"]) >= 2 and history["best_history"][-1] == history["best_history"][-2]:
        history["stagnation"] = history.get("stagnation", 0) + 1
    else:
        history["stagnation"] = 0

    # ── per-teacher stats ─────────────────────────────────────────────────────
    teachers_out = []
    for t in all_teachers:
        free_days = len(ALL_DAYS - teacher_days[t])
        dev = teacher_hours[t] - pensum_target
        t_coll = len(teacher_slots[t]) - len(set(teacher_slots[t]))
        teachers_out.append({
            "name": f"T{t}",
            "pensum_dev": dev,
            "free_days": free_days,
            "violations": t_coll,
        })

    total_v = v_teacher_coll + v_room_coll
    feasible_pct = 100 if total_v == 0 else max(0, 100 - total_v * 10)

    return {
        "generation": generation,
        "best": best, "mean": mean, "worst": worst,
        "pensum_term": pensum_sq, "freeday_term": total_free,
        "diversity": diversity, "feasible_pct": feasible_pct,
        "violations": {
            "Teacher-Subject":   0,          # not detectable without PT-S table
            "Room-Subject":      0,          # not detectable without PS-C table
            "Teacher Collision": v_teacher_coll,
            "Room Collision":    v_room_coll,
            "Subject Hours":     0,          # not detectable without r(s) table
        },
        "teachers": teachers_out,
        "stagnation": history["stagnation"],
    }


# ── file-backed ticker ────────────────────────────────────────────────────────
class FileGA:
    """
    Iterates through lines of a solutions file, one line = one tick.
    Each line: day,hour,classroom,teacher,subject;...;...
    """

    def __init__(self, filepath: str, pensum_target: int = 6):
        self.filepath = filepath
        self.pensum_target = pensum_target
        self.generation = 0
        self._lines = []
        self._idx = 0
        self._history = {}
        # series mirrors kept here for chart access
        self.best_fitness_history    = []
        self.mean_fitness_history    = []
        self.worst_fitness_history   = []
        self.pensum_history          = []
        self.freeday_history         = []
        self.diversity_history       = []
        self._load()

    def _load(self):
        with open(self.filepath, "r") as f:
            self._lines = [l for l in f if l.strip()]
        self._idx = 0
        self._history = {}
        self.generation = 0
        self.best_fitness_history    = []
        self.mean_fitness_history    = []
        self.worst_fitness_history   = []
        self.pensum_history          = []
        self.freeday_history         = []
        self.diversity_history       = []

    @property
    def exhausted(self):
        return self._idx >= len(self._lines)

    @property
    def total_lines(self):
        return len(self._lines)

    def tick(self):
        if self.exhausted:
            return None
        line = self._lines[self._idx]
        self._idx += 1
        self.generation += 1

        slots = parse_line(line)
        data  = analyse_schedule(slots, self.generation, self._history,
                                 pensum_target=self.pensum_target)

        # keep series on self so _update charts can read them
        self.best_fitness_history  = self._history["best_history"]
        self.mean_fitness_history  = self._history["mean_history"]
        self.worst_fitness_history = self._history["worst_history"]
        self.pensum_history        = self._history["pensum_history"]
        self.freeday_history       = self._history["freeday_history"]
        self.diversity_history     = self._history["diversity_history"]
        return data


# ── helper widgets ────────────────────────────────────────────────────────────
def make_card(parent, row, col, rowspan=1, colspan=1, title=""):
    frame = tk.Frame(parent, bg=PANEL, bd=0, highlightthickness=1,
                     highlightbackground=BORDER)
    frame.grid(row=row, column=col, rowspan=rowspan, columnspan=colspan,
               sticky="nsew", padx=5, pady=5)
    if title:
        tk.Label(frame, text=title.upper(), bg=PANEL, fg=TEXT_DIM,
                 font=("Courier New", 8, "bold"), anchor="w",
                 padx=10, pady=6).pack(fill="x")
        ttk.Separator(frame, orient="horizontal").pack(fill="x")
    return frame


def stat_label(parent, label, value, color=TEXT, row=0):
    f = tk.Frame(parent, bg=PANEL)
    f.pack(fill="x", padx=10, pady=2)
    tk.Label(f, text=label, bg=PANEL, fg=TEXT_DIM,
             font=("Courier New", 9), anchor="w").pack(side="left")
    lbl = tk.Label(f, text=value, bg=PANEL, fg=color,
                   font=("Courier New", 9, "bold"), anchor="e")
    lbl.pack(side="right")
    return lbl


def mini_bar(parent, value, max_value=1.0, color=ACCENT, height=6):
    """Thin horizontal progress bar drawn on a canvas."""
    c = tk.Canvas(parent, bg=PANEL, height=height, highlightthickness=0)
    c.pack(fill="x", padx=10, pady=1)
    def draw(v=value, m=max_value, col=color):
        c.delete("all")
        w = c.winfo_width() or 200
        pct = max(0, min(1, v / m)) if m else 0
        c.create_rectangle(0, 0, w, height, fill=BORDER, outline="")
        if pct > 0:
            c.create_rectangle(0, 0, int(w * pct), height, fill=col, outline="")
    c.bind("<Configure>", lambda e: draw())
    c._draw = draw
    return c


# ── main dashboard ────────────────────────────────────────────────────────────
class GADashboard(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("GA Statistics — Timetable Scheduling")
        self.configure(bg=BG)
        self.geometry("1200x780")
        self.minsize(900, 600)

        self.ga = None
        self.running = False
        self._after_id = None

        self._build_header()
        self._build_grid()
        self._build_status_bar()

    # ── layout ────────────────────────────────────────────────────────────────
    def _build_header(self):
        h = tk.Frame(self, bg=BG)
        h.pack(fill="x", padx=10, pady=(10, 0))

        tk.Label(h, text="GA STATISTICS", bg=BG, fg=TEXT,
                 font=("Courier New", 16, "bold")).pack(side="left")
        tk.Label(h, text="TIMETABLE SCHEDULING", bg=BG, fg=TEXT_DIM,
                 font=("Courier New", 10)).pack(side="left", padx=(10, 0))

        btn_frame = tk.Frame(h, bg=BG)
        btn_frame.pack(side="right")

        # ── file open ──
        tk.Button(btn_frame, text="OPEN FILE", command=self._open_file,
                  bg='#fff', fg=BG, relief="flat",
                  font=("Courier New", 9, "bold"),
                  padx=14, pady=5, cursor="hand2",
                  activebackground='#888', activeforeground=BG).pack(side="left", padx=4)

        self.btn_run = tk.Button(btn_frame, text="▶  RUN", command=self._toggle,
                                 bg=ACCENT, fg="white", relief="flat",
                                 font=("Courier New", 9, "bold"),
                                 padx=14, pady=5, cursor="hand2",
                                 activebackground=ACCENT, activeforeground="white",
                                 state="disabled")
        self.btn_run.pack(side="left", padx=4)

        tk.Button(btn_frame, text="↺  RESET", command=self._reset,
                  bg=BORDER, fg=TEXT, relief="flat",
                  font=("Courier New", 9), padx=14, pady=5, cursor="hand2",
                  activebackground=PANEL, activeforeground=TEXT).pack(side="left", padx=4)

        # ── pensum target ──
        tk.Label(btn_frame, text="PENSUM", bg=BG, fg=TEXT_DIM,
                 font=("Courier New", 8)).pack(side="left", padx=(12, 2))
        self.pensum_var = tk.IntVar(value=6)
        tk.Spinbox(btn_frame, from_=1, to=40, textvariable=self.pensum_var,
                   width=3, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                   relief="flat", font=("Courier New", 9),
                   buttonbackground=BORDER).pack(side="left", padx=(0, 8))

        # ── speed ──
        tk.Label(btn_frame, text="SPEED", bg=BG, fg=TEXT_DIM,
                 font=("Courier New", 8)).pack(side="left", padx=(4, 4))
        self.speed_var = tk.IntVar(value=300)
        sp = ttk.Scale(btn_frame, from_=50, to=1000, orient="horizontal",
                       variable=self.speed_var, length=100)
        sp.pack(side="left")

    def _build_grid(self):
        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        for c in range(4): container.columnconfigure(c, weight=1)
        for r in range(3): container.rowconfigure(r, weight=1)

        self._build_kpi_row(container)
        self._build_fitness_chart(container)
        self._build_violations_panel(container)
        self._build_objective_chart(container)
        self._build_teacher_panel(container)
        # self._build_diversity_panel(container)

    def _build_kpi_row(self, parent):
        kpis = [
            ("Funkcja kosztu (BEST)",   "0.00",  ACCENT,  "best_lbl"),
            ("Średnia funkcja kosztu (MEAN)",   "0.00",  TEXT,     "mean_lbl"),
            # ("FEASIBLE",       "0 %",   GREEN,    "feasible_lbl"),
            ("Pokolenie",     "0 pokolenie", YELLOW,   "stag_lbl"),
        ]
        for i, (title, val, color, attr) in enumerate(kpis):
            card = make_card(parent, 0, i, title=title)
            lbl = tk.Label(card, text=val, bg=PANEL, fg=color,
                           font=("Courier New", 20, "bold"))
            lbl.pack(expand=True, pady=(4, 10))
            setattr(self, attr, lbl)

    def _build_fitness_chart(self, parent):
        card = make_card(parent, 1, 0, colspan=2, title="Historia funkcji kosztu")
        if HAS_MPL:
            self.fig_fit = Figure(figsize=(1, 1), dpi=90, facecolor=PANEL)
            self.ax_fit  = self.fig_fit.add_subplot(111)
            self._style_ax(self.ax_fit)
            self.line_best,  = self.ax_fit.plot([], [], color=ACCENT,  lw=1.5, label="Best")
            self.line_mean,  = self.ax_fit.plot([], [], color=TEXT_DIM, lw=1,  label="Mean", ls="--")
            self.line_worst, = self.ax_fit.plot([], [], color=RED,     lw=1,   label="Worst", ls=":")
            self.ax_fit.legend(fontsize=7, facecolor=PANEL, edgecolor=BORDER,
                               labelcolor=TEXT, loc="upper right")
            self.canvas_fit = FigureCanvasTkAgg(self.fig_fit, master=card)
            self.canvas_fit.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        else:
            self._no_mpl_label(card)

    def _build_violations_panel(self, parent):
        card = make_card(parent, 1, 2, title="Kolizje")
        self.violation_labels = {}
        self.violation_bars   = {}
        vnames = ["Teacher-Subject", "Room-Subject", "Teacher Collision",
                  "Room Collision", "Subject Hours"]
        colors = [ACCENT, ACCENT3, ACCENT2, ACCENT4, RED]
        for vname, col in zip(vnames, colors):
            lbl = stat_label(card, vname, "0", color=col)
            bar = mini_bar(card, 0, max_value=10, color=col)
            self.violation_labels[vname] = lbl
            self.violation_bars[vname]   = bar

        tk.Frame(card, bg=PANEL, height=6).pack()
        self.total_v_lbl = stat_label(card, "TOTAL VIOLATIONS", "0", color=RED)

    def _build_objective_chart(self, parent):
        card = make_card(parent, 2, 2, title="Dekompozycja funkcji kosztu")
        if HAS_MPL:
            self.fig_obj = Figure(figsize=(1, 1), dpi=90, facecolor=PANEL)
            self.ax_obj  = self.fig_obj.add_subplot(111)
            self._style_ax(self.ax_obj)
            self.line_pensum,  = self.ax_obj.plot([], [], color=ACCENT2, lw=1.5, label="Pensum Δ²")
            self.line_freeday, = self.ax_obj.plot([], [], color=ACCENT3, lw=1.5, label="Dni wolne (λ)")
            self.ax_obj.legend(fontsize=7, facecolor=PANEL, edgecolor=BORDER,
                               labelcolor=TEXT, loc="upper right")
            self.canvas_obj = FigureCanvasTkAgg(self.fig_obj, master=card)
            self.canvas_obj.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        else:
            self._no_mpl_label(card)

    def _build_teacher_panel(self, parent):
        card = make_card(parent, 2, 0, colspan=2, title="Statystyki nauczycieli")

        cols = ("Nauczyciel", "Pensum Δ", "Dni wolne", "Kolizje")
        style = ttk.Style()
        style.theme_use("default")
        style.configure("GA.Treeview",
                        background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=22,
                        font=("Courier New", 9),
                        borderwidth=0)
        style.configure("GA.Treeview.Heading",
                        background=BORDER, foreground=TEXT_DIM,
                        font=("Courier New", 8, "bold"),
                        relief="flat")
        style.map("GA.Treeview", background=[("selected", ACCENT)])

        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                 style="GA.Treeview", height=5)
        widths = [80, 100, 100, 100]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        # tag colours
        self.tree.tag_configure("good",    foreground=GREEN)
        self.tree.tag_configure("bad",     foreground=RED)
        self.tree.tag_configure("neutral", foreground=TEXT)

    # def _build_diversity_panel(self, parent):
    #     card = make_card(parent, 2, 2, title="Population Health")

    #     self.diversity_lbl   = stat_label(card, "Diversity Index",   "0.00", ACCENT3)
    #     self.pop_collapse_lbl= stat_label(card, "Population Collapse","No",  GREEN)
    #     tk.Frame(card, bg=PANEL, height=4).pack()
    #     self.div_bar = mini_bar(card, 0, max_value=1.0, color=ACCENT3, height=8)

    #     ttk.Separator(card, orient="horizontal").pack(fill="x", pady=6)
    #     tk.Label(card, text="GENERATION COUNTER", bg=PANEL, fg=TEXT_DIM,
    #              font=("Courier New", 8, "bold"), padx=10).pack(anchor="w")
    #     self.gen_lbl = tk.Label(card, text="0", bg=PANEL, fg=ACCENT,
    #                             font=("Courier New", 28, "bold"))
    #     self.gen_lbl.pack(pady=(2, 8))

        # card2 = make_card(parent, 2, 3, title="Convergence")
        # if HAS_MPL:
        #     self.fig_div = Figure(figsize=(1, 1), dpi=90, facecolor=PANEL)
        #     self.ax_div  = self.fig_div.add_subplot(111)
        #     self._style_ax(self.ax_div)
        #     self.line_div, = self.ax_div.plot([], [], color=ACCENT3, lw=1.5, label="Diversity")
        #     self.ax_div.set_ylim(0, 1)
        #     self.ax_div.legend(fontsize=7, facecolor=PANEL, edgecolor=BORDER,
        #                        labelcolor=TEXT, loc="upper right")
        #     self.canvas_div = FigureCanvasTkAgg(self.fig_div, master=card2)
        #     self.canvas_div.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        # else:
        #     self._no_mpl_label(card2)

    def _build_status_bar(self):
        bar = tk.Frame(self, bg=BORDER, height=22)
        bar.pack(fill="x", side="bottom")
        self.status_lbl = tk.Label(bar, text="Ready.", bg=BORDER, fg=TEXT_DIM,
                                   font=("Courier New", 8), anchor="w", padx=8)
        self.status_lbl.pack(side="left")
        if not HAS_MPL:
            tk.Label(bar, text="⚠ matplotlib not found — charts disabled",
                     bg=BORDER, fg=YELLOW,
                     font=("Courier New", 8)).pack(side="right", padx=8)

    # ── update ────────────────────────────────────────────────────────────────
    def _update(self, data):
        gen = data["generation"]

        # KPIs
        self.best_lbl.config(text=f"{data['best']:.1f}")
        self.mean_lbl.config(text=f"{data['mean']:.1f}")
        # self.feasible_lbl.config(text=f"{data['feasible_pct']} %",
        #     fg=GREEN if data["feasible_pct"] > 60 else (YELLOW if data["feasible_pct"] > 30 else RED))
        self.stag_lbl.config(text=f"{data['stagnation']} pokolenie",
            fg=RED if data["stagnation"] > 20 else YELLOW if data["stagnation"] > 10 else GREEN)

        # Violations
        total_v = sum(data["violations"].values())
        for vname, count in data["violations"].items():
            self.violation_labels[vname].config(text=str(count))
            self.violation_bars[vname]._draw(count, max(10, count + 1))
        self.total_v_lbl.config(text=str(total_v),
            fg=GREEN if total_v == 0 else RED if total_v > 10 else YELLOW)

        # Teacher table
        for row in self.tree.get_children():
            self.tree.delete(row)
        for t in data["teachers"]:
            dev = t["pensum_dev"]
            tag = "good" if abs(dev) < 0.5 else ("bad" if abs(dev) > 2 else "neutral")
            self.tree.insert("", "end",
                values=(t["name"],
                        f"{dev:+.2f}",
                        t["free_days"],
                        t["violations"]),
                tags=(tag,))

        # Diversity
        # div = data["diversity"]
        # self.diversity_lbl.config(text=f"{div:.3f}")
        # self.pop_collapse_lbl.config(
        #     text="YES" if div < 0.05 else "No",
        #     fg=RED if div < 0.05 else GREEN)
        # self.div_bar._draw(div, 1.0)
        # self.gen_lbl.config(text=str(gen))

        # Charts
        if HAS_MPL:
            xs = list(range(1, gen + 1))
            ga = self.ga

            self.line_best.set_data(xs,  ga.best_fitness_history)
            self.line_mean.set_data(xs,  ga.mean_fitness_history)
            self.line_worst.set_data(xs, ga.worst_fitness_history)
            self.ax_fit.relim(); self.ax_fit.autoscale_view()
            self.canvas_fit.draw_idle()

            self.line_pensum.set_data(xs,  ga.pensum_history)
            self.line_freeday.set_data(xs, ga.freeday_history)
            self.ax_obj.relim(); self.ax_obj.autoscale_view()
            self.canvas_obj.draw_idle()

            # self.line_div.set_data(xs, ga.diversity_history)
            # self.ax_div.relim(); self.ax_div.autoscale_view()
            # self.canvas_div.draw_idle()

        self.status_lbl.config(
            text=f"Pokolenie {gen}  |  Best J = {data['best']:.2f}"
                 f"  |  Total violations = {total_v}")

    def _open_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Open solutions file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        self._stop()
        self.ga = FileGA(path, pensum_target=self.pensum_var.get())
        self.btn_run.config(state="normal")
        self.status_lbl.config(
            text=f"Loaded {self.ga.total_lines} solutions from {path}")
        self._first_tick()

    def _tick(self):
        if self.ga is None:
            return
        data = self.ga.tick()
        if data is None:
            self._stop()
            self.status_lbl.config(text="End of file — all solutions replayed.")
            return
        self._update(data)
        if self.running:
            delay = max(50, 1050 - self.speed_var.get())
            self._after_id = self.after(delay, self._tick)

    def _first_tick(self):
        if self.ga is None:
            return
        data = self.ga.tick()
        if data:
            self._update(data)

    def _stop(self):
        self.running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.btn_run.config(text="START", bg=ACCENT)

    def _toggle(self):
        if self.ga is None:
            return
        if self.running:
            self._stop()
        else:
            self.running = True
            self.btn_run.config(text="PAUZA", bg=ACCENT2)
            self._tick()

    def _reset(self):
        self._stop()
        if self.ga is None:
            return
        self.ga._load()
        self._first_tick()

    # ── helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _style_ax(ax):
        ax.set_facecolor(PANEL)
        ax.tick_params(colors=TEXT_DIM, labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        ax.xaxis.label.set_color(TEXT_DIM)
        ax.yaxis.label.set_color(TEXT_DIM)
        ax.grid(color=BORDER, linestyle="--", linewidth=0.5, alpha=0.6)

    @staticmethod
    def _no_mpl_label(parent):
        tk.Label(parent, text="Install matplotlib\nto see charts",
                 bg=PANEL, fg=TEXT_DIM,
                 font=("Courier New", 9)).pack(expand=True)


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = GADashboard()
    app.mainloop()