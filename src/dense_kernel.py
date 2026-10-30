import json
import statistics
import time
from pathlib import Path

import numpy as np
from numba import njit

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"


@njit
def multiply_ijk(A, B, C, M):
    for i in range(M):
        for j in range(M):
            total = 0.0
            for k in range(M):
                total += A[i * M + k] * B[k * M + j]
            C[i * M + j] = total


@njit
def multiply_ikj(A, B, C, M):
    for i in range(M):
        for k in range(M):
            a_value = A[i * M + k]
            for j in range(M):
                C[i * M + j] += a_value * B[k * M + j]


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    # Read the salted parameters
    with open(RESULTS_DIR / "salted_params.json", encoding="utf-8") as file:
        params = json.load(file)

    N = params["N"]
    M = N // 2
    seed = params["seed"]

    rng = np.random.default_rng(seed)

    A = rng.random(M * M).astype(np.float64)
    B = rng.random(M * M).astype(np.float64)

    times_ijk = []
    times_ikj = []

    result_ijk = np.zeros(M * M, dtype=np.float64)
    result_ikj = np.zeros(M * M, dtype=np.float64)

    # Compile both functions before measuring
    multiply_ijk(A, B, result_ijk, M)
    multiply_ikj(A, B, result_ikj, M)

    # Three measured runs
    for run in range(3):
        result_ijk.fill(0)
        start = time.perf_counter()
        multiply_ijk(A, B, result_ijk, M)
        times_ijk.append(time.perf_counter() - start)

        result_ikj.fill(0)
        start = time.perf_counter()
        multiply_ikj(A, B, result_ikj, M)
        times_ikj.append(time.perf_counter() - start)

        print(f"Completed run {run + 1}/3")

    median_ijk = statistics.median(times_ijk)
    median_ikj = statistics.median(times_ikj)

    max_difference = float(np.max(np.abs(result_ijk - result_ikj)))
    speedup = median_ijk / median_ikj

    results = {
        "student_id": params["student_id"],
        "N": N,
        "M": M,
        "algorithm_ijk_median_seconds": median_ijk,
        "algorithm_ikj_median_seconds": median_ikj,
        "speedup": speedup,
        "maximum_absolute_difference": max_difference,
        "numerically_equivalent": bool(
            np.allclose(result_ijk, result_ikj, rtol=0, atol=1e-12)
        ),
        "checksum_ijk": float(np.sum(result_ijk)),
        "checksum_ikj": float(np.sum(result_ikj))
    }

    output = RESULTS_DIR / "loop_interchange.json"

    with open(output, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    print("\nLoop interchange results")
    print(f"Matrix size: {M} x {M}")
    print(f"i-j-k median: {median_ijk:.6f} seconds")
    print(f"i-k-j median: {median_ikj:.6f} seconds")
    print(f"Speedup: {speedup:.4f}x")
    print(f"Maximum difference: {max_difference:.12g}")
    print(f"Equivalent: {results['numerically_equivalent']}")
    print(f"\nSaved to: {output}")


if __name__ == "__main__":
    main()