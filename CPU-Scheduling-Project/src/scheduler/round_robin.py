from collections import deque

def round_robin(processes, quantum):
    time = 0
    queue = deque()
    gantt = []
    states = []

    processes.sort(key=lambda x: x.arrival)
    n = len(processes)
    i = 0
    completed = 0

    def snapshot():
        state = f"t={time} → [" + ", ".join([p.pid for p in queue]) + "]"
        if not states or states[-1] != state:
            states.append(state)

    while queue or i < n:

        # Add arrived processes
        while i < n and processes[i].arrival <= time:
            queue.append(processes[i])
            i += 1

        snapshot()

        if not queue:
            time += 1
            continue

        current = queue.popleft()

        # Response time (first execution only)
        if not current.started:
            current.response_time = time - current.arrival
            current.started = True

        exec_time = min(quantum, current.remaining)

        start = time
        end = time + exec_time

        gantt.append((current.pid, start, end))

        time = end
        current.remaining -= exec_time

        # Add new arrivals during execution
        while i < n and processes[i].arrival <= time:
            queue.append(processes[i])
            i += 1

        # Requeue or finish
        if current.remaining > 0:
            queue.append(current)
        else:
            current.finish_time = time
            completed += 1

        snapshot()

    return gantt, states