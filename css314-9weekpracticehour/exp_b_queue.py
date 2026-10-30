
import time
from multiprocessing import Process, Queue


# Worker sends individual items through a shared queue
def queue_worker(out_queue, items_per_worker):

    for i in range(items_per_worker):

        # Every iteration sends one item through IPC
        out_queue.put(i % 7)


# Run the queue contention benchmark
def run_queue_benchmark(p, total_items=400_000):

    q = Queue()

    items_per_worker = total_items // p

    workers = [
        Process(
            target=queue_worker,
            args=(q, items_per_worker)
        )
        for _ in range(p)
    ]

    start_time = time.perf_counter()

    # Start all worker processes
    for w in workers:
        w.start()

    # Main process receives all items
    collected = 0

    while collected < total_items:
        q.get()
        collected += 1

    # Wait for workers to finish
    for w in workers:
        w.join()

    elapsed_time = time.perf_counter() - start_time

    q.close()
    q.join_thread()

    return elapsed_time


if __name__ == "__main__":

    cores = [1, 2, 4, 8]

    runtimes = {}

    print("\n===== EXPERIMENT B: QUEUE CONTENTION =====")

    for p in cores:

        runtime = run_queue_benchmark(p)

        runtimes[p] = runtime

        print(
            f"Workers: {p:2d} | "
            f"Time: {runtime:.3f} seconds"
        )

    # Calculate Karp-Flatt metric
    t1 = runtimes[1]

    print("\n===== QUEUE CONTENTION ANALYSIS =====")

    for p in [2, 4, 8]:

        tp = runtimes[p]

        speedup = t1 / tp

        efficiency = speedup / p * 100

        e = ((p * tp / t1) - 1.0) / (p - 1.0)

        print(
            f"P={p:2d} | "
            f"Time={tp:.3f}s | "
            f"Speedup={speedup:.3f}x | "
            f"Efficiency={efficiency:.2f}% | "
            f"Karp-Flatt e={e:.4f}"
        )