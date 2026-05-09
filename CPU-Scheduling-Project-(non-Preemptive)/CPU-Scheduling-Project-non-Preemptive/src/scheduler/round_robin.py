from collections import deque


def round_robin(processes, quantum):
    """
    Simulate the Round Robin (RR) CPU scheduling algorithm.

    Each process is given a fixed time slice (quantum). If it doesn't
    finish within that slice, it is re-added to the back of the queue
    and waits for its next turn.

    Parameters
    ----------
    processes : list of Process
        All processes to schedule. Each must have:
          arrival, burst, remaining, started, response_time, finish_time.
    quantum   : int
        Maximum CPU time given to a process per turn (must be > 0).

    Returns
    -------
    gantt  : list of (pid, start, end) tuples
        The execution timeline in order — used to draw the Gantt chart.
    states : list of str
        Snapshot of the ready queue at key moments — used for the
        step-by-step view in the UI.
    """

    time      = 0          # Current simulation clock
    queue     = deque()    # Ready queue holding processes waiting for the CPU
    gantt     = []         # Execution timeline: (pid, start, end)
    states    = []         # Queue snapshots for the step-by-step view

    processes.sort(key=lambda x: x.arrival)   # Process arrivals in order
    n         = len(processes)
    i         = 0          # Index into the sorted processes list
    completed = 0          # Number of processes that have finished

    def snapshot():
        """
        Record the current ready-queue contents as a readable string.
        Only appended if the state has changed since the last snapshot,
        to avoid duplicate entries in the step view.
        """
        state = f"t={time} → [" + ", ".join([p.pid for p in queue]) + "]"
        if not states or states[-1] != state:
            states.append(state)

    while queue or i < n:

        # Enqueue every process that has arrived by the current time
        while i < n and processes[i].arrival <= time:
            queue.append(processes[i])
            i += 1

        snapshot()   # Capture the queue state before picking the next process

        # CPU is idle — no process is ready yet, advance the clock by 1
        if not queue:
            time += 1
            continue

        current = queue.popleft()   # Pick the process at the front of the queue

        # Record response time on the very first CPU assignment
        if not current.started:
            current.response_time = time - current.arrival
            current.started = True

        # Run for at most one quantum, or whatever time is left if less
        exec_time = min(quantum, current.remaining)

        start = time
        end   = time + exec_time

        gantt.append((current.pid, start, end))   # Log this burst to the timeline

        time               = end
        current.remaining -= exec_time

        # Enqueue any processes that arrived while current was running
        while i < n and processes[i].arrival <= time:
            queue.append(processes[i])
            i += 1

        if current.remaining > 0:
            # Process still has work left — send it to the back of the queue
            queue.append(current)
        else:
            # Process is done — record its finish time
            current.finish_time = time
            completed += 1

        snapshot()   # Capture the queue state after the burst completes

    return gantt, states