def calculate_metrics(processes):
    total_wt = 0
    total_tat = 0
    total_rt = 0

    n = len(processes)
    if n == 0:
        return {"avg_wt": 0, "avg_tat": 0, "avg_rt": 0}

    for p in processes:
        arrival = p.arrival
        burst = p.burst

        # حماية من القيم الفارغة
        finish = p.finish_time if p.finish_time is not None else arrival + burst
        response = p.response_time if p.response_time is not None else 0

        tat = finish - arrival
        wt = tat - burst

        total_wt += wt
        total_tat += tat
        total_rt += response

    return {
        "avg_wt": round(total_wt / n, 3),
        "avg_tat": round(total_tat / n, 3),
        "avg_rt": round(total_rt / n, 3)
    }