def sjf(processes):
    """
    Simulate the Shortest Job First (SJF) CPU scheduling algorithm
    in its PREEMPTIVE form (also known as Shortest Remaining Time First — SRTF).

    At every clock tick the scheduler checks all arrived processes and
    always runs the one with the least remaining burst time. If a new
    process arrives with a shorter remaining time than the current one,
    a context switch occurs immediately.

    Parameters
    ----------
    processes : list of Process
        All processes to schedule. Each must have:
          arrival, burst, remaining, response_time, finish_time.

    Returns
    -------
    gantt : list of (pid, start, end) tuples
        The execution timeline in order — used to draw the Gantt chart.
        Consecutive ticks of the same process are merged into one block.
    """

    time      = 0     # Current simulation clock (advances 1 unit per iteration)
    gantt     = []    # Execution timeline: (pid, start, end)
    ready     = []    # Processes that have arrived and still have remaining burst

    processes.sort(key=lambda p: p.arrival)   # Ensure arrival order for scanning
    n         = len(processes)
    completed = 0     # Number of processes that have finished

    # Gantt merging helpers — track the current running process and when it started
    last_process = None
    start_time   = None

    while completed < n:

        # Enqueue every process that has arrived and still has work left
        for p in processes:
            if p.arrival <= time and p not in ready and p.remaining > 0:
                ready.append(p)

        # CPU is idle — no process has arrived yet, advance the clock by 1
        if not ready:
            time += 1
            continue

        # Pick the process with the shortest remaining burst (preemptive SJF / SRTF)
        ready.sort(key=lambda x: x.remaining)
        current = ready[0]

        # Record response time the first time this process gets the CPU
        if current.response_time is None:
            current.response_time = time - current.arrival

        # Detect a context switch — close the previous Gantt block and open a new one
        if last_process != current:
            if last_process is not None:
                gantt.append((last_process.pid, start_time, time))
            last_process = current
            start_time   = time

        # Execute exactly 1 time unit (preemptive: re-evaluate priorities next tick)
        current.remaining -= 1
        time += 1

        # Process has finished — record finish time and close its Gantt block
        if current.remaining == 0:
            current.finish_time = time
            ready.remove(current)
            completed += 1

            gantt.append((current.pid, start_time, time))
            last_process = None   # Reset so next process opens a fresh Gantt block
            start_time   = None

    return gantt