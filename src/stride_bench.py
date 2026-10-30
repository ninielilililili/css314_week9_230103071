import csv
import time
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"

def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    data = np.ones(16_777_216, dtype=np.float64)
    strides = [1, 2, 4, 8, 16, 32, 64, 128]

    output = RESULTS_DIR / "stride_results.tsv"

    with open(output, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow([
            "stride",
            "elements_touched",
            "median_time_ns",
            "latency_ns_per_element",
            "checksum"
        ])

        for stride in strides:
            view = data[::stride]

            # Warmup
            for _ in range(5):
                checksum = np.sum(view)

            # Measurement
            times = []
            for _ in range(5):
                start = time.perf_counter_ns()
                checksum = np.sum(view)
                end = time.perf_counter_ns()
                times.append(end - start)

            median_time = float(np.median(times))
            elements = len(view)
            latency = median_time / elements

            writer.writerow([
                stride,
                elements,
                median_time,
                latency,
                float(checksum)
            ])

            print(
                f"Stride {stride:3}: "
                f"{median_time:,.0f} ns, "
                f"{latency:.4f} ns/element"
            )

    print(f"\nSaved results to: {output}")


if __name__ == "__main__":
    main()