def sjf(processes):
    """
    Simulate the Shortest Job First (SJF) CPU scheduling algorithm
    in its NON-PREEMPTIVE form.

    Once a process is selected and starts running, it holds the CPU
    until it finishes — no interruptions allowed, even if a shorter
    process arrives in the meantime.

    At each selection point the scheduler picks the arrived process
    with the smallest burst time. If two processes have equal burst
    times, the one that arrived earlier is chosen.

    Parameters
    ----------
    processes : list of Process
        All processes to schedule. Each must have:
          arrival, burst, remaining, response_time, finish_time.

    Returns
    -------
    gantt : list of (pid, start, end) tuples
        The execution timeline in order — used to draw the Gantt chart.
    """

    time      = 0     # Current simulation clock
    gantt     = []    # Execution timeline: (pid, start, end)

    processes.sort(key=lambda p: p.arrival)   # Ensure arrival order for scanning
    n         = len(processes)
    completed = 0     # Number of processes that have finished
    done      = set() # PIDs of processes that have already finished

    while completed < n:

        # Collect all processes that have arrived and are not yet finished
        ready = [p for p in processes if p.arrival <= time and p.pid not in done]

        # CPU is idle — no process has arrived yet, advance the clock by 1
        if not ready:
            time += 1
            continue

        # Pick the process with the shortest burst time (non-preemptive selection)
        # Tie-break by arrival time so earlier arrivals go first
        ready.sort(key=lambda x: (x.burst, x.arrival))
        current = ready[0]

        # Record response time — equals waiting time since this is non-preemptive
        if current.response_time is None:
            current.response_time = time - current.arrival

        # Run the process to completion in one shot (no interruption possible)
        start = time
        time += current.burst   # Jump the clock forward by the full burst duration
        end   = time

        current.remaining   = 0    # Process has used all its CPU time
        current.finish_time = end  # Record when it finished

        gantt.append((current.pid, start, end))   # Log the full burst to the timeline

        done.add(current.pid)
        completed += 1

    return gantt