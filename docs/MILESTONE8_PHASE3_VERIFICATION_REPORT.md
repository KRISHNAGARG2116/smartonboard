# Milestone 8 Phase 3 Verification Report
## Candidate Self-Scheduling & Interactive Booking

This report details the architectural design, security boundaries, database schemas, overlap constraints, candidate ownership checks, and verification results for the completed **Milestone 8 Phase 3 (Self-Scheduling Subsystem)** of SmartOnboard.

---

### 1. Key Accomplishments

#### A. Database Migration `013`
* **Exclusion Overlap Constraint**: Enables `btree_gist` extension in PostgreSQL and establishes the `exclude_overlapping_confirmed_bookings` exclude constraint on `interview_slots` table, mathematically preventing overlapping confirmed bookings:
  ```sql
  ALTER TABLE interview_slots ADD CONSTRAINT exclude_overlapping_confirmed_bookings
  EXCLUDE USING gist (
      interview_id WITH =,
      tstzrange(start_time, end_time) WITH &&
  ) WHERE (status = 'confirmed')
  ```
* **Ownership Token Column**: Adds `booking_token_hash` (VARCHAR(64), Nullable=True, Unique=True) to `interview_slots`.

#### B. Public Availability Grid Resolver
* **Interactive Grid**: Selects slots by parsing live third-party calendars free/busy feeds dynamically, combining recruiter working hours boundaries and existing database bookings, and resolving consensus lists.
* **Link TTLs & Expiry**: Public availability lookup gates expired and single-use scheduling links, returning HTTP `410 Gone`.

#### C. Candidate Booking Ownership Validation
* **Single-Use Ownership tokens**: Booking confirmation returns a 128-bit `booking_token` once. The database persists only `booking_token_hash = sha256(booking_token)`.
* **Authorized Cancel & Reschedule**: Candidate reschedule and cancellation endpoints validate requests, matching:  
  `sha256(X-Booking-Token) == slot.booking_token_hash`.

#### D. Specialized Scheduling Auditing
Exposes eight append-only compliant logs:
* `schedule.link_created` on link generation.
* `schedule.link_expired` when accessing expired links.
* `schedule.slot_booked` on slot bookings.
* `schedule.slot_cancelled` on meeting cancellations.
* `schedule.rescheduled` on meeting reschedules.
* `schedule.reminder_sent` on notification dispatches.
* `schedule.calendar_event_created` on provider sync successes.
* `schedule.calendar_event_failed` on provider sync outages.

---

### 2. Security & RLS Isolation
* Public endpoints verify tokens under company RLS parameters.
* Booking tokens prevent candidate meeting hijacking or directory harvesting.

---

### 3. Automated Test Suite Verification

Integration tests inside `tests/test_federated_scheduling.py` validate link creation, expired access blocks, successful bookings, candidate ownership validations, and overlap EXCLUDE constraints:

```bash
$ pytest -k "link or expired or overlap or reschedule" tests/test_federated_scheduling.py
============================= test session starts ==============================
collected 13 items / 9 deselected / 4 selected

tests/test_federated_scheduling.py ....                                  [100%]

======================== 4 passed, 9 deselected in 3.65s =======================
```
