
import time
from multiprocessing import Pool


# Calculate the number of steps required for a Collatz sequence
def collatz_steps(n):
    steps = 0

    while n > 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1

        steps += 1

    return steps


# Run the granularity experiment
def run_granularity(workers, total_items=1_000_000, chunk_size=1):

    numbers = range(1, total_items + 1)

    start_time = time.perf_counter()

    with Pool(processes=workers) as pool:
        results = pool.map(
            collatz_steps,
            numbers,
            chunksize=chunk_size
        )

    elapsed_time = time.perf_counter() - start_time

    return elapsed_time, sum(results)


if __name__ == "__main__":

    cores = [1, 2, 4, 8]
    chunk_sizes = [1, 10000]

    results = {}

    print("\n===== EXPERIMENT A: GRANULARITY =====")

    for chunk_size in chunk_sizes:

        print(f"\n--- Chunk size: {chunk_size} ---")

        for workers in cores:

            runtime, total_steps = run_granularity(
                workers,
                total_items=1_000_000,
                chunk_size=chunk_size
            )

            results[(chunk_size, workers)] = runtime

            print(
                f"Workers: {workers:2d} | "
                f"Time: {runtime:.3f} seconds | "
                f"Total steps: {total_steps}"
            )

    print("\n===== SPEEDUP ANALYSIS =====")

    for chunk_size in chunk_sizes:

        t1 = results[(chunk_size, 1)]

        print(f"\nChunk size: {chunk_size}")

        for workers in [2, 4, 8]:

            tp = results[(chunk_size, workers)]

            speedup = t1 / tp

            efficiency = speedup / workers * 100

            karp_flatt = (
                (workers * tp / t1) - 1
            ) / (workers - 1)

            print(
                f"P={workers} | "
                f"Time={tp:.3f}s | "
                f"Speedup={speedup:.3f}x | "
                f"Efficiency={efficiency:.2f}% | "
                f"Karp-Flatt={karp_flatt:.4f}"
            )

