"""
Shared CPU-work guard.

Everything here runs on CPU only (embeddings, OCR) — there's no GPU to
fall back to. On a 6-core machine, if several users' documents get
embedded or OCR'd at the same moment, they all fight over the same
cores and *everyone's* request slows down together instead of failing
cleanly.

CPU_JOB_SLOTS bounds how many of those heavy jobs run at once. Extra
requests block on the semaphore and run as soon as a slot frees up,
rather than all threads thrashing the CPU simultaneously. This does
not add latency for a single user — it only matters once there's
real concurrency.

Tune via the CPU_JOB_SLOTS env var. Default of 2 leaves headroom for
Streamlit's own request handling and the LLM-call threads in llm.py
on a 6-core box; raise it if you deploy on more cores.
"""

import os
import threading

CPU_JOB_SLOTS = int(os.getenv("CPU_JOB_SLOTS", "2"))

_cpu_job_semaphore = threading.Semaphore(CPU_JOB_SLOTS)


class cpu_job:
    """Context manager: `with cpu_job(): ...` around any CPU-bound block
    (embedding a batch, running OCR on a page) so at most CPU_JOB_SLOTS
    of these run concurrently across all users of the app."""

    def __enter__(self):
        _cpu_job_semaphore.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _cpu_job_semaphore.release()
        return False
