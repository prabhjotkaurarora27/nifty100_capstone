# Performance & Load Testing Notes — Nifty 100 Analytics API

## 🚀 1. Concurrency Benchmark (10 Thread Screener Calls)
- **Total Duration for 10 Calls**: `0.0572 seconds` (Target: < 10s)
- **Status**: PASS ✅
- **Call Breakdown**:
  - Call 1: HTTP 200 in 55.97 ms
  - Call 2: HTTP 200 in 56.69 ms
  - Call 3: HTTP 200 in 52.14 ms
  - Call 4: HTTP 200 in 56.18 ms
  - Call 5: HTTP 200 in 42.92 ms
  - Call 6: HTTP 200 in 55.13 ms
  - Call 7: HTTP 200 in 41.88 ms
  - Call 8: HTTP 200 in 51.77 ms
  - Call 9: HTTP 200 in 53.28 ms
  - Call 10: HTTP 200 in 51.96 ms

## ⚡ 2. Company Profile Endpoint Latency
- **TCS Profile**: HTTP 200 in 2.38 ms (Target: < 3.0s)
- **INFY Profile**: HTTP 200 in 1.67 ms (Target: < 3.0s)
- **RELIANCE Profile**: HTTP 200 in 1.70 ms (Target: < 3.0s)
- **HDFCBANK Profile**: HTTP 200 in 1.68 ms (Target: < 3.0s)
- **ITC Profile**: HTTP 200 in 1.80 ms (Target: < 3.0s)

## 🌐 3. Ports & Service Isolation
- **FastAPI REST Server**: Served on `http://localhost:8000` (`/docs` OpenAPI available)
- **Streamlit Web Dashboard**: Served on `http://localhost:8501`
- **Port Conflicts**: Zero conflicts detected during simultaneous execution.
