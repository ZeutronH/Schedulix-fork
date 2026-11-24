from app.services.scheduler import HybridScheduler, Job


def make_job(priority, duration):
    return Job(
        assignment_id="a",
        faculty_id="f",
        subject_id="s",
        section_id="sec",
        duration=duration,
        priority=priority,
        sessions=1,
        capacity=40,
        room_type="CLASSROOM",
        subject_name="Test",
        faculty_name="Teacher",
        session_type="LECTURE"
    )


def test_hybrid_score():
    high = make_job(10, 60)
    low = make_job(1, 120)

    scheduler = object.__new__(HybridScheduler)
    scheduler.mode = "HYBRID"
    scheduler.priority_weight = 0.65
    scheduler.sjf_weight = 0.35

    high_score = scheduler.get_score(high, 60, 120)
    low_score = scheduler.get_score(low, 60, 120)

    assert high_score > low_score


def test_priority_score():
    scheduler = object.__new__(HybridScheduler)
    scheduler.mode = "PRIORITY"

    high = make_job(10, 120)
    low = make_job(5, 60)

    assert scheduler.get_score(high, 60, 120) == 1
    assert scheduler.get_score(low, 60, 120) == 0.5


def test_sjf_score():
    scheduler = object.__new__(HybridScheduler)
    scheduler.mode = "SJF"

    short = make_job(5, 60)
    long = make_job(5, 120)

    assert scheduler.get_score(short, 60, 120) == 1
    assert scheduler.get_score(long, 60, 120) == 0


def test_hybrid_weights():
    scheduler = object.__new__(HybridScheduler)
    scheduler.mode = "HYBRID"
    scheduler.priority_weight = 0.65
    scheduler.sjf_weight = 0.35

    job = make_job(10, 60)

    assert scheduler.get_score(job, 60, 120) == 1.0


def test_lecture_duration():
    job = make_job(5, 60)
    assert job.duration == 60


def test_laboratory_duration():
    job = make_job(5, 120)
    assert job.duration == 120


def test_shorter_job_preference():
    scheduler = object.__new__(HybridScheduler)
    scheduler.mode = "SJF"

    short = make_job(5, 60)
    long = make_job(5, 120)

    assert scheduler.get_score(short, 60, 120) > (
        scheduler.get_score(long, 60, 120)
    )