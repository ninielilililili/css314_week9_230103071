import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import psutil
import cpuinfo

# Project folders
BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"

def run_powershell(command):
    """Run a Windows PowerShell command and return its output."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--student-id", required=True)
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)

    # CPU information
    cpu = cpuinfo.get_cpu_info()
    processor = psutil.cpu_count(logical=False)
    logical = psutil.cpu_count(logical=True)
    frequency = psutil.cpu_freq()

    # Windows processor information
    wmi_cpu = run_powershell(
        "Get-CimInstance Win32_Processor | "
        "Select-Object -First 1 Name,L2CacheSize,L3CacheSize,MaxClockSpeed "
        "| ConvertTo-Json -Compress"
    )

    # Windows cache records
    cache_records = run_powershell(
        "Get-CimInstance Win32_CacheMemory | "
        "Select-Object DeviceID,Purpose,Level,InstalledSize,BlockSize "
        "| ConvertTo-Json -Compress"
    )

    if isinstance(cache_records, dict):
        cache_records = [cache_records]

    if not isinstance(cache_records, list):
        cache_records = []

    # CPU cache information from py-cpuinfo
    l1_data = cpu.get("l1_data_cache_size")
    l2_cache = cpu.get("l2_cache_size")
    l3_cache = cpu.get("l3_cache_size")
    cache_line = cpu.get("clflush_size")

    profile = {
        "cpu": {
            "model": cpu.get("brand_raw", platform.processor()),
            "architecture": cpu.get("arch"),
            "family": cpu.get("family"),
            "model_number": cpu.get("model"),
            "physical_cores": processor,
            "logical_processors": logical,
            "smt_enabled": logical > processor if processor and logical else None,
            "reported_max_clock_mhz": (
                wmi_cpu.get("MaxClockSpeed") if wmi_cpu else None
            ),
            "current_frequency_mhz": (
                frequency.current if frequency else None
            ),
            "l1_data_cache_reported": l1_data,
            "l2_cache_reported": l2_cache,
            "l3_cache_reported": l3_cache,
            "cache_line_bytes_reported": cache_line,
            "cache_records_from_windows": cache_records
        },
        "operating_system": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        },
        "python": {
            "version": sys.version,
            "implementation": sys.implementation.name
        },
        "numpy": None
    }

    try:
        import numpy
        profile["numpy"] = numpy.__version__
    except ImportError:
        pass

    if wmi_cpu:
        profile["cpu"]["windows_l2_cache_kb"] = wmi_cpu.get("L2CacheSize")
        profile["cpu"]["windows_l3_cache_kb"] = wmi_cpu.get("L3CacheSize")

    # Save hardware profile
    profile_path = RESULTS_DIR / "host_profile.json"
    with open(profile_path, "w", encoding="utf-8") as file:
        json.dump(profile, file, indent=4)

    # Save salted student parameters
    sys.path.insert(0, str(BASE_DIR))
    from src.salt import get_student_params

    params = get_student_params(args.student_id)

    params_path = RESULTS_DIR / "salted_params.json"
    with open(params_path, "w", encoding="utf-8") as file:
        json.dump(params, file, indent=4)

    print("Milestone 0 completed.")
    print("Hardware profile:", profile_path)
    print("Salted parameters:", params_path)
    print("\nSalted parameters:")
    print(json.dumps(params, indent=4))


if __name__ == "__main__":
    main()