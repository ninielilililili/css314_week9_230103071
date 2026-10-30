
--- Chunk size: 1 ---
Workers:  1 | Time: 60.720 seconds | Total steps: 131434424
Workers:  2 | Time: 49.272 seconds | Total steps: 131434424
Workers:  4 | Time: 27.735 seconds | Total steps: 131434424
Workers:  8 | Time: 29.712 seconds | Total steps: 131434424

--- Chunk size: 10000 ---
Workers:  1 | Time: 9.183 seconds | Total steps: 131434424
Workers:  2 | Time: 5.538 seconds | Total steps: 131434424
Workers:  4 | Time: 3.728 seconds | Total steps: 131434424
Workers:  8 | Time: 3.135 seconds | Total steps: 131434424

===== SPEEDUP ANALYSIS =====

Chunk size: 1
P=2 | Time=49.272s | Speedup=1.232x | Efficiency=61.62% | Karp-Flatt=0.6229
P=4 | Time=27.735s | Speedup=2.189x | Efficiency=54.73% | Karp-Flatt=0.2757
P=8 | Time=29.712s | Speedup=2.044x | Efficiency=25.55% | Karp-Flatt=0.4164

Chunk size: 10000
P=2 | Time=5.538s | Speedup=1.658x | Efficiency=82.91% | Karp-Flatt=0.2062
P=4 | Time=3.728s | Speedup=2.463x | Efficiency=61.59% | Karp-Flatt=0.2079
P=8 | Time=3.135s | Speedup=2.929x | Efficiency=36.61% | Karp-Flatt=0.2473




===== EXPERIMENT B: QUEUE CONTENTION =====
Workers:  1 | Time: 3.152 seconds
Workers:  2 | Time: 10.744 seconds
Workers:  4 | Time: 11.638 seconds
Workers:  8 | Time: 11.913 seconds

===== QUEUE CONTENTION ANALYSIS =====
P= 2 | Time=10.744s | Speedup=0.293x | Efficiency=14.67% | Karp-Flatt e=5.8167
P= 4 | Time=11.638s | Speedup=0.271x | Efficiency=6.77% | Karp-Flatt e=4.5889
P= 8 | Time=11.913s | Speedup=0.265x | Efficiency=3.31% | Karp-Flatt e=4.1759


===== EXPERIMENT C: CORRECTED BUFFERED QUEUE =====
Workers:  1 | Time: 0.924 seconds | Sum: 29999994
Workers:  2 | Time: 0.547 seconds | Sum: 29999994
Workers:  4 | Time: 0.394 seconds | Sum: 29999994
Workers:  8 | Time: 0.458 seconds | Sum: 29999994

===== PERFORMANCE ANALYSIS =====
P= 2 | Time=0.547s | Speedup=1.688x | Efficiency=84.42% | Karp-Flatt e=0.1846
P= 4 | Time=0.394s | Speedup=2.343x | Efficiency=58.58% | Karp-Flatt e=0.2357
P= 8 | Time=0.458s | Speedup=2.019x | Efficiency=25.24% | Karp-Flatt e=0.4231




AND observation done by AI about my output (i just decided to ask ai how it performs):

Benchmark	Main bottleneck	Diagnostic verdict
A: Micro-tasks	Dispatch and scheduling overhead	Poor scaling
A: Coarse chunks	Reduced dispatch overhead	Improved scaling
B: Queue contention	Shared IPC queue contention	Negative scaling
C: Buffered batches	Remaining processing and parallel overhead	Improved communication, limited scaling