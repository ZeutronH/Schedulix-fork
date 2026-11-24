# Schedulix — Engineering Concepts & Architectural Implementation

This document provides a comprehensive technical breakdown of the **Database Management Systems (DBMS)**, **Operating Systems (OS)**, and **Algorithmic** concepts implemented across the Schedulix codebase, citing exact file paths, class names, functions, and architectural decisions.

---

# PART I: DATABASE MANAGEMENT SYSTEMS (DBMS)

## 1. Database Normalisation & Schema Design
- **Code Reference**: [`backend/app/models.py`](file:///home/monkeching/Codes/Schedulix/backend/app/models.py)
- **Normal Form Enforced**: Third Normal Form (3NF).
- **Relational Integrity**:
  - **1NF**: Every table column stores atomic scalar values. Repeating groups such as enrolled students in a section are normalized into the relational junction table `Enrolment` ([`backend/app/models.py#L90-L105`](file:///home/monkeching/Codes/Schedulix/backend/app/models.py)).
  - **2NF**: All non-key attributes are fully functionally dependent on primary keys. In junction tables such as `FacultyAssignment` ([`backend/app/models.py#L107-L122`](file:///home/monkeching/Codes/Schedulix/backend/app/models.py)), all attributes (e.g. `weekly_sessions`, `active`) depend on the complete assignment relationship rather than a subset.
  - **3NF**: Non-key transitive dependencies have been removed. Scheduled classes do not replicate department codes, teacher names, or room equipment strings; instead, foreign keys (`section_id`, `faculty_id`, `room_id`, `subject_id`) link to dedicated master entities.

## 2. Primary Keys, Candidate Keys & Human-Readable Identifiers
- **Code Reference**: [`backend/app/models.py`](file:///home/monkeching/Codes/Schedulix/backend/app/models.py), [`backend/app/routers/academic.py`](file:///home/monkeching/Codes/Schedulix/backend/app/routers/academic.py)
- **Surrogate UUID Keys**: All primary entities employ surrogate UUID primary keys (`UUID(as_uuid=False)` or string UUIDs generated via `uuid.uuid4()`). This guarantees global uniqueness, prevents database enumeration attacks, and eliminates cascading key updates across distributed shards.
- **Natural Candidate Keys**:
  - `departments.code` (Unique constraint)
  - `programmes.code` (Unique constraint)
  - `subjects.code` (Unique constraint)
  - `faculty.email`, `faculty.faculty_id` (Unique constraints)
  - `students.student_id`, `students.email` (Unique constraints)
- **Concurrency-Safe ID Generation**:
  - Student identifiers: `YYYY + 5-digit sequential serial` (e.g., `202400001`).
  - Faculty identifiers: `DEPT-FAC-XXX` (e.g., `CSE-FAC-001`).
  - Classroom identifiers: `BLD-F{floor}-{room_name}` (e.g., `CE-B1-F1-R101`).
  - Subject codes: `DEPT-{semester * 100 + serial}` (e.g., `CS-104`, `CS-401`).
  - Generation functions execute within transactional boundaries utilizing `SELECT count(*) + 1 FOR UPDATE` to avoid duplicate serial generation under concurrent client access.

## 3. SQL Database Triggers vs. Application-Level Listeners
- **Code Reference**: [`backend/triggers.sql`](file:///home/monkeching/Codes/Schedulix/backend/triggers.sql)
- Schedulix implements PostgreSQL database triggers executed directly by the PostgreSQL database engine, ensuring constraints are enforced regardless of whether queries originate from FastAPI, Alembic, or direct DB administrative shells.

### Implemented Database Triggers
1. **Automated Audit Logging Trigger (`audit_entity_change_trigger`)**:
   - *Target Tables*: `scheduled_classes`, `faculty_assignments`, `timetable_versions`.
   - *Behavior*: Executes `AFTER INSERT OR UPDATE OR DELETE`. Constructs a JSON payload of the old and new row values and records an immutable log into `audit_logs` with action types `SQL_TRIGGER_INSERT`, `SQL_TRIGGER_UPDATE`, and `SQL_TRIGGER_DELETE`.
   - *Code*: [`backend/triggers.sql#L15-L65`](file:///home/monkeching/Codes/Schedulix/backend/triggers.sql)
2. **Faculty Availability Validation Trigger (`validate_faculty_availability_trigger`)**:
   - *Target Table*: `faculty_availability`.
   - *Behavior*: Executes `BEFORE INSERT OR UPDATE`. Ensures `end_time > start_time` and detects temporal overlaps with existing availability intervals for the same faculty member on the same weekday, raising an SQL exception (`RAISE EXCEPTION`) to reject corrupted data at the DBMS level.
   - *Code*: [`backend/triggers.sql#L70-L105`](file:///home/monkeching/Codes/Schedulix/backend/triggers.sql)
3. **Session Metadata Maintenance Trigger (`maintain_session_metadata_trigger`)**:
   - *Target Table*: `scheduled_classes`.
   - *Behavior*: Executes `BEFORE INSERT OR UPDATE`. Automatically calculates duration (`end_minute - start_minute`), enforces operating hours limits (08:00 to 20:00), and stamps the `updated_at` modification timestamp.
   - *Code*: [`backend/triggers.sql#L110-L140`](file:///home/monkeching/Codes/Schedulix/backend/triggers.sql)

### Distinction Between SQL Triggers and Application Listeners
- **SQL Triggers**: Guarantee ACID consistency at the database engine level. They cannot be bypassed by external administrative SQL scripts or bulk ETL imports.
- **SQLAlchemy Event Listeners** (`app.audit.record_audit`): Handle higher-level application context, such as capturing the authenticated HTTP request admin ID, client IP address, and complex business notification dispatches.

## 4. Transactions and ACID Guarantees
- **Code Reference**: [`backend/app/routers/scheduling.py`](file:///home/monkeching/Codes/Schedulix/backend/app/routers/scheduling.py), [`backend/app/services/rescheduler.py`](file:///home/monkeching/Codes/Schedulix/backend/app/services/rescheduler.py)
- **Atomicity**: Timetable generation writes 40-100+ session records across multiple tables (`timetable_versions`, `scheduled_classes`, `audit_logs`). The operation occurs within a single transaction block (`with db.begin():` or explicit commit/rollback). If any constraint fails, the entire transaction rolls back via `db.rollback()`, ensuring zero orphaned classes or partially written versions.
- **Consistency**: Database foreign keys with `ON DELETE CASCADE` or `ON DELETE RESTRICT` maintain referential integrity. Schema checks reject negative durations or unassigned rooms.
- **Isolation**:
  - Version publishing uses PostgreSQL row-level pessimistic locking: `db.execute(select(TimetableVersion).where(id == version_id).with_for_update())` ([`backend/app/routers/scheduling.py#L303-L308`](file:///home/monkeching/Codes/Schedulix/backend/app/routers/scheduling.py)).
  - Prevents race conditions where two administrators might approve or publish conflicting versions concurrently.
- **Durability**: All modifications are persisted through PostgreSQL write-ahead logs (WAL) to disk before HTTP success responses are returned.

## 5. Database Indexing Strategy
- **Code Reference**: [`backend/app/models.py`](file:///home/monkeching/Codes/Schedulix/backend/app/models.py), [`backend/alembic/versions/`](file:///home/monkeching/Codes/Schedulix/backend/alembic/versions/)
- Strategic B-tree indexes are added on high-cardinality foreign keys and scheduling query predicates:
  - `ix_scheduled_classes_version_id`: Speeds up timetable rendering and validation by version.
  - `ix_scheduled_classes_faculty_id` & `ix_scheduled_classes_room_id`: Accelerates clash detection during real-time rescheduling queries.
  - `ix_scheduled_classes_weekday_start`: Multi-column index optimizing time-slice range lookups.
  - `ix_students_student_id` & `ix_faculty_faculty_id`: Fast human-readable ID search.
  - `ix_audit_logs_created_at` & `ix_audit_logs_entity`: Allows fast pagination on the admin Audit Trail.

## 6. Audit Logging Architecture
- **Code Reference**: [`backend/app/audit.py`](file:///home/monkeching/Codes/Schedulix/backend/app/audit.py), [`backend/app/routers/audit.py`](file:///home/monkeching/Codes/Schedulix/backend/app/routers/audit.py)
- All state-altering operations record:
  - `timestamp`: UTC datetime.
  - `admin_id`: Foreign key to `administrators` (nullable for automated triggers).
  - `action`: Canonical action string (e.g. `TIMETABLE_GENERATED`, `VERSION_PUBLISHED`, `SESSION_RESCHEDULED`, `EMAIL_SENT`, `SQL_TRIGGER_INSERT`).
  - `entity_type`: Target entity name (`TimetableVersion`, `ScheduledClass`, `FacultyAssignment`).
  - `entity_id`: Primary key of the affected entity.
  - `details`: Structured JSON dictionary capturing before/after values, solver statistics, or recipient emails.

---

# PART II: OPERATING SYSTEMS CONCEPTS (OS)

## 1. Process Management, Background Workers & Concurrency
- **Code Reference**: [`backend/app/tasks/jobs.py`](file:///home/monkeching/Codes/Schedulix/backend/app/tasks/jobs.py), [`backend/app/routers/scheduling.py#L156-L200`](file:///home/monkeching/Codes/Schedulix/backend/app/routers/scheduling.py)
- Timetable generation is an NP-hard combinatorial problem that may require significant computational time.
- **Asynchronous Execution**:
  - `POST /api/scheduling/generate-async`: Dispatches the generation job to a Celery distributed background worker backed by Redis.
  - Returns immediate response with `task_id` and initial state `PENDING`.
  - Clients track progress via `GET /api/scheduling/task/{task_id}` which reports `STARTED`, `PROGRESS`, `SUCCESS`, or `FAILURE` with solver diagnostics.

## 2. CPU Scheduling Policies Applied to Timetable Generation
- **Code Reference**: [`backend/app/services/scheduler.py`](file:///home/monkeching/Codes/Schedulix/backend/app/services/scheduler.py)
- Schedulix draws an architectural parallel between OS CPU process scheduling and academic session scheduling:
  - **OS Process**: Job arriving at the CPU ready queue with priority, burst time (duration), and resource requirements (memory, I/O).
  - **Academic Session**: Class session arriving at the solver queue with subject priority, duration in minutes, and resource requirements (faculty, room, lab equipment).

### Implemented Strategies:
1. **Priority Scheduling**:
   - Jobs are prioritized by subject academic weighting:
     $$\text{Score} = \frac{\text{priority}}{10.0}$$
   - High-priority courses (e.g. core engineering theory and accredited capstones) are scheduled into optimal morning prime-time slots first.
2. **Shortest Job First (SJF)**:
   - Evaluates job burst times (session durations):
     $$\text{Score} = \frac{\text{max\_duration} - \text{duration}}{\text{max\_duration} - \text{min\_duration}}$$
   - Favors shorter sessions (e.g. 60-minute tutorials) over long sessions, minimizing average queue waiting time and packing density.
3. **Hybrid Priority-SJF**:
   - Combines priority and SJF using administrator-configurable weights:
     $$\text{Score} = w_{\text{priority}} \times \left(\frac{\text{priority}}{10.0}\right) + w_{\text{sjf}} \times \left(\frac{\text{max\_duration} - \text{duration}}{\text{max\_duration} - \text{min\_duration}}\right)$$
   - Configurable via frontend sliders (e.g. 65% Priority / 35% SJF).
   - In OR-Tools CP-SAT, this score scales the objective coefficients of candidate assignment variables, directly influencing solver variable selection and branch heuristics.

## 3. Counting & Binary Semaphores
- **Code Reference**: [`backend/app/concurrency.py#L25-L95`](file:///home/monkeching/Codes/Schedulix/backend/app/concurrency.py)
- **Binary Semaphore Implementation**:
  - Implements Python's `threading.Semaphore(1)` combined with a PostgreSQL transactional advisory lock (`pg_try_advisory_xact_lock(741852)`).
  - Initialized with value 1 (`s = Semaphore(1)`).
  - **Acquire (`wait`)**: Prior to starting timetable generation, the thread executes `s.acquire(blocking=True, timeout=timeout_seconds)`. If another generation job is running, incoming requests block or time out, returning HTTP 429 (Too Many Requests).
  - **Release (`signal`)**: Implemented via Python's `contextlib.contextmanager`. In the `finally:` block, `s.release()` is unconditionally executed, ensuring that even on unhandled exceptions or solver failures, the semaphore counter is incremented and the resource is freed.
- **Distributed Advisory Lock**:
  - Local process semaphores only protect a single process. Schedulix complements the binary semaphore with PostgreSQL's session-level advisory lock, guaranteeing mutual exclusion across multiple independent backend Docker containers without relying on third-party lock daemons.

## 4. Critical Sections & Mutual Exclusion
- **Critical Sections in Schedulix**:
  1. *Timetable Generation*: Solvers read unallocated rooms, assign classes, and persist versions. If two solvers ran concurrently without mutual exclusion, they would read the same vacant rooms and assign clashing classes.
  2. *Rescheduling Transactions*: Moving a class requires reading availability, checking clashes, and updating the slot. Mutual exclusion prevents two administrators from moving two different classes into the same room simultaneously.
  3. *Sequential Human-Readable ID Allocation*: Counter increments must be atomic to prevent assigning the same student ID to two admissions.

## 5. Deadlock Prevention & Coffman Conditions
- **Code Reference**: [`backend/app/concurrency.py#L97-L175`](file:///home/monkeching/Codes/Schedulix/backend/app/concurrency.py)
- In a university timetable system, multiple resources (Faculty, Classrooms, Lab Equipment, Sections) must be acquired simultaneously. Uncontrolled acquisition causes deadlocks.
- Schedulix demonstrates the elimination of the four **Coffman Conditions**:

| Coffman Condition | Mathematical Description | Schedulix Prevention Mechanism |
| :--- | :--- | :--- |
| **Mutual Exclusion** | Resources cannot be shared simultaneously. | Maintained because physical rooms and faculty cannot be cloned. |
| **Hold and Wait** | Process holds resource $R_1$ while requesting $R_2$. | **Eliminated**: All required resource locks are acquired atomically as a unified bundle before execution begins. If any lock fails, all acquired locks are immediately released and rolled back. |
| **No Preemption** | Resources cannot be forcibly confiscated. | **Eliminated**: PostgreSQL bounded `SET LOCAL lock_timeout = '2s'` forces preemption. If a lock cannot be acquired within 2 seconds, the transaction aborts and rolls back safely. |
| **Circular Wait** | Process $P_1$ waits for $P_2$ while $P_2$ waits for $P_1$. | **Eliminated via Global Canonical Lock Ordering**: Schedulix defines a strict global hierarchy: `FACULTY (1) < CLASSROOM (2) < SECTION (3) < SESSION (4)`. Resources are sorted lexicographically by `(Hierarchy_Level, UUID)` before lock acquisition, rendering circular wait mathematically impossible. |

---

# PART III: CONSTRAINT OPTIMIZATION & GRAPH ALGORITHMS

## 1. OR-Tools CP-SAT Solver Formulation
- **Code Reference**: [`backend/app/services/scheduler.py`](file:///home/monkeching/Codes/Schedulix/backend/app/services/scheduler.py)
- The timetable scheduling problem is formulated as a Constraint Satisfaction and Integer Linear Programming model using Google OR-Tools CP-SAT:

### Decision Variables
For each candidate job $j \in J$, day $d \in D$, start minute $t \in T$, and room $r \in R$:
$$x_{j, d, t, r} \in \{0, 1\}$$
where $x = 1$ if job $j$ is scheduled on day $d$ at time $t$ in room $r$.

### Constraints
1. **Job Completion**: Each required session of an assignment must be scheduled exactly once:
   $$\sum_{d, t, r} x_{j, d, t, r} = 1 \quad \forall j \in J$$
2. **Room Mutual Exclusion (Zero Clashes)**: No room can host more than one class during any discrete time-slice:
   $$\sum_{j \in J(r, \tau)} x_{j, d, t, r} \le 1 \quad \forall r \in R, d \in D, \tau \in \text{TimeSlices}$$
3. **Faculty Mutual Exclusion**: No faculty member can teach multiple classes simultaneously:
   $$\sum_{j \in J(f, \tau)} x_{j, d, t, r} \le 1 \quad \forall f \in F, d \in D, \tau \in \text{TimeSlices}$$
4. **Section Mutual Exclusion**: No student section can attend two classes simultaneously:
   $$\sum_{j \in J(s, \tau)} x_{j, d, t, r} \le 1 \quad \forall s \in S, d \in D, \tau \in \text{TimeSlices}$$
5. **Classroom Type & Capacity**:
   - Laboratory sessions ($j \in J_{\text{lab}}$) are constrained to rooms where $r_{\text{type}} = \text{LABORATORY}$.
   - Class size must not exceed room capacity: $\text{student\_count}(j) \le \text{capacity}(r)$.
6. **Faculty Availability**: $x_{j, d, t, r} = 0$ if faculty $f(j)$ has marked unavailable for day $d$ and time $t$.

### Objective Function
Maximize the weighted quality score:
$$\max \sum_{j, d, t, r} x_{j, d, t, r} \cdot \left[ w_{\text{priority}} \cdot \text{Score}_{\text{priority}}(j) + w_{\text{sjf}} \cdot \text{Score}_{\text{sjf}}(j) + \text{Bonus}_{\text{morning}}(t) \right]$$

### Performance Optimization
Rather than generating an $O(N^2)$ pairwise non-overlapping interval constraint network across thousands of boolean combinations, Schedulix groups candidate variables into discrete 30-minute time-slice resource buckets ($\sum x \le 1$). This reduction lowered constraint setup complexity from $O(N^2)$ to $O(N)$, allowing 48 university class sessions across 6 departments to solve to proven **OPTIMAL** in approximately 20 seconds.

---

## 2. Graph Algorithms: NetworkX Dijkstra Shortest Path
- **Code Reference**: [`backend/app/services/graph.py`](file:///home/monkeching/Codes/Schedulix/backend/app/services/graph.py), [`backend/app/routers/campus.py#L155-L203`](file:///home/monkeching/Codes/Schedulix/backend/app/routers/campus.py)
- Campus navigation and transit between consecutive classes is modeled as a weighted directed graph $G = (V, E)$ using NetworkX:
  - **Vertices ($V$)**: Campus nodes representing building entrances, floor corridors, stairwells, elevators, and classroom doorways.
  - **Edges ($E$)**: Physical pathways between nodes, weighted by Euclidean distance in meters ($w(u, v)$).
  - **Edge Attributes**: `accessible` (boolean for wheelchair/ramp access), `bidirectional` (boolean), `connection_type` (`CORRIDOR`, `STAIRS`, `ELEVATOR`).

### Shortest Path Routing (Dijkstra's Algorithm)
Given source classroom $R_1$ mapped to node $u$ and target classroom $R_2$ mapped to node $v$, Dijkstra's algorithm computes the minimum distance path:
$$d(v) = \min_{u \in V} \{ d(u) + w(u, v) \}$$
- **Accessibility Filtering**: When `accessible_only=True`, stairs and non-accessible edges are filtered prior to Dijkstra execution, returning ADA-compliant wheelchair routes.
- **Transit Estimation**: Walking transit time is calculated assuming an average university walking velocity of $80\text{ m/min}$ ($1.33\text{ m/s}$):
  $$\text{Walking Time (minutes)} = \frac{\text{distance\_meters}}{80.0}$$
This metric is displayed on the frontend campus map and used by timetable validators to prevent scheduling consecutive classes for faculty or students in distant buildings without adequate transit windows.
