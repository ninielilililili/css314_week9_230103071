
import time
from multiprocessing import Process, Queue


def buffered_worker(out_queue, start_index, items_per_worker,
                    batch_size=10_000):

    buffer = []

    for i in range(start_index, start_index + items_per_worker):

        buffer.append(i % 7)

        if len(buffer) >= batch_size:
            out_queue.put(sum(buffer))
            buffer.clear()

    # Send the remaining values
    if buffer:
        out_queue.put(sum(buffer))

    # Tell the main process that this worker is finished
    out_queue.put(None)


def run_buffered(p, total_items=10_000_000):

    q = Queue()

    base_items = total_items // p
    remainder = total_items % p

    workers = []

    for worker_id in range(p):

        items = base_items + (1 if worker_id < remainder else 0)

        start_index = worker_id * base_items + min(worker_id, remainder)

        worker = Process(
            target=buffered_worker,
            args=(q, start_index, items)
        )

        workers.append(worker)

    start_time = time.perf_counter()

    for worker in workers:
        worker.start()

    total_sum = 0
    active = p

    while active > 0:

        value = q.get()

        if value is None:
            active -= 1
        else:
            total_sum += value

    for worker in workers:
        worker.join()

    elapsed_time = time.perf_counter() - start_time

    q.close()
    q.join_thread()

    return elapsed_time, total_sum


if __name__ == "__main__":

    cores = [1, 2, 4, 8]

    runtimes = {}
    sums = {}

    print("\n===== EXPERIMENT C: CORRECTED BUFFERED QUEUE =====")

    for p in cores:

        runtime, total_sum = run_buffered(
            p,
            total_items=10_000_000
        )

        runtimes[p] = runtime
        sums[p] = total_sum

        print(
            f"Workers: {p:2d} | "
            f"Time: {runtime:.3f} seconds | "
            f"Sum: {total_sum}"
        )

    print("\n===== PERFORMANCE ANALYSIS =====")

    t1 = runtimes[1]

    for p in [2, 4, 8]:

        tp = runtimes[p]

        speedup = t1 / tp

        efficiency = speedup / p * 100

        e = ((p * tp / t1) - 1) / (p - 1)

        print(
            f"P={p:2d} | "
            f"Time={tp:.3f}s | "
            f"Speedup={speedup:.3f}x | "
            f"Efficiency={efficiency:.2f}% | "
            f"Karp-Flatt e={e:.4f}"
        )

