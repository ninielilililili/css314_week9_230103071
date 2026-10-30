import csv
import multiprocessing as mp
import statistics
import time
from pathlib import Path
from ctypes import c_int64


BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"

WORKERS = [1, 2, 4, 8]
K = 5_000_000
REPEATS = 3
PADDING = 8  # 8 int64 values × 8 bytes = 64 bytes


def worker(shared_array, barrier, worker_id, mode, increments):
    """
    Each process updates its own counter.
    The barrier makes workers start at approximately the same time.
    """

    barrier.wait()

    if mode == "unpadded":
        index = worker_id

        for _ in range(increments):
            shared_array[index] += 1

    elif mode == "padded":
        index = worker_id * PADDING

        for _ in range(increments):
            shared_array[index] += 1

    elif mode == "privatized":
        local_count = 0

        for _ in range(increments):
            local_count += 1

        # One shared-memory write after local counting
        shared_array[worker_id] = local_count


def run_once(process_count, mode):
    """
    Run one experiment and return its execution time and final counter total.
    """

    context = mp.get_context("spawn")

    if mode == "padded":
        array_size = process_count * PADDING
    else:
        array_size = process_count

    shared_array = context.RawArray(c_int64, array_size)
    barrier = context.Barrier(process_count + 1)

    processes = []

    for worker_id in range(process_count):
        process = context.Process(
            target=worker,
            args=(
                shared_array,
                barrier,
                worker_id,
                mode,
                K
            )
        )

        processes.append(process)
        process.start()

    # Start timing after all processes have been created.
    start_time = time.perf_counter()

    # Release all workers at approximately the same time.
    barrier.wait()

    for process in processes:
        process.join()

    end_time = time.perf_counter()

    # Check whether any worker failed.
    for process in processes:
        if process.exitcode != 0:
            raise RuntimeError(
                f"Worker process failed with exit code {process.exitcode}"
            )

    # Calculate the total number of increments.
    if mode == "padded":
        total = sum(
            shared_array[i * PADDING]
            for i in range(process_count)
        )
    else:
        total = sum(
            shared_array[i]
            for i in range(process_count)
        )

    expected_total = process_count * K

    if total != expected_total:
        raise ValueError(
            f"Incorrect result for {mode}, P={process_count}: "
            f"expected {expected_total}, got {total}"
        )

    return end_time - start_time, total


def run_experiment(process_count, mode):
    """
    Repeat the experiment and return the median execution time.
    """

    measurements = []
    total = 0

    for repeat in range(REPEATS):
        elapsed, total = run_once(process_count, mode)
        measurements.append(elapsed)

        print(
            f"{mode:10} | workers={process_count:2} | "
            f"run={repeat + 1}/{REPEATS} | "
            f"time={elapsed:.4f}s | total={total:,}"
        )

    return statistics.median(measurements), total


def karp_flatt(time_one, time_parallel, process_count):
    """
    Calculate the Karp-Flatt effective serial fraction.
    """

    if process_count == 1:
        return 0.0

    speedup = time_one / time_parallel

    return (
        (1 / speedup) - (1 / process_count)
    ) / (1 - (1 / process_count))


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    modes = ["unpadded", "padded", "privatized"]

    results = {}

    print("=" * 75)
    print("FALSE SHARING EXPERIMENT")
    print(f"Increments per worker: {K:,}")
    print(f"Worker counts: {WORKERS}")
    print(f"Repeats per experiment: {REPEATS}")
    print("=" * 75)

    # Run all three methods for each worker count.
    for mode in modes:
        results[mode] = {}

        for process_count in WORKERS:
            median_time, total = run_experiment(
                process_count,
                mode
            )

            results[mode][process_count] = {
                "time": median_time,
                "total": total
            }

    # Calculate Karp-Flatt values using each method's own P=1 baseline.
    output_file = RESULTS_DIR / "false_sharing_karp_flatt.tsv"

    with open(output_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter="\t")

        writer.writerow([
            "method",
            "workers",
            "increments_per_worker",
            "total_increments",
            "median_time_seconds",
            "speedup",
            "efficiency_percent",
            "karp_flatt"
        ])

        for mode in modes:
            time_one = results[mode][1]["time"]

            for process_count in WORKERS:
                elapsed = results[mode][process_count]["time"]

                speedup = time_one / elapsed
                efficiency = speedup / process_count * 100

                if mode in ["unpadded", "padded"]:
                    kf = karp_flatt(
                        time_one,
                        elapsed,
                        process_count
                    )
                else:
                    kf = ""

                total = results[mode][process_count]["total"]

                writer.writerow([
                    mode,
                    process_count,
                    K,
                    total,
                    elapsed,
                    speedup,
                    efficiency,
                    kf
                ])

    print("\n" + "=" * 75)
    print("EXPERIMENT SUMMARY")
    print("=" * 75)

    for mode in modes:
        print(f"\n{mode.upper()}")

        for process_count in WORKERS:
            item = results[mode][process_count]

            print(
                f"P={process_count:2} | "
                f"time={item['time']:.4f}s | "
                f"total={item['total']:,}"
            )

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    mp.freeze_support()
    main()