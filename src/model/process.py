class Process:
    def __init__(self, pid, arrival, burst):
        self.pid = pid
        self.arrival = arrival
        self.burst = burst

        # runtime fields
        self.remaining = burst
        self.finish_time = None
        self.response_time = None

        # internal flags
        self.started = False