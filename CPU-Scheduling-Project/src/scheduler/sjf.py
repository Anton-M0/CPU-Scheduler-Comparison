def sjf(processes):
    time = 0
    gantt = []
    ready = []

    processes.sort(key=lambda p: p.arrival)
    n = len(processes)
    completed = 0

    last_process = None
    start_time = None

    while completed < n:

        # add arrived processes
        for p in processes:
            if p.arrival <= time and p not in ready and p.remaining > 0:
                ready.append(p)

        if not ready:
            time += 1
            continue

        # 🔥 pick shortest remaining time (PREEMPTIVE)
        ready.sort(key=lambda x: x.remaining)
        current = ready[0]

        # response time (first time only)
        if current.response_time is None:
            current.response_time = time - current.arrival

        # detect context switch for Gantt
        if last_process != current:
            if last_process is not None:
                gantt.append((last_process.pid, start_time, time))
            last_process = current
            start_time = time

        # execute 1 unit time (preemptive step)
        current.remaining -= 1
        time += 1

        # if finished
        if current.remaining == 0:
            current.finish_time = time
            ready.remove(current)
            completed += 1

            gantt.append((current.pid, start_time, time))
            last_process = None
            start_time = None

    return gantt