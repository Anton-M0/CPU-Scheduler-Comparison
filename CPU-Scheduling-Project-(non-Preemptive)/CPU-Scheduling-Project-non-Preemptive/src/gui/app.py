import tkinter as tk
from tkinter import ttk, messagebox
import copy

from src.model.process import Process
from src.scheduler.round_robin import round_robin
from src.scheduler.sjf import sjf
from src.metrics.calculations import calculate_metrics


# ================= THEME =================
# Color palette for the dark-themed UI
BG          = "#1E1E2E"   # Main window background
PANEL_BG    = "#2A2A3E"   # Panel / LabelFrame background
BORDER      = "#3A3A5C"   # Border and heading color
TEXT        = "#E0E0F0"   # Primary text color
SUBTEXT     = "#9090B0"   # Secondary / muted text color
ACCENT      = "#7C6AF7"   # Highlight / selection color
RR_COLOR    = "#4DA6FF"   # Color used for Round Robin elements
SJF_COLOR   = "#5CD65C"   # Color used for SJF elements
BTN_ADD     = "#4CAF82"   # "Add Process" button color
BTN_RUN     = "#5B8EF0"   # "Run Simulation" button color
BTN_BACK    = "#E0953A"   # "Step Back" button color
BTN_RESET   = "#D95F5F"   # "Reset" button color
GANTT_BG    = "#12121E"   # Gantt chart / text area background

# Font definitions reused throughout the UI
FONT_TITLE  = ("Segoe UI", 10, "bold")
FONT_LABEL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 9)
FONT_BTN    = ("Segoe UI", 9, "bold")


# ================= ROOT =================
# Create and configure the main application window
root = tk.Tk()
root.title("CPU Scheduling Simulator  —  RR vs SJF")
root.geometry("1120x1050")
root.minsize(900, 700)
root.configure(bg=BG)


# ================= TTK STYLE =================
# Apply a unified dark "clam" theme to all ttk widgets
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
    """
    Create and return a styled flat tk.Button.

    Parameters
    ----------
    parent  : tk widget  – the container that will hold the button.
    text    : str        – label displayed on the button.
    command : callable   – function called when the button is clicked.
    bg      : str        – background hex color of the button.
    width   : int        – character width of the button (default 14).

    Returns
    -------
    tk.Button
    """
    return tk.Button(
        parent, text=text, command=command,
        bg=bg, fg="#FFFFFF", activebackground=bg,
        font=FONT_BTN, relief="flat", cursor="hand2",
        padx=10, pady=5, width=width,
        bd=0, highlightthickness=0,
    )


def make_label_frame(parent, title):
    """
    Create and return a styled tk.LabelFrame used as a section container.

    Parameters
    ----------
    parent : tk widget – the container that will hold the frame.
    title  : str       – text shown in the frame's border label.

    Returns
    -------
    tk.LabelFrame
    """
    return tk.LabelFrame(
        parent, text=f"  {title}  ",
        bg=PANEL_BG, fg=ACCENT,
        font=FONT_TITLE,
        bd=1, relief="solid",
    )


def make_entry(parent, width=12):
    """
    Create and return a styled tk.Entry input field.

    Parameters
    ----------
    parent : tk widget – the container that will hold the entry.
    width  : int       – character width of the entry field (default 12).

    Returns
    -------
    tk.Entry
    """
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
# Build a vertically scrollable main area using a Canvas + Frame combo
outer = tk.Frame(root, bg=BG)
outer.pack(fill="both", expand=True)

main_canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
scrollbar   = ttk.Scrollbar(outer, orient="vertical",
                             command=main_canvas.yview,
                             style="Vertical.TScrollbar")

scrollable_frame = tk.Frame(main_canvas, bg=BG)
# Recalculate scroll region whenever the inner frame resizes
scrollable_frame.bind(
    "<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
)

main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
main_canvas.configure(yscrollcommand=scrollbar.set)
main_canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")


def _on_mousewheel(event):
    """
    Scroll the main canvas vertically in response to the mouse wheel.

    Parameters
    ----------
    event : tk.Event – the MouseWheel event containing the scroll delta.
    """
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


# Shared state: list of Process objects added by the user
process_list  = []
# Stack of snapshots used by the Step Back feature
history_stack = []


# ================= UNDO HELPERS =================

def save_snapshot():
    """
    Push a deep copy of the current process list and tree rows onto
    the history stack so that step_back() can restore them later.
    Also refreshes the enabled/disabled state of the Step Back button.
    """
    history_stack.append({
        "process_list": copy.deepcopy(process_list),
        "tree_rows": [tree.item(r)["values"] for r in tree.get_children()],
    })
    update_step_back_btn()


def update_step_back_btn():
    """
    Enable the Step Back button when there is at least one snapshot in
    the history stack, otherwise disable it.
    """
    btn_step_back.config(state="normal" if history_stack else "disabled")


# ================= INPUT PANEL =================
input_frame = make_label_frame(scrollable_frame, "Input Panel")
input_frame.pack(fill="x", padx=14, pady=(6, 2))

# Column headers for the entry fields
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

make_btn(btn_frame, "+ Add Process",  lambda: add_process(), BTN_ADD,  16).pack(side="left", padx=8)
make_btn(btn_frame, "Run Simulation", lambda: run(),         BTN_RUN,  16).pack(side="left", padx=8)

btn_step_back = make_btn(btn_frame, "< Step Back", lambda: step_back(), BTN_BACK, 13)
btn_step_back.pack(side="left", padx=8)
btn_step_back.config(state="disabled")   # Disabled until the first snapshot exists

make_btn(btn_frame, "Reset", lambda: reset_all(), BTN_RESET, 10).pack(side="left", padx=8)


# ================= SCENARIO PRESETS =================
# Pre-defined process sets that demonstrate different scheduling behaviors
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

# Button accent colors per scenario key
SCENARIO_COLORS = {
    "A": "#5B8EF0",
    "B": "#4CAF82",
    "C": "#9673C6",
    "D": "#D4943A",
    "E": "#D95F5F",
}


def _silent_reset():
    """
    Clear all application state and UI widgets without showing any
    confirmation dialog.  Used internally by reset_all() and load_scenario().

    Clears:
      - process_list and history_stack
      - All rows in the process, RR, SJF, and average metric tables
      - Both Gantt canvases
      - The ready-queue listbox and its status label
      - The summary text area
      - All four input entry fields
    """
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
    """
    Load a pre-defined scenario, populate the process list, and run
    the simulation automatically.

    Parameters
    ----------
    key : str – one of 'A', 'B', 'C', 'D', 'E' identifying the scenario.

    Behavior
    --------
    - Calls _silent_reset() to start with a clean state.
    - Sets the quantum entry to the scenario's predefined value.
    - For scenario 'E' (validation demo), attempts to add intentionally
      invalid inputs so the user can observe each error dialog.
    - For all other scenarios, adds the predefined processes and then
      calls run() to display results immediately.
    """
    scenario = SCENARIOS[key]
    _silent_reset()
    quantum_entry.insert(0, str(scenario["quantum"]))

    if key == "E":
        # Scenario E: demonstrate validation by submitting bad inputs
        summary.insert(tk.END, scenario["description"] + "\n\nAttempting to add invalid inputs...\n")
        for pid, at, bt in [("P1", "0", "5"), ("P1", "1", "3"), ("P2", "abc", "4"), ("P3", "2", "0")]:
            pid_entry.delete(0, tk.END);     pid_entry.insert(0, pid)
            arrival_entry.delete(0, tk.END); arrival_entry.insert(0, at)
            burst_entry.delete(0, tk.END);   burst_entry.insert(0, bt)
            root.update()
            add_process()   # Each call will trigger an error dialog
        run()
        return

    # Normal scenario: populate process_list and the table, then simulate
    for pid, at, bt in scenario["processes"]:
        process_list.append(Process(pid, at, bt))
        tree.insert("", "end", values=(pid, at, bt))

    summary.insert(tk.END, scenario["description"] + "\n\n")
    run()


# Scenario quick-launch buttons (one per scenario key)
scenario_frame = tk.Frame(scrollable_frame, bg=BG)
scenario_frame.pack(fill="x", padx=14, pady=(4, 2))

tk.Label(scenario_frame, text="Quick Scenarios:",
         bg=BG, fg=SUBTEXT, font=("Segoe UI", 8)).pack(side="left", padx=(0, 6))

for _key, _sc in SCENARIOS.items():
    full_label = _sc["label"]
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

# --- Round Robin Gantt ---
tk.Label(gantt_frame, text="Round Robin",
         bg=PANEL_BG, fg=RR_COLOR, font=FONT_TITLE).pack(anchor="w", padx=8, pady=(4, 0))

rr_gantt_wrap = tk.Frame(gantt_frame, bg=GANTT_BG)
rr_gantt_wrap.pack(fill="x", padx=6, pady=(2, 10))

canvas_rr = tk.Canvas(rr_gantt_wrap, height=120, bg=GANTT_BG, highlightthickness=0)
rr_hscroll = ttk.Scrollbar(rr_gantt_wrap, orient="horizontal", command=canvas_rr.xview)
canvas_rr.configure(xscrollcommand=rr_hscroll.set)
canvas_rr.pack(fill="x", expand=True)
rr_hscroll.pack(fill="x")

# --- SJF Gantt ---
tk.Label(gantt_frame, text="SJF  (Non-Preemptive)",
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
    """
    Read the PID, Arrival Time, and Burst Time from the input entries,
    validate each field, and append a new Process to process_list.

    Validation rules
    ----------------
    - All three fields must be non-empty.
    - Arrival Time and Burst Time must be non-negative integers
      (only digit characters accepted).
    - Arrival Time must be >= 0; Burst Time must be > 0.
    - PID must be unique across all processes already added.

    On success
    ----------
    - Saves a snapshot to history_stack (enables Step Back).
    - Appends the new Process to process_list.
    - Inserts a row into the process Treeview.
    - Clears the PID, Arrival, and Burst entry fields.

    On failure
    ----------
    - Shows an error dialog describing the problem; no state is changed.
    """
    pid = pid_entry.get().strip()
    at  = arrival_entry.get().strip()
    bt  = burst_entry.get().strip()

    # Check all fields are filled in
    if not pid or not at or not bt:
        messagebox.showerror("Error", "All fields are required.")
        return

    # Ensure arrival and burst contain only digits
    if not at.isdigit() or not bt.isdigit():
        messagebox.showerror("Error", "Arrival & Burst must be non-negative integers.")
        return

    at = int(at)
    bt = int(bt)

    # Range checks
    if at < 0 or bt <= 0:
        messagebox.showerror("Error", "Arrival must be >= 0 and Burst must be > 0.")
        return

    # Duplicate PID check
    for p in process_list:
        if p.pid == pid:
            messagebox.showerror("Error", f"Duplicate PID '{pid}' is not allowed.")
            return

    # All checks passed — persist state and add process
    save_snapshot()
    process_list.append(Process(pid, at, bt))
    tree.insert("", "end", values=(pid, at, bt))

    # Clear the per-process entry fields (keep quantum intact)
    pid_entry.delete(0, tk.END)
    arrival_entry.delete(0, tk.END)
    burst_entry.delete(0, tk.END)


# ================= STEP BACK =================

def step_back():
    """
    Restore the application state to the most recent snapshot saved by
    save_snapshot(), effectively undoing the last add_process() call.

    Behavior
    --------
    - Pops the top snapshot from history_stack.
    - Replaces process_list contents with the snapshot's deep copy.
    - Rebuilds the process Treeview rows from the snapshot.
    - Calls update_step_back_btn() to disable the button if the stack
      is now empty.
    - Shows an info dialog if there is nothing to undo.
    """
    if not history_stack:
        messagebox.showinfo("Step Back", "No previous state to go back to.")
        return

    snapshot = history_stack.pop()
    process_list.clear()
    process_list.extend(snapshot["process_list"])

    # Rebuild the Treeview from the saved row data
    tree.delete(*tree.get_children())
    for row in snapshot["tree_rows"]:
        tree.insert("", "end", values=row)

    update_step_back_btn()


# ================= RESET =================

def reset_all():
    """
    Ask the user for confirmation, then clear all state and UI elements
    by delegating to _silent_reset().

    Shows a Yes/No dialog; does nothing if the user chooses No.
    """
    if not messagebox.askyesno("Reset", "Clear all data and results?"):
        return
    _silent_reset()


# ================= DRAW GANTT =================

def draw(canvas, gantt, algo):
    """
    Render a Gantt chart onto a tk.Canvas for the given scheduling result.

    Parameters
    ----------
    canvas : tk.Canvas
        The canvas widget to draw on (canvas_rr or canvas_sjf).
    gantt  : list of (pid, start, end) tuples
        Each tuple represents one CPU burst:
          pid   – process identifier string
          start – integer time when the burst begins
          end   – integer time when the burst finishes
    algo   : str
        'RR' to use RR_COLOR for the rectangles,
        any other value uses SJF_COLOR.

    Drawing layout (y-axis, canvas height = 120)
    --------------------------------------------
      y 12–62 : colored rectangle for each burst
      y 37    : PID label centered inside the rectangle
      y 76    : start/end time tick labels below the rectangle

    Each time unit maps to PX_PER_UNIT (50) pixels on the x-axis.
    The canvas scrollregion is updated to fit the total timeline width.
    """
    canvas.delete("all")
    if not gantt:
        return

    canvas.update_idletasks()
    total_time   = gantt[-1][2]   # End time of the last burst
    MARGIN       = 30
    PX_PER_UNIT  = 50             # Pixels per one time unit

    total_draw_w = int(total_time * PX_PER_UNIT) + MARGIN
    canvas.configure(scrollregion=(0, 0, total_draw_w, 120))

    x = 10   # Starting x-coordinate for the first block
    for pid, start, end in gantt:
        w     = (end - start) * PX_PER_UNIT
        color = RR_COLOR if algo == "RR" else SJF_COLOR

        # Draw the burst block
        canvas.create_rectangle(x, 12, x + w, 62,
                                 fill=color, outline=GANTT_BG, width=2)

        # Draw the PID label only if there is enough horizontal space
        if w > 20:
            canvas.create_text(x + w / 2, 37, text=pid,
                                fill="#FFFFFF", font=FONT_TITLE)

        # Draw start and end time ticks below the block
        canvas.create_text(x,     76, text=str(start),
                            fill=SUBTEXT, font=("Segoe UI", 8))
        canvas.create_text(x + w, 76, text=str(end),
                            fill=SUBTEXT, font=("Segoe UI", 8))
        x += w   # Advance x to the right edge of this block


# ================= RUN =================

def run():
    """
    Validate the time quantum, execute both scheduling algorithms on deep
    copies of process_list, and update every UI section with the results.

    Validation
    ----------
    - Time Quantum must be a positive integer; shows an error dialog otherwise.
    - At least one process must exist; shows an error dialog otherwise.

    Steps performed
    ---------------
    1. Deep-copy process_list twice (once for RR, once for SJF) and reset
       each copy's runtime attributes (remaining, response_time, etc.).
    2. Run round_robin() to get (gantt, states) for Round Robin.
    3. Run sjf() to get the Gantt list for Shortest Job First.
    4. Schedule Gantt drawing for both canvases (50 ms delay to allow the
       canvas to finish resizing before draw() reads its dimensions).
    5. Populate the Ready Queue listbox with the step-by-step RR states.
    6. Fill the RR and SJF per-process metric tables (WT, TAT, RT).
    7. Calculate average metrics for both algorithms and fill avg_table.
    8. Write a detailed plain-text Final Analysis into the summary Text widget.

    Metrics computed per process
    ----------------------------
    - TAT (Turnaround Time)  = finish_time - arrival
    - WT  (Waiting Time)     = TAT - burst
    - RT  (Response Time)    = process.response_time (set by the scheduler)
    """
    q = quantum_entry.get().strip()
    if not q.isdigit() or int(q) <= 0:
        messagebox.showerror("Error", "Time Quantum must be a positive integer.")
        return
    if not process_list:
        messagebox.showerror("Error", "No processes added yet.")
        return

    quantum  = int(q)

    # Create independent copies so both schedulers start from the same state
    rr       = copy.deepcopy(process_list)
    sjf_list = copy.deepcopy(process_list)

    # Reset runtime fields on every process copy before scheduling
    for p in rr + sjf_list:
        p.remaining     = p.burst
        p.response_time = None
        p.finish_time   = None
        p.started       = False

    # Run both scheduling algorithms
    rr_gantt,  rr_states = round_robin(rr, quantum)
    sjf_gantt             = sjf(sjf_list)

    # Draw Gantt charts after a short delay to ensure canvas dimensions are ready
    root.after(50, lambda: draw(canvas_rr,  rr_gantt,  "RR"))
    root.after(50, lambda: draw(canvas_sjf, sjf_gantt, "SJF"))

    # --- Populate Ready Queue listbox ---
    ready_queue.delete(0, tk.END)
    if rr_states:
        queue_status.config(text="RR Execution Steps Loaded", fg=SJF_COLOR)
        for i, state in enumerate(rr_states, 1):
            ready_queue.insert(tk.END, f"  Step {i:>3}:  {state}")
    else:
        queue_status.config(text="No RR states returned.", fg=BTN_RESET)

    # --- Fill per-process RR metrics table ---
    rr_table.delete(*rr_table.get_children())
    for p in rr:
        tat = p.finish_time - p.arrival
        wt  = tat - p.burst
        rt  = p.response_time if p.response_time is not None else 0
        rr_table.insert("", "end", values=(p.pid, wt, tat, rt))

    # --- Fill per-process SJF metrics table ---
    sjf_table.delete(*sjf_table.get_children())
    for p in sjf_list:
        tat = p.finish_time - p.arrival
        wt  = tat - p.burst
        rt  = p.response_time if p.response_time is not None else 0
        sjf_table.insert("", "end", values=(p.pid, wt, tat, rt))

    # --- Fill average comparison table ---
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

    # --- Write Final Analysis text ---
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