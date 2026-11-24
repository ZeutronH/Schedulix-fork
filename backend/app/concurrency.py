"""
Operating System Concurrency Control, Semaphores, and Deadlock Prevention for Schedulix.

This module implements:
1. SEMAPHORES: Python asyncio/threading semaphore paired with PostgreSQL transaction advisory locks.
   Controls access to the timetable generation critical section.
2. DEADLOCK PREVENTION: Enforces strict resource hierarchy ordering, bounded acquisition timeouts,
   no hold-and-wait, and safe rollback on timeout.
"""

import asyncio
import threading
import time
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from fastapi import HTTPException

# -----------------------------------------------------------------------------
# 1. SEMAPHORE CONCURRENCY CONTROL
# -----------------------------------------------------------------------------
# A threading Semaphore with capacity 1 (binary semaphore / mutex) for local process mutual exclusion.
# Combined with PostgreSQL advisory lock (pg_try_advisory_xact_lock) for distributed mutual exclusion.
GENERATION_SEMAPHORE = threading.Semaphore(1)
ASYNC_GENERATION_SEMAPHORE = asyncio.Semaphore(1)

# PostgreSQL Advisory Lock key for university-wide timetable generation
TIMETABLE_ADVISORY_LOCK_ID = 741852

class SemaphoreBusyException(HTTPException):
    def __init__(self, detail: str = "Timetable generation is currently in progress. Please wait."):
        super().__init__(status_code=429, detail=detail)


@contextmanager
def acquire_generation_semaphore(db: Session, scope: str = "GLOBAL", timeout_seconds: float = 2.0):
    """
    Acquires both the in-process semaphore and the PostgreSQL database-level advisory lock.
    Demonstrates:
    - Semaphore Initialisation: GENERATION_SEMAPHORE initialized with value=1.
    - Semaphore Wait / Acquire: bounded acquire with timeout prevents indefinite waiting.
    - Mutual Exclusion: only one thread / process can enter the critical section.
    - Semaphore Signal / Release: release() guaranteed in finally block.
    """
    acquired_local = False
    start_time = time.time()

    # 1. Acquire in-memory semaphore with timeout
    acquired_local = GENERATION_SEMAPHORE.acquire(timeout=timeout_seconds)
    if not acquired_local:
        raise SemaphoreBusyException(
            f"Scheduling Semaphore: Resource is busy. Another generation operation is in progress (waited {timeout_seconds}s)."
        )

    try:
        # 2. Acquire database-level transaction advisory lock (distributed mutual exclusion)
        # We use pg_try_advisory_xact_lock on PostgreSQL to fail fast without hanging the database connection.
        is_postgres = bool(db.bind and db.bind.dialect.name == "postgresql")
        if is_postgres:
            result = db.execute(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": TIMETABLE_ADVISORY_LOCK_ID}
            ).scalar()

            if not result:
                raise SemaphoreBusyException(
                    "Distributed Lock: Another Schedulix backend worker holds the timetable generation lock."
                )

        yield {
            "scope": scope,
            "acquired_at": datetime.utcnow().isoformat(),
            "local_semaphore": True,
            "db_advisory_lock": is_postgres
        }

    finally:
        # 3. Always release local semaphore on exit
        if acquired_local:
            GENERATION_SEMAPHORE.release()


# -----------------------------------------------------------------------------
# 2. DEADLOCK PREVENTION & HIERARCHICAL LOCKING
# -----------------------------------------------------------------------------
# Deadlock requires 4 Coffman conditions simultaneously:
# 1. Mutual Exclusion
# 2. Hold and Wait
# 3. No Preemption
# 4. Circular Wait
#
# Prevention Strategies Implemented:
# A. Circular Wait Elimination: Strict global resource lock hierarchy.
#    Resources must ALWAYS be acquired in increasing numerical order:
#    ACADEMIC_SCOPE (1) -> FACULTY (2) -> CLASSROOM (3) -> TIMETABLE_SESSION (4)
# B. Hold and Wait Elimination: Atomic multi-resource acquisition with rollback.
# C. Bounded Lock Acquisition Timeouts: Prevents indefinite blocking.
# -----------------------------------------------------------------------------

RESOURCE_HIERARCHY = {
    "ACADEMIC_SCOPE": 1,
    "FACULTY": 2,
    "CLASSROOM": 3,
    "TIMETABLE_SESSION": 4
}


class DeadlockPreventionManager:
    """
    Manages lock acquisition obeying global ordering and timeout bounds.
    """

    @staticmethod
    def sort_resources(resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sorts candidate resources according to the strict canonical global hierarchy."""
        return sorted(
            resources,
            key=lambda r: (RESOURCE_HIERARCHY.get(r.get("type", ""), 999), str(r.get("id", "")))
        )

    @staticmethod
    def acquire_ordered_locks(db: Session, resources: List[Dict[str, Any]], timeout_seconds: float = 3.0):
        """
        Acquires row-level locks on requested resources in strictly ascending global order.
        If any lock cannot be acquired within the timeout, rolls back and raises an error.
        """
        sorted_res = DeadlockPreventionManager.sort_resources(resources)

        # Set transaction lock timeout in PostgreSQL
        if db.bind and db.bind.dialect.name == "postgresql":
            timeout_ms = int(timeout_seconds * 1000)
            db.execute(text(f"SET LOCAL lock_timeout = '{timeout_ms}ms'"))

        acquired = []
        try:
            for res in sorted_res:
                r_type = res["type"]
                r_id = res["id"]

                # Perform row lock based on entity type
                if r_type == "FACULTY":
                    db.execute(text("SELECT id FROM faculty WHERE id = :id FOR UPDATE"), {"id": r_id})
                elif r_type == "CLASSROOM":
                    db.execute(text("SELECT id FROM rooms WHERE id = :id FOR UPDATE"), {"id": r_id})
                elif r_type == "TIMETABLE_SESSION":
                    db.execute(text("SELECT id FROM scheduled_classes WHERE id = :id FOR UPDATE"), {"id": r_id})
                
                acquired.append(f"{r_type}:{r_id}")

            return {
                "status": "ACQUIRED",
                "lock_order": acquired,
                "strategy": "CIRCULAR_WAIT_ELIMINATION"
            }
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Deadlock Prevention: Failed to acquire lock in ordered hierarchy within {timeout_seconds}s timeout. Transaction safely rolled back. Detail: {str(e)}"
            )
