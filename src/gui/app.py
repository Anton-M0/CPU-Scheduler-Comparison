import tkinter as tk
from tkinter import ttk, messagebox
import copy

from src.model.process import Process
from src.scheduler.round_robin import round_robin
from src.scheduler.sjf import sjf
from src.metrics.calculations import calculate_metrics


# ================= COLORS =================
RR_COLOR = "#4DA6FF"
SJF_COLOR = "#5CD65C"
IDLE_COLOR = "#C0C0C0"


# ================= ROOT =================
root = tk.Tk()
root.title("CPU Scheduling Simulator (RR vs SJF)")
root.geometry("1050x1000")


# ================= SCROLL =================
main_canvas = tk.Canvas(root)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=main_canvas.yview)

scrollable_frame = tk.Frame(main_canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
)

main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
main_canvas.configure(yscrollcommand=scrollbar.set)

main_canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")


process_list = []


# ================= INPUT =================
input_frame = tk.LabelFrame(scrollable_frame, text="Input Panel", padx=10, pady=10)
input_frame.pack(fill="x", padx=10, pady=5)

tk.Label(input_frame, text="PID").grid(row=0, column=0)
tk.Label(input_frame, text="Arrival").grid(row=0, column=1)
tk.Label(input_frame, text="Burst").grid(row=0, column=2)
tk.Label(input_frame, text="Quantum").grid(row=0, column=3)

pid_entry = tk.Entry(input_frame)
arrival_entry = tk.Entry(input_frame)
burst_entry = tk.Entry(input_frame)
quantum_entry = tk.Entry(input_frame)

pid_entry.grid(row=1, column=0)
arrival_entry.grid(row=1, column=1)
burst_entry.grid(row=1, column=2)
quantum_entry.grid(row=1, column=3)


# ================= BUTTONS =================
btn_frame = tk.Frame(scrollable_frame)
btn_frame.pack(pady=5)

tk.Button(btn_frame, text="Add Process", command=lambda: add_process()).pack(side="left", padx=10)
tk.Button(btn_frame, text="Run Simulation", command=lambda: run()).pack(side="left", padx=10)


# ================= PROCESS TABLE =================
table_frame = tk.LabelFrame(scrollable_frame, text="Process Table")
table_frame.pack(fill="x", padx=10, pady=5)

tree = ttk.Treeview(table_frame, columns=("PID", "Arrival", "Burst"), show="headings")

for c in ("PID", "Arrival", "Burst"):
    tree.heading(c, text=c)

tree.pack(fill="x")


# ================= READY QUEUE =================
rq_frame = tk.LabelFrame(scrollable_frame, text="Ready Queue (RR) - Step View")
rq_frame.pack(fill="x", padx=10, pady=5)

ready_queue = tk.Listbox(rq_frame, height=6)
ready_queue.pack(fill="x")

queue_status = tk.Label(rq_frame, text="Waiting for simulation...", fg="gray")
queue_status.pack()


# ================= GANTT =================
gantt_frame = tk.LabelFrame(scrollable_frame, text="Gantt Charts")
gantt_frame.pack(fill="x", padx=10, pady=5)

tk.Label(gantt_frame, text="Round Robin").pack()
canvas_rr = tk.Canvas(gantt_frame, height=140, bg="white")
canvas_rr.pack(fill="x")

tk.Label(gantt_frame, text="SJF").pack()
canvas_sjf = tk.Canvas(gantt_frame, height=140, bg="white")
canvas_sjf.pack(fill="x")


# ================= RR METRICS TABLE =================
rr_frame = tk.LabelFrame(scrollable_frame, text="RR Metrics")
rr_frame.pack(fill="x", padx=10, pady=5)

rr_table = ttk.Treeview(rr_frame, columns=("PID", "WT", "TAT", "RT"), show="headings")

for c in ("PID", "WT", "TAT", "RT"):
    rr_table.heading(c, text=c)

rr_table.pack(fill="x")


# ================= SJF METRICS TABLE =================
sjf_frame = tk.LabelFrame(scrollable_frame, text="SJF Metrics")
sjf_frame.pack(fill="x", padx=10, pady=5)

sjf_table = ttk.Treeview(sjf_frame, columns=("PID", "WT", "TAT", "RT"), show="headings")

for c in ("PID", "WT", "TAT", "RT"):
    sjf_table.heading(c, text=c)

sjf_table.pack(fill="x")


# ================= AVERAGE TABLE =================
avg_frame = tk.LabelFrame(scrollable_frame, text="Average Metrics Comparison")
avg_frame.pack(fill="x", padx=10, pady=5)

avg_table = ttk.Treeview(avg_frame,
    columns=("Algorithm", "Avg WT", "Avg TAT", "Avg RT"),
    show="headings",
    height=2
)

for c in ("Algorithm", "Avg WT", "Avg TAT", "Avg RT"):
    avg_table.heading(c, text=c)

avg_table.pack(fill="x")


# ================= SUMMARY (RESTORED) =================
summary_frame = tk.LabelFrame(scrollable_frame, text="Final Analysis")
summary_frame.pack(fill="both", expand=True, padx=10, pady=5)

summary = tk.Text(summary_frame, height=12)
summary.pack(fill="both", expand=True)


# ================= ADD PROCESS (FIXED VALIDATION) =================
def add_process():
    pid = pid_entry.get().strip()
    at = arrival_entry.get().strip()
    bt = burst_entry.get().strip()

    if not pid or not at or not bt:
        messagebox.showerror("Error", "All fields required")
        return

    if not at.isdigit() or not bt.isdigit():
        messagebox.showerror("Error", "Arrival & Burst must be non-negative numbers")
        return

    at = int(at)
    bt = int(bt)

    if at < 0 or bt <= 0:
        messagebox.showerror("Error", "Arrival must be >= 0 and Burst must be > 0")
        return

    for p in process_list:
        if p.pid == pid:
            messagebox.showerror("Error", f"Duplicate PID '{pid}' is not allowed!")
            return

    process_list.append(Process(pid, at, bt))
    tree.insert("", "end", values=(pid, at, bt))

    pid_entry.delete(0, tk.END)
    arrival_entry.delete(0, tk.END)
    burst_entry.delete(0, tk.END)


# ================= DRAW =================
def draw(canvas, gantt, algo):
    canvas.delete("all")

    x = 10
    scale = 30

    for pid, start, end in gantt:
        width = (end - start) * scale
        color = RR_COLOR if algo == "RR" else SJF_COLOR

        canvas.create_rectangle(x, 20, x + width, 70, fill=color)
        canvas.create_text(x + width/2, 45, text=pid)

        canvas.create_text(x, 80, text=start)
        canvas.create_text(x + width, 80, text=end)

        x += width


# ================= RUN =================
def run():
    q = quantum_entry.get().strip()

    if not q.isdigit() or int(q) <= 0:
        messagebox.showerror("Error", "Invalid Quantum")
        return

    if not process_list:
        messagebox.showerror("Error", "No processes added")
        return

    quantum = int(q)

    rr = copy.deepcopy(process_list)
    sjf_list = copy.deepcopy(process_list)

    for p in rr + sjf_list:
        p.remaining = p.burst
        p.response_time = None
        p.finish_time = None
        p.started = False

    rr_gantt, rr_states = round_robin(rr, quantum)
    sjf_gantt = sjf(sjf_list)

    draw(canvas_rr, rr_gantt, "RR")
    draw(canvas_sjf, sjf_gantt, "SJF")

    ready_queue.delete(0, tk.END)

    if rr_states:
        queue_status.config(text="RR Execution Steps Loaded", fg="green")
        for i, state in enumerate(rr_states, 1):
            ready_queue.insert(tk.END, f"Step {i}: {state}")
    else:
        queue_status.config(text="No RR states returned", fg="red")

    rr_table.delete(*rr_table.get_children())
    for p in rr:
        tat = p.finish_time - p.arrival
        wt = tat - p.burst
        rt = p.response_time if p.response_time is not None else 0
        rr_table.insert("", "end", values=(p.pid, wt, tat, rt))

    sjf_table.delete(*sjf_table.get_children())
    for p in sjf_list:
        tat = p.finish_time - p.arrival
        wt = tat - p.burst
        rt = p.response_time if p.response_time is not None else 0
        sjf_table.insert("", "end", values=(p.pid, wt, tat, rt))

    avg_table.delete(*avg_table.get_children())

    rr_m = calculate_metrics(rr)
    sjf_m = calculate_metrics(sjf_list)

    avg_table.insert("", "end", values=("RR",
        round(rr_m["avg_wt"], 2),
        round(rr_m["avg_tat"], 2),
        round(rr_m["avg_rt"], 2)))

    avg_table.insert("", "end", values=("SJF",
        round(sjf_m["avg_wt"], 2),
        round(sjf_m["avg_tat"], 2),
        round(sjf_m["avg_rt"], 2)))

    # ================= RESTORED SUMMARY =================
    summary.delete("1.0", tk.END)

    summary.insert(tk.END, f"""
================ FINAL ANALYSIS ================

Average Metrics:
WT  → RR={rr_m['avg_wt']:.2f} | SJF={sjf_m['avg_wt']:.2f}
TAT → RR={rr_m['avg_tat']:.2f} | SJF={sjf_m['avg_tat']:.2f}
RT  → RR={rr_m['avg_rt']:.2f} | SJF={sjf_m['avg_rt']:.2f}

---------------- Comparison ----------------

• Fairness vs Efficiency:
  RR is fair (time sharing).
  SJF is efficient (short jobs first).

• CPU Distribution:
  RR rotates using quantum.
  SJF picks shortest job available.

• Quantum Effect:
  Small quantum → better responsiveness.
  Large quantum → behaves like FCFS.

• Response Time:
  RR usually better response.
  SJF may delay long jobs.

• Long Process Impact:
  RR handles long jobs fairly.
  SJF may cause starvation risk.

---------------- Result ----------------

✔ Better WT  → {'RR' if rr_m['avg_wt'] < sjf_m['avg_wt'] else 'SJF'}
✔ Better RT  → {'RR' if rr_m['avg_rt'] < sjf_m['avg_rt'] else 'SJF'}

Quantum = {quantum}

===============================================
""")

root.mainloop()