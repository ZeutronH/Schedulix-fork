-- ============================================================================
-- SCHEDULIX DBMS DEMONSTRATION: POSTGRESQL FUNCTIONS AND TRIGGERS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. AUDIT TRIGGER
-- Automatically logs INSERT, UPDATE, and DELETE operations on scheduled_classes
-- and faculty_assignments directly into the audit_logs table.
-- Demonstrates: Database-level audit compliance, decoupling auditing from app logic.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION audit_entity_change_trigger()
RETURNS TRIGGER AS $$
DECLARE
    entity_name VARCHAR(100);
    record_id VARCHAR(36);
    action_type VARCHAR(100);
    log_details JSONB;
BEGIN
    entity_name := TG_TABLE_NAME;
    
    IF (TG_OP = 'DELETE') THEN
        action_type := 'SQL_TRIGGER_DELETE';
        record_id := OLD.id;
        log_details := to_jsonb(OLD);
    ELSIF (TG_OP = 'UPDATE') THEN
        action_type := 'SQL_TRIGGER_UPDATE';
        record_id := NEW.id;
        log_details := jsonb_build_object(
            'old', to_jsonb(OLD),
            'new', to_jsonb(NEW)
        );
    ELSIF (TG_OP = 'INSERT') THEN
        action_type := 'SQL_TRIGGER_INSERT';
        record_id := NEW.id;
        log_details := to_jsonb(NEW);
    END IF;

    INSERT INTO audit_logs (id, admin_id, action, entity_type, entity_id, details, created_at)
    VALUES (
        gen_random_uuid()::text,
        NULL,
        action_type,
        entity_name,
        record_id,
        log_details::json,
        NOW()
    );

    IF (TG_OP = 'DELETE') THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Attach audit trigger to scheduled_classes
DROP TRIGGER IF EXISTS trg_audit_scheduled_classes ON scheduled_classes;
CREATE TRIGGER trg_audit_scheduled_classes
AFTER INSERT OR UPDATE OR DELETE ON scheduled_classes
FOR EACH ROW EXECUTE FUNCTION audit_entity_change_trigger();

-- Attach audit trigger to faculty_assignments
DROP TRIGGER IF EXISTS trg_audit_faculty_assignments ON faculty_assignments;
CREATE TRIGGER trg_audit_faculty_assignments
AFTER INSERT OR UPDATE OR DELETE ON faculty_assignments
FOR EACH ROW EXECUTE FUNCTION audit_entity_change_trigger();


-- ----------------------------------------------------------------------------
-- 2. AVAILABILITY VALIDATION TRIGGER
-- Prevents invalid (start >= end) or overlapping availability windows for faculty.
-- Demonstrates: Declarative business constraint enforcement at database layer.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_faculty_availability_trigger()
RETURNS TRIGGER AS $$
DECLARE
    overlap_count INTEGER;
BEGIN
    -- Check that start_time is strictly earlier than end_time
    IF NEW.start_time >= NEW.end_time THEN
        RAISE EXCEPTION 'Invalid availability time window: start_time (%) must be earlier than end_time (%)',
            NEW.start_time, NEW.end_time
            USING ERRCODE = 'check_violation';
    END IF;

    -- Check for overlapping availability blocks on the same weekday for the same faculty
    SELECT COUNT(*) INTO overlap_count
    FROM faculty_availability
    WHERE faculty_id = NEW.faculty_id
      AND weekday = NEW.weekday
      AND id <> COALESCE(NEW.id, '')
      AND (
          (NEW.start_time >= start_time AND NEW.start_time < end_time)
          OR (NEW.end_time > start_time AND NEW.end_time <= end_time)
          OR (NEW.start_time <= start_time AND NEW.end_time >= end_time)
      );

    IF overlap_count > 0 THEN
        RAISE EXCEPTION 'Faculty availability clash: an overlapping availability window already exists for faculty % on weekday %',
            NEW.faculty_id, NEW.weekday
            USING ERRCODE = 'exclusion_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_faculty_availability ON faculty_availability;
CREATE TRIGGER trg_validate_faculty_availability
BEFORE INSERT OR UPDATE ON faculty_availability
FOR EACH ROW EXECUTE FUNCTION validate_faculty_availability_trigger();


-- ----------------------------------------------------------------------------
-- 3. TIMETABLE SESSION MODIFICATION TRIGGER
-- Detects manual modification of scheduled class sessions and marks manual_override = true.
-- Ensures session timing consistency: start_minute < end_minute.
-- Demonstrates: Data integrity and automatic modification flag maintenance.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION maintain_session_metadata_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate session timing
    IF NEW.end_minute <= NEW.start_minute THEN
        RAISE EXCEPTION 'Invalid session duration: end_minute (%) must be greater than start_minute (%)',
            NEW.end_minute, NEW.start_minute
            USING ERRCODE = 'check_violation';
    END IF;

    -- If room, weekday, or timeslot was changed, automatically flag manual_override
    IF (TG_OP = 'UPDATE') THEN
        IF (NEW.room_id <> OLD.room_id OR NEW.weekday <> OLD.weekday OR
            NEW.start_minute <> OLD.start_minute OR NEW.end_minute <> OLD.end_minute) THEN
            NEW.manual_override := TRUE;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_maintain_session_metadata ON scheduled_classes;
CREATE TRIGGER trg_maintain_session_metadata
BEFORE INSERT OR UPDATE ON scheduled_classes
FOR EACH ROW EXECUTE FUNCTION maintain_session_metadata_trigger();
