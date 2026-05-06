import tkinter as tk
from tkinter import ttk, messagebox
import copy

from src.model.process import Process
from src.scheduler.round_robin import round_robin
from src.scheduler.sjf import sjf
from src.metrics.calculations import calculate_metrics


# ================= THEME =================
BG          = "#1E1E2E"
PANEL_BG    = "#2A2A3E"
BORDER      = "#3A3A5C"
TEXT        = "#E0E0F0"
SUBTEXT     = "#9090B0"
ACCENT      = "#7C6AF7"
RR_COLOR    = "#4DA6FF"
SJF_COLOR   = "#5CD65C"
BTN_ADD     = "#4CAF82"
BTN_RUN     = "#5B8EF0"
BTN_BACK    = "#E0953A"
BTN_RESET   = "#D95F5F"
GANTT_BG    = "#12121E"

FONT_TITLE  = ("Segoe UI", 10, "bold")
FONT_LABEL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 9)
FONT_BTN    = ("Segoe UI", 9, "bold")


# ================= ROOT =================
root = tk.Tk()
root.title("CPU Scheduling Simulator  —  RR vs SJF")
root.geometry("1120x1050")
root.minsize(900, 700)
root.configure(bg=BG)


# ================= TTK STYLE =================
style = ttk.Style(root)
style.theme_use("clam")

style.configure("Vertical.TScrollbar",
    troughcolor=BG, background=BORDER, bordercolor=BG, arrowcolor=TEXT)

style.configure("Treeview",
    background=PANEL_BG, foreground=TEXT,
    fieldbackground=PANEL_BG, rowheight=26,
    borderwidth=0, font=FONT_MONO)
style.configure("Treeview.Heading",
    background=BORDER, foreground=TEXT,
    font=FONT_TITLE, relief="flat")
style.map("Treeview",
    background=[("selected", ACCENT)],
    foreground=[("selected", "#FFFFFF")])


# ================= HELPERS =================
def make_btn(parent, text, command, bg, width=14):
    return tk.Button(
        parent, text=text, command=command,
        bg=bg, fg="#FFFFFF", activebackground=bg,
        font=FONT_BTN, relief="flat", cursor="hand2",
        padx=10, pady=5, width=width,
        bd=0, highlightthickness=0,
    )


def make_label_frame(parent, title):
    return tk.LabelFrame(
        parent, text=f"  {title}  ",
        bg=PANEL_BG, fg=ACCENT,
        font=FONT_TITLE,
        bd=1, relief="solid",
    )


def make_entry(parent, width=12):
    return tk.Entry(
        parent, width=width,
        bg=GANTT_BG, fg=TEXT,
        insertbackground=TEXT,
        relief="flat", font=FONT_MONO,
        bd=4, highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
    )


# ================= SCROLL =================
outer = tk.Frame(root, bg=BG)
outer.pack(fill="both", expand=True)

main_canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
scrollbar   = ttk.Scrollbar(outer, orient="vertical",
                             command=main_canvas.yview,
                             style="Vertical.TScrollbar")

scrollable_frame = tk.Frame(main_canvas, bg=BG)
scrollable_frame.bind(
    "<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
)

main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
main_canvas.configure(yscrollcommand=scrollbar.set)
main_canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

def _on_mousewheel(event):
    main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
main_canvas.bind_all("<MouseWheel>", _on_mousewheel)


# ================= HEADER =================
header = tk.Frame(scrollable_frame, bg=PANEL_BG)
header.pack(fill="x", padx=14, pady=(14, 4))

tk.Label(header, text="CPU Scheduling Simulator",
         bg=PANEL_BG, fg=TEXT,
         font=("Segoe UI", 16, "bold")).pack(side="left", padx=12, pady=10)

tk.Label(header, text="Round Robin  vs  SJF",
         bg=PANEL_BG, fg=SUBTEXT,
         font=("Segoe UI", 11)).pack(side="left", pady=10)


process_list  = []
history_stack = []


# ================= UNDO HELPERS =================
def save_snapshot():
    history_stack.append({
        "process_list": copy.deepcopy(process_list),
        "tree_rows": [tree.item(r)["values"] for r in tree.get_children()],
    })
    update_step_back_btn()


def update_step_back_btn():
    btn_step_back.config(state="normal" if history_stack else "disabled")


# ================= INPUT PANEL =================
input_frame = make_label_frame(scrollable_frame, "Input Panel")
input_frame.pack(fill="x", padx=14, pady=(6,2))

for col, lbl in enumerate(["PID", "Arrival Time", "Burst Time", "Time Quantum"]):
    tk.Label(input_frame, text=lbl, bg=PANEL_BG, fg=SUBTEXT,
             font=FONT_LABEL).grid(row=0, column=col, padx=16, pady=(6, 2))

pid_entry     = make_entry(input_frame)
arrival_entry = make_entry(input_frame)
burst_entry   = make_entry(input_frame)
quantum_entry = make_entry(input_frame)

for col, e in enumerate([pid_entry, arrival_entry, burst_entry, quantum_entry]):
    e.grid(row=1, column=col, padx=16, pady=(2, 10))


# ================= ACTION BUTTONS =================
btn_frame = tk.Frame(scrollable_frame, bg=BG)
btn_frame.pack(pady=4)

make_btn(btn_frame, "+ Add Process",    lambda: add_process(), BTN_ADD,   16).pack(side="left", padx=8)
make_btn(btn_frame, "Run Simulation",   lambda: run(),         BTN_RUN,   16).pack(side="left", padx=8)

btn_step_back = make_btn(btn_frame, "< Step Back", lambda: step_back(), BTN_BACK, 13)
btn_step_back.pack(side="left", padx=8)
btn_step_back.config(state="disabled")

make_btn(btn_frame, "Reset", lambda: reset_all(), BTN_RESET, 10).pack(side="left", padx=8)


# ================= SCENARIO PRESETS =================
SCENARIOS = {
    "A": {
        "label": "A  Basic Mixed",
        "quantum": 3,
        "processes": [
            ("P1", 0, 8), ("P2", 1, 4), ("P3", 2, 9), ("P4", 3, 5),
        ],
        "description": (
            "Scenario A - Basic Mixed Workload\n"
            "A typical mix of short, medium, and long processes\n"
            "arriving at different times with quantum = 3.\n"
            "Useful for a general side-by-side comparison."
        ),
    },
    "B": {
        "label": "B  Short-Job Heavy",
        "quantum": 2,
        "processes": [
            ("P1", 0, 2), ("P2", 0, 3), ("P3", 1, 1), ("P4", 2, 3),
        ],
        "description": (
            "Scenario B - Short-Job Heavy\n"
            "All processes have small burst times.\n"
            "SJF excels here: minimal waiting, near-optimal TAT.\n"
            "RR with quantum=2 closely matches but adds context-switch overhead."
        ),
    },
    "C": {
        "label": "C  Fairness",
        "quantum": 4,
        "processes": [
            ("P1", 0, 12), ("P2", 0, 12),
            ("P3", 0, 12), ("P4", 0, 12),
        ],
        "description": (
            "Scenario C - Fairness Case\n"
            "Four equal-length processes all arriving at time 0.\n"
            "RR distributes CPU time evenly (quantum=4), giving every\n"
            "process the same response time. SJF behaves like FCFS here."
        ),
    },
    "D": {
        "label": "D  Long-Job Sensitivity",
        "quantum": 3,
        "processes": [
            ("P1", 0, 20), ("P2", 1, 3), ("P3", 2, 4), ("P4", 3, 2),
        ],
        "description": (
            "Scenario D - Long-Job Sensitivity\n"
            "One long process (burst=20) competes with three short ones.\n"
            "SJF prioritises the short jobs, potentially starving P1.\n"
            "RR keeps P1 making steady progress throughout execution."
        ),
    },
    "E": {
        "label": "E  Validation",
        "quantum": 0,
        "processes": [],
        "description": (
            "Scenario E - Validation Case\n"
            "Demonstrates input validation:\n"
            "  * Quantum = 0       -> rejected (must be > 0)\n"
            "  * Duplicate PID P1  -> rejected\n"
            "  * Non-digit arrival -> rejected\n"
            "  * Burst = 0         -> rejected (must be > 0)\n"
            "Each invalid entry triggers an error dialog."
        ),
    },
}

SCENARIO_COLORS = {
    "A": "#5B8EF0",
    "B": "#4CAF82",
    "C": "#9673C6",
    "D": "#D4943A",
    "E": "#D95F5F",
}


def _silent_reset():
    process_list.clear()
    history_stack.clear()
    tree.delete(*tree.get_children())
    rr_table.delete(*rr_table.get_children())
    sjf_table.delete(*sjf_table.get_children())
    avg_table.delete(*avg_table.get_children())
    canvas_rr.delete("all")
    canvas_sjf.delete("all")
    ready_queue.delete(0, tk.END)
    queue_status.config(text="Waiting for simulation...", fg=SUBTEXT)
    summary.delete("1.0", tk.END)
    for e in [pid_entry, arrival_entry, burst_entry, quantum_entry]:
        e.delete(0, tk.END)
    update_step_back_btn()


def load_scenario(key):
    scenario = SCENARIOS[key]
    _silent_reset()
    quantum_entry.insert(0, str(scenario["quantum"]))

    if key == "E":
        summary.insert(tk.END, scenario["description"] + "\n\nAttempting to add invalid inputs...\n")
        for pid, at, bt in [("P1","0","5"), ("P1","1","3"), ("P2","abc","4"), ("P3","2","0")]:
            pid_entry.delete(0, tk.END);     pid_entry.insert(0, pid)
            arrival_entry.delete(0, tk.END); arrival_entry.insert(0, at)
            burst_entry.delete(0, tk.END);   burst_entry.insert(0, bt)
            root.update()
            add_process()
        run()
        return

    for pid, at, bt in scenario["processes"]:
        process_list.append(Process(pid, at, bt))
        tree.insert("", "end", values=(pid, at, bt))

    summary.insert(tk.END, scenario["description"] + "\n\n")
    run()


# Scenario buttons — compact size to save vertical space
scenario_frame = tk.Frame(scrollable_frame, bg=BG)
scenario_frame.pack(fill="x", padx=14, pady=(4, 2))

tk.Label(scenario_frame, text="Quick Scenarios:",
         bg=BG, fg=SUBTEXT, font=("Segoe UI", 8)).pack(side="left", padx=(0, 6))

for _key, _sc in SCENARIOS.items():
    short_label = _sc["label"].split()[0]
    full_label  = _sc["label"]
    tk.Button(
        scenario_frame,
        text=full_label,
        bg=SCENARIO_COLORS[_key], fg="white",
        activebackground=SCENARIO_COLORS[_key],
        font=("Segoe UI", 8), relief="flat", cursor="hand2",
        padx=8, pady=3, bd=0, highlightthickness=0,
        command=lambda k=_key: load_scenario(k),
    ).pack(side="left", padx=3, pady=3)


# ================= PROCESS TABLE =================
table_frame = make_label_frame(scrollable_frame, "Process Table")
table_frame.pack(fill="x", padx=14, pady=6)

tree = ttk.Treeview(table_frame, columns=("PID", "Arrival", "Burst"),
                    show="headings", height=4)
for c in ("PID", "Arrival", "Burst"):
    tree.heading(c, text=c)
    tree.column(c, anchor="center", width=140)
tree.pack(fill="x", padx=6, pady=6)


# ================= READY QUEUE =================
rq_frame = make_label_frame(scrollable_frame, "Ready Queue  (RR Step View)")
rq_frame.pack(fill="x", padx=14, pady=6)

rq_inner = tk.Frame(rq_frame, bg=PANEL_BG)
rq_inner.pack(fill="x")

ready_queue = tk.Listbox(
    rq_inner, height=4,
    bg=GANTT_BG, fg=TEXT,
    selectbackground=ACCENT,
    font=FONT_MONO, relief="flat", bd=0,
    highlightthickness=0,
)
rq_sb = ttk.Scrollbar(rq_inner, orient="vertical",
                       command=ready_queue.yview,
                       style="Vertical.TScrollbar")
ready_queue.configure(yscrollcommand=rq_sb.set)
ready_queue.pack(side="left", fill="x", expand=True, padx=(6, 0), pady=6)
rq_sb.pack(side="right", fill="y", pady=6)

queue_status = tk.Label(rq_frame, text="Waiting for simulation...",
                         bg=PANEL_BG, fg=SUBTEXT, font=FONT_LABEL)
queue_status.pack(anchor="w", padx=6, pady=(0, 6))


# ================= GANTT CHARTS =================
gantt_frame = make_label_frame(scrollable_frame, "Gantt Charts")
gantt_frame.pack(fill="x", padx=14, pady=6)

# Round Robin
tk.Label(gantt_frame, text="Round Robin",
         bg=PANEL_BG, fg=RR_COLOR, font=FONT_TITLE).pack(anchor="w", padx=8, pady=(4, 0))

rr_gantt_wrap = tk.Frame(gantt_frame, bg=GANTT_BG)
rr_gantt_wrap.pack(fill="x", padx=6, pady=(2, 10))

canvas_rr = tk.Canvas(rr_gantt_wrap, height=120, bg=GANTT_BG, highlightthickness=0)
rr_hscroll = ttk.Scrollbar(rr_gantt_wrap, orient="horizontal", command=canvas_rr.xview)
canvas_rr.configure(xscrollcommand=rr_hscroll.set)
canvas_rr.pack(fill="x", expand=True)
rr_hscroll.pack(fill="x")

# SJF
tk.Label(gantt_frame, text="SJF  (Shortest Job First)",
         bg=PANEL_BG, fg=SJF_COLOR, font=FONT_TITLE).pack(anchor="w", padx=8)

sjf_gantt_wrap = tk.Frame(gantt_frame, bg=GANTT_BG)
sjf_gantt_wrap.pack(fill="x", padx=6, pady=(2, 6))

canvas_sjf = tk.Canvas(sjf_gantt_wrap, height=120, bg=GANTT_BG, highlightthickness=0)
sjf_hscroll = ttk.Scrollbar(sjf_gantt_wrap, orient="horizontal", command=canvas_sjf.xview)
canvas_sjf.configure(xscrollcommand=sjf_hscroll.set)
canvas_sjf.pack(fill="x", expand=True)
sjf_hscroll.pack(fill="x")


# ================= METRICS (side by side) =================
metrics_outer = tk.Frame(scrollable_frame, bg=BG)
metrics_outer.pack(fill="x", padx=14, pady=6)

rr_frame = make_label_frame(metrics_outer, "RR Metrics")
rr_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

rr_table = ttk.Treeview(rr_frame, columns=("PID", "WT", "TAT", "RT"),
                         show="headings", height=4)
for c in ("PID", "WT", "TAT", "RT"):
    rr_table.heading(c, text=c)
    rr_table.column(c, anchor="center")
rr_table.pack(fill="both", expand=True, padx=6, pady=6)

sjf_frame = make_label_frame(metrics_outer, "SJF Metrics")
sjf_frame.pack(side="left", fill="both", expand=True, padx=(6, 0))

sjf_table = ttk.Treeview(sjf_frame, columns=("PID", "WT", "TAT", "RT"),
                          show="headings", height=4)
for c in ("PID", "WT", "TAT", "RT"):
    sjf_table.heading(c, text=c)
    sjf_table.column(c, anchor="center")
sjf_table.pack(fill="both", expand=True, padx=6, pady=6)


# ================= AVERAGE COMPARISON =================
avg_frame = make_label_frame(scrollable_frame, "Average Metrics Comparison")
avg_frame.pack(fill="x", padx=14, pady=6)

avg_table = ttk.Treeview(avg_frame,
    columns=("Algorithm", "Avg WT", "Avg TAT", "Avg RT"),
    show="headings", height=2)
for c in ("Algorithm", "Avg WT", "Avg TAT", "Avg RT"):
    avg_table.heading(c, text=c)
    avg_table.column(c, anchor="center")
avg_table.pack(fill="x", padx=6, pady=6)


# ================= FINAL ANALYSIS =================
summary_frame = make_label_frame(scrollable_frame, "Final Analysis")
summary_frame.pack(fill="both", expand=True, padx=14, pady=(6, 14))

summary = tk.Text(
    summary_frame, height=14,
    bg=GANTT_BG, fg=TEXT,
    insertbackground=TEXT,
    font=FONT_MONO, relief="flat", bd=0,
    highlightthickness=0,
    padx=12, pady=10,
)
summary.pack(fill="both", expand=True, padx=6, pady=6)


# ================= ADD PROCESS =================
def add_process():
    pid = pid_entry.get().strip()
    at  = arrival_entry.get().strip()
    bt  = burst_entry.get().strip()

    if not pid or not at or not bt:
        messagebox.showerror("Error", "All fields are required.")
        return
    if not at.isdigit() or not bt.isdigit():
        messagebox.showerror("Error", "Arrival & Burst must be non-negative integers.")
        return

    at = int(at)
    bt = int(bt)

    if at < 0 or bt <= 0:
        messagebox.showerror("Error", "Arrival must be >= 0 and Burst must be > 0.")
        return
    for p in process_list:
        if p.pid == pid:
            messagebox.showerror("Error", f"Duplicate PID '{pid}' is not allowed.")
            return

    save_snapshot()
    process_list.append(Process(pid, at, bt))
    tree.insert("", "end", values=(pid, at, bt))

    pid_entry.delete(0, tk.END)
    arrival_entry.delete(0, tk.END)
    burst_entry.delete(0, tk.END)


# ================= STEP BACK =================
def step_back():
    if not history_stack:
        messagebox.showinfo("Step Back", "No previous state to go back to.")
        return
    snapshot = history_stack.pop()
    process_list.clear()
    process_list.extend(snapshot["process_list"])
    tree.delete(*tree.get_children())
    for row in snapshot["tree_rows"]:
        tree.insert("", "end", values=row)
    update_step_back_btn()


# ================= RESET =================
def reset_all():
    if not messagebox.askyesno("Reset", "Clear all data and results?"):
        return
    _silent_reset()


# ================= DRAW GANTT =================
def draw(canvas, gantt, algo):
    canvas.delete("all")
    if not gantt:
        return

    canvas.update_idletasks()
    total_time   = gantt[-1][2]
    MARGIN       = 30
    PX_PER_UNIT  = 50

    total_draw_w = int(total_time * PX_PER_UNIT) + MARGIN
    canvas.configure(scrollregion=(0, 0, total_draw_w, 120))

    x = 10
    for pid, start, end in gantt:
        w     = (end - start) * PX_PER_UNIT
        color = RR_COLOR if algo == "RR" else SJF_COLOR

        canvas.create_rectangle(x, 12, x + w, 62,
                                 fill=color, outline=GANTT_BG, width=2)
        if w > 20:
            canvas.create_text(x + w / 2, 37, text=pid,
                                fill="#FFFFFF", font=FONT_TITLE)

        canvas.create_text(x,     76, text=str(start),
                            fill=SUBTEXT, font=("Segoe UI", 8))
        canvas.create_text(x + w, 76, text=str(end),
                            fill=SUBTEXT, font=("Segoe UI", 8))
        x += w


# ================= RUN =================
def run():
    q = quantum_entry.get().strip()
    if not q.isdigit() or int(q) <= 0:
        messagebox.showerror("Error", "Time Quantum must be a positive integer.")
        return
    if not process_list:
        messagebox.showerror("Error", "No processes added yet.")
        return

    quantum  = int(q)
    rr       = copy.deepcopy(process_list)
    sjf_list = copy.deepcopy(process_list)

    for p in rr + sjf_list:
        p.remaining     = p.burst
        p.response_time = None
        p.finish_time   = None
        p.started       = False

    rr_gantt,  rr_states = round_robin(rr, quantum)
    sjf_gantt             = sjf(sjf_list)

    root.after(50, lambda: draw(canvas_rr,  rr_gantt,  "RR"))
    root.after(50, lambda: draw(canvas_sjf, sjf_gantt, "SJF"))

    ready_queue.delete(0, tk.END)
    if rr_states:
        queue_status.config(text="RR Execution Steps Loaded", fg=SJF_COLOR)
        for i, state in enumerate(rr_states, 1):
            ready_queue.insert(tk.END, f"  Step {i:>3}:  {state}")
    else:
        queue_status.config(text="No RR states returned.", fg=BTN_RESET)

    rr_table.delete(*rr_table.get_children())
    for p in rr:
        tat = p.finish_time - p.arrival
        wt  = tat - p.burst
        rt  = p.response_time if p.response_time is not None else 0
        rr_table.insert("", "end", values=(p.pid, wt, tat, rt))

    sjf_table.delete(*sjf_table.get_children())
    for p in sjf_list:
        tat = p.finish_time - p.arrival
        wt  = tat - p.burst
        rt  = p.response_time if p.response_time is not None else 0
        sjf_table.insert("", "end", values=(p.pid, wt, tat, rt))

    avg_table.delete(*avg_table.get_children())
    rr_m  = calculate_metrics(rr)
    sjf_m = calculate_metrics(sjf_list)
    avg_table.insert("", "end", values=("Round Robin",
        round(rr_m["avg_wt"],  2),
        round(rr_m["avg_tat"], 2),
        round(rr_m["avg_rt"],  2)))
    avg_table.insert("", "end", values=("SJF",
        round(sjf_m["avg_wt"],  2),
        round(sjf_m["avg_tat"], 2),
        round(sjf_m["avg_rt"],  2)))

    summary.delete("1.0", tk.END)
    summary.insert(tk.END, f"""\
================ FINAL ANALYSIS ================

Average Metrics:
  WT   ->  RR = {rr_m['avg_wt']:.2f}   |   SJF = {sjf_m['avg_wt']:.2f}
  TAT  ->  RR = {rr_m['avg_tat']:.2f}   |   SJF = {sjf_m['avg_tat']:.2f}
  RT   ->  RR = {rr_m['avg_rt']:.2f}   |   SJF = {sjf_m['avg_rt']:.2f}

---------------- Comparison ----------------

  Fairness vs Efficiency:
    RR  -> fair time-sharing; every process gets CPU turns.
    SJF -> efficient; shortest jobs finish first.

  CPU Distribution:
    RR  -> rotates using quantum = {quantum}.
    SJF -> always picks the shortest available job.

  Quantum Effect (RR):
    Small quantum -> better responsiveness, more context switches.
    Large quantum -> behaves like FCFS.

  Response Time:
    RR  -> generally better first-response time.
    SJF -> may delay long processes significantly.

  Starvation Risk:
    RR  -> none; long jobs always make progress.
    SJF -> possible if short jobs keep arriving.

---------------- Result ----------------

  Better Avg WT   ->  {'Round Robin' if rr_m['avg_wt']  < sjf_m['avg_wt']  else 'SJF'}
  Better Avg TAT  ->  {'Round Robin' if rr_m['avg_tat'] < sjf_m['avg_tat'] else 'SJF'}
  Better Avg RT   ->  {'Round Robin' if rr_m['avg_rt']  < sjf_m['avg_rt']  else 'SJF'}

  Quantum = {quantum}

================================================
""")


root.mainloop()
