import csv
import json
import math
import multiprocessing as mp
import statistics
import time
from pathlib import Path
from multiprocessing import shared_memory

import numpy as np


BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"

ITERATIONS = 5
REPEATS = 3

# Shared variables used by worker processes
BUFFER_A = None
BUFFER_B = None
SHM_A = None
SHM_B = None


def initialize_worker(name_a, name_b, n):
    """Attach each worker to the shared input and output matrices."""
    global BUFFER_A, BUFFER_B, SHM_A, SHM_B

    SHM_A = shared_memory.SharedMemory(name=name_a)
    SHM_B = shared_memory.SharedMemory(name=name_b)

    BUFFER_A = np.ndarray(
        (n, n), dtype=np.float64, buffer=SHM_A.buf
    )
    BUFFER_B = np.ndarray(
        (n, n), dtype=np.float64, buffer=SHM_B.buf
    )

def update_chunk(task):
    """Update a group of matrix rows using a 5-point stencil."""
    start_row, end_row, source_index = task

    if source_index == 0:
        source = BUFFER_A
        target = BUFFER_B
    else:
        source = BUFFER_B
        target = BUFFER_A

    target[start_row:end_row, 1:-1] = (
        source[start_row - 1:end_row - 1, 1:-1]
        + source[start_row + 1:end_row + 1, 1:-1]
        + source[start_row:end_row, :-2]
        + source[start_row:end_row, 2:]
    ) * 0.25

    return end_row - start_row


def make_tasks(n, workers):
    """Divide the interior matrix rows between workers."""
    edges = np.linspace(
        1, n - 1, workers + 1, dtype=int
    )

    return [
        (int(edges[i]), int(edges[i + 1]), 0)
        for i in range(workers)
        if edges[i] < edges[i + 1]
    ]


def serial_reference(initial_matrix):
    """Calculate the reference result using one process."""
    source = initial_matrix.copy()
    target = np.zeros_like(source)

    for _ in range(ITERATIONS):
        target[1:-1, 1:-1] = (
            source[:-2, 1:-1]
            + source[2:, 1:-1]
            + source[1:-1, :-2]
            + source[1:-1, 2:]
        ) * 0.25

        source, target = target, source

    return source


def run_benchmark(n, workers, seed):
    """Benchmark the stencil using shared memory and a process pool."""
    rng = np.random.default_rng(seed)

    initial = rng.random((n, n), dtype=np.float64)

    # Keep the matrix boundary equal to zero.
    initial[0, :] = 0
    initial[-1, :] = 0
    initial[:, 0] = 0
    initial[:, -1] = 0

    reference = serial_reference(initial)
    reference_checksum = float(np.sum(reference))

    shm_a = shared_memory.SharedMemory(
        create=True, size=initial.nbytes
    )
    shm_b = shared_memory.SharedMemory(
        create=True, size=initial.nbytes
    )

    array_a = np.ndarray(
        (n, n), dtype=np.float64, buffer=shm_a.buf
    )
    array_b = np.ndarray(
        (n, n), dtype=np.float64, buffer=shm_b.buf
    )

    tasks = make_tasks(n, workers)

    measurements = []
    final_checksum = None

    try:
        with mp.Pool(
            processes=workers,
            initializer=initialize_worker,
            initargs=(shm_a.name, shm_b.name, n)
        ) as pool:

            # Warmup run. It is not included in the measurements.
            array_a[:] = initial
            array_b.fill(0)

            for iteration in range(ITERATIONS):
                source_index = iteration % 2

                current_tasks = [
                    (start, end, source_index)
                    for start, end, _ in tasks
                ]

                pool.map(update_chunk, current_tasks)

            # Run the measured trials.
            for repeat in range(REPEATS):
                array_a[:] = initial
                array_b.fill(0)

                start_time = time.perf_counter()

                for iteration in range(ITERATIONS):
                    source_index = iteration % 2

                    current_tasks = [
                        (start, end, source_index)
                        for start, end, _ in tasks
                    ]

                    pool.map(update_chunk, current_tasks)

                elapsed = time.perf_counter() - start_time

                final_array = (
                    array_a if ITERATIONS % 2 == 0 else array_b
                )

                final_checksum = float(np.sum(final_array))

                if not np.isclose(
                    final_checksum,
                    reference_checksum,
                    rtol=1e-10,
                    atol=1e-8
                ):
                    raise ValueError(
                        f"Checksum mismatch for N={n}, P={workers}: "
                        f"parallel={final_checksum}, "
                        f"serial={reference_checksum}"
                    )

                measurements.append(elapsed)

                print(
                    f"N={n:5} | workers={workers:2} | "
                    f"run={repeat + 1}/{REPEATS} | "
                    f"time={elapsed:.4f}s | "
                    f"checksum={final_checksum:.6f}"
                )

    finally:
        del array_a
        del array_b

        shm_a.close()
        shm_b.close()

        shm_a.unlink()
        shm_b.unlink()

    return {
        "median_time": statistics.median(measurements),
        "checksum": final_checksum,
        "reference_checksum": reference_checksum
    }


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    with open(
        RESULTS_DIR / "salted_params.json",
        encoding="utf-8"
    ) as file:
        params = json.load(file)

    with open(
        RESULTS_DIR / "host_profile.json",
        encoding="utf-8"
    ) as file:
        host = json.load(file)

    n = int(params["N"])
    seed = int(params["seed"])

    physical_cores = int(host.get("physical_cores", 16))

    # Powers of two up to the available physical core count.
    workers_list = [1, 2, 4, 8, 16]
    workers_list = [
        p for p in workers_list if p <= physical_cores
    ]

    strong_results = {}
    weak_results = {}

    print("=" * 70)
    print("MILESTONE 3: STRONG SCALING")
    print(f"Base matrix size: {n} x {n}")
    print(f"Workers: {workers_list}")
    print("=" * 70)

    # Strong scaling: keep N fixed.
    for workers in workers_list:
        strong_results[workers] = run_benchmark(
            n, workers, seed
        )

    time_one = strong_results[1]["median_time"]

    print("\n" + "=" * 70)
    print("MILESTONE 3: WEAK SCALING")
    print("=" * 70)

    # Weak scaling: increase matrix dimension with sqrt(P).
    for workers in workers_list:
        scaled_n = math.ceil(n * math.sqrt(workers))

        weak_results[workers] = run_benchmark(
            scaled_n,
            workers,
            seed
        )

    # Save strong and weak scaling results.
    output_file = RESULTS_DIR / "scaling_metrics.tsv"

    with open(
        output_file, "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.writer(file, delimiter="\t")

        writer.writerow([
            "scaling_type",
            "workers",
            "matrix_dimension",
            "median_time_seconds",
            "speedup",
            "efficiency_percent",
            "serial_fraction",
            "scaled_speedup",
            "checksum",
            "reference_checksum"
        ])

        for workers in workers_list:
            item = strong_results[workers]
            elapsed = item["median_time"]

            speedup = time_one / elapsed
            efficiency = speedup / workers * 100

            if workers == 1:
                serial_fraction = 0.0
            else:
                serial_fraction = (
                    (1 / speedup) - (1 / workers)
                ) / (1 - (1 / workers))

            writer.writerow([
                "strong",
                workers,
                n,
                elapsed,
                speedup,
                efficiency,
                serial_fraction,
                "",
                item["checksum"],
                item["reference_checksum"]
            ])

        base_work = (n - 2) ** 2 * ITERATIONS

        for workers in workers_list:
            scaled_n = math.ceil(n * math.sqrt(workers))
            item = weak_results[workers]
            elapsed = item["median_time"]

            scaled_work = (
                (scaled_n - 2) ** 2 * ITERATIONS
            )

            scaled_speedup = (
                workers * base_work * time_one
            ) / (scaled_work * elapsed)

            writer.writerow([
                "weak",
                workers,
                scaled_n,
                elapsed,
                "",
                "",
                "",
                scaled_speedup,
                item["checksum"],
                item["reference_checksum"]
            ])

    # Calculate Amdahl's theoretical limit using the average
    # of the measured serial fractions for P > 1.
    fractions = []

    for workers in workers_list:
        if workers == 1:
            continue

        elapsed = strong_results[workers]["median_time"]
        speedup = time_one / elapsed

        fraction = (
            (1 / speedup) - (1 / workers)
        ) / (1 - (1 / workers))

        fractions.append(fraction)

    average_fraction = (
        statistics.mean(fractions) if fractions else None
    )

    if average_fraction is not None and average_fraction > 0:
        maximum_speedup = 1 / average_fraction
    else:
        maximum_speedup = None

    # A 5-point stencil uses four loads and one store per cell.
    # Four additions plus one multiplication = 5 FLOPs.
    flops_per_cell = 5
    bytes_per_cell = 5 * 8
    arithmetic_intensity = flops_per_cell / bytes_per_cell

    roofline = {
        "kernel": "2D five-point stencil",
        "iterations": ITERATIONS,
        "floating_point_operations_per_cell": flops_per_cell,
        "bytes_per_cell_without_cache_reuse": bytes_per_cell,
        "arithmetic_intensity_flops_per_byte": arithmetic_intensity,
        "assumption": (
            "Four float64 neighbor loads and one float64 output store "
            "per updated cell; cache reuse is not included."
        ),
        "cache_sizes_from_host_profile": host,
        "memory_bandwidth_assessment": (
            "Likely memory-bandwidth sensitive because arithmetic "
            "intensity is low. A definitive Roofline classification "
            "requires verified peak memory bandwidth and peak FLOP rate."
        ),
        "amdahl_average_serial_fraction": average_fraction,
        "amdahl_maximum_speedup": maximum_speedup
    }

    with open(
        RESULTS_DIR / "roofline_summary.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(roofline, file, indent=4)

    print("\n" + "=" * 70)
    print("SCALING SUMMARY")
    print("=" * 70)

    for workers in workers_list:
        elapsed = strong_results[workers]["median_time"]
        speedup = time_one / elapsed
        efficiency = speedup / workers * 100

        print(
            f"Strong scaling P={workers:2}: "
            f"time={elapsed:.4f}s | "
            f"speedup={speedup:.3f}x | "
            f"efficiency={efficiency:.2f}%"
        )

    print("\nAmdahl's law:")
    print(f"Average serial fraction: {average_fraction}")
    print(f"Theoretical maximum speedup: {maximum_speedup}")

    print("\nRoofline:")
    print(f"Arithmetic intensity: {arithmetic_intensity:.4f} FLOPs/byte")

    print("\nFiles saved:")
    print(RESULTS_DIR / "scaling_metrics.tsv")
    print(RESULTS_DIR / "roofline_summary.json")


if __name__ == "__main__":
    mp.freeze_support()
    main()