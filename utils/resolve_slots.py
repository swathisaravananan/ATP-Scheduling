import pandas as pd
import json
from dateutil import parser
from datetime import datetime, timedelta, time

# -----------------------------------------------------------
# INPUT / OUTPUT PATHS  (adjust if running outside this env)
# -----------------------------------------------------------


# -----------------------------------------------------------
# GENERIC UTILITIES
# -----------------------------------------------------------
DAYMAP = {"M": 0, "T": 1, "W": 2, "R": 3, "F": 4}

def parse_datetime(value, default_date=None):
    """Parse any date/time string robustly. If only time given, combine with default_date."""
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    try:
        return parser.parse(s, default=default_date)
    except:
        pass
    # try typical time-only formats
    formats = ["%H:%M", "%I:%M %p", "%I %p", "%H%M"]
    for fmt in formats:
        try:
            t = datetime.strptime(s, fmt).time()
            if default_date:
                base = default_date.date() if isinstance(default_date, datetime) else default_date
                return datetime.combine(base, t)
            return datetime.combine(datetime.today().date(), t)
        except:
            continue
    raise ValueError(f"Cannot parse datetime/time: {value}")

def parse_time(value):
    return parse_datetime(value).time()

def times_close(t1, t2, tolerance_minutes=5):
    """Match times with +/- tolerance to handle differences like 11 vs 11:00 AM."""
    dt1 = datetime.combine(datetime.today(), t1)
    dt2 = datetime.combine(datetime.today(), t2)
    return abs((dt1 - dt2).total_seconds()) <= tolerance_minutes * 60

def overlaps(s1, e1, s2, e2):
    return max(s1, s2) < min(e1, e2)


# -----------------------------------------------------------
# LOAD TIMETABLE JSON
# -----------------------------------------------------------
def load_timetable(json_path):
    """
    Returns:
      dict: student_id -> list of slots, each slot is:
            (weekday_int, start_time, end_time, crn or None)
    JSON format is NOT modified.
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    timetable = {}

    for student in data.get("students", []):
        sid = str(student["student_id"])
        timetable[sid] = []

        for day_block in student.get("Timings", []):
            day_name = day_block.get("Day", "").strip()

            # Convert to weekday_int robustly
            wd = None
            try:
                wd = parser.parse(day_name).weekday()
            except:
                d = day_name.upper()
                if d.startswith("MON") or d == "M": wd = 0
                elif d.startswith("TUE") or d == "T": wd = 1
                elif d.startswith("WED") or d == "W": wd = 2
                elif d.startswith("THU") or d == "R": wd = 3
                elif d.startswith("FRI") or d == "F": wd = 4
                elif d.startswith("SAT") or d == "S": wd = 5
                elif d.startswith("SUN") or d == "U": wd = 6

            if wd is None:
                continue

            for slot in day_block.get("Slots", []):
                st_raw = slot.get("start_time")
                et_raw = slot.get("end_time")
                if not st_raw or not et_raw:
                    continue

                try:
                    st = parse_time(st_raw)
                    et = parse_time(et_raw)
                except:
                    continue

                timetable[sid].append((wd, st, et, None))  # CRN tags added later

    return timetable


# -----------------------------------------------------------
# TAG TIMETABLE WITH CRN FROM CSV (in-memory only)
# -----------------------------------------------------------
def tag_slots_with_crn(df, timetable):
    """
    For each row in CSV, map class days + class start time to correct
    timetable slot for that student. Tag that slot with CRN (in-memory only).
    """
    for _, row in df.iterrows():
        sid = str(row["Student ID"]).strip()
        crn = str(row["CRN"]).strip()
        days_str = str(row["Days the class is offered"]).strip()
        class_start_raw = row["Class start timings"]

        if sid not in timetable:
            continue

        try:
            class_start = parse_time(class_start_raw)
        except:
            continue

        # Format A: "M, T, W"
        day_letters = [d.strip().upper() for d in days_str.split(",") if d.strip()]

        for d in day_letters:
            if d not in DAYMAP:
                continue
            wd = DAYMAP[d]

            # Find matching slot by weekday + start time
            slots = timetable[sid]
            for i, (slot_wd, slot_st, slot_et, slot_crn) in enumerate(slots):
                if slot_wd == wd and times_close(slot_st, class_start):
                    slots[i] = (slot_wd, slot_st, slot_et, crn)
                    break


# -----------------------------------------------------------
# CHECK CONFLICT WITH STUDENT TIMETABLE
# -----------------------------------------------------------
def timetable_conflict(slots, start_dt, end_dt, ignore_crn):
    weekday = start_dt.weekday()
    for (wd, st, et, slot_crn) in slots:
        if wd != weekday:
            continue
        if slot_crn == ignore_crn:
            continue  # allow exam overlapping its own class
        slot_s = datetime.combine(start_dt.date(), st)
        slot_e = datetime.combine(start_dt.date(), et)
        if overlaps(start_dt, end_dt, slot_s, slot_e):
            return True
    return False


# -----------------------------------------------------------
# CHECK NOAM / NOPM
# -----------------------------------------------------------
def check_noam_nopm(row, start_dt, end_dt):
    noam = str(row.get("NOAM", "")).upper() == "Y"
    nopm = str(row.get("NOPM", "")).upper() == "Y"

    if noam and start_dt.time() < time(9, 0):
        return False
    if nopm and end_dt.time() > time(18, 0):
        return False
    return True


# -----------------------------------------------------------
# PARSE DURATION
# -----------------------------------------------------------
def parse_duration(value):
    if value is None or str(value).strip() == "":
        return 0
    v = str(value)
    if ":" in v:
        h, m = v.split(":", 1)
        return int(h) * 60 + int(m)
    try:
        return int(float(v))
    except:
        return 0


# -----------------------------------------------------------
# BUILD ALTERNATIVE CANDIDATES
# -----------------------------------------------------------
def build_candidates(row, inst_dt):
    candidates = [("Instructor", inst_dt)]

    rules = [
        ("8:00 am the day of the exam", 0, time(8, 0)),
        ("5:00 pm the day of the exam", 0, time(17, 0)),
        ("8:00 am the day BEFORE the exam", -1, time(8, 0)),
        ("5:00 pm the day BEFORE the exam", -1, time(17, 0)),
        ("8:00 am the day AFTER the exam", 1, time(8, 0)),
        ("5:00 pm the day AFTER the exam", 1, time(17, 0)),
    ]

    for col, offset, fixed_time in rules:
        if str(row.get(col, "")).upper() == "Y":
            dt = datetime.combine((inst_dt + timedelta(days=offset)).date(), fixed_time)
            candidates.append((col, dt))

    # Up to a week after
    week_col = None
    for col in row.index:
        lc = col.lower()
        if "week" in lc and "after" in lc:
            week_col = col
            break

    if week_col and str(row[week_col]).upper() == "Y":
        for d in range(1, 8):
            for t in [time(8, 0), time(17, 0)]:
                dt = datetime.combine((inst_dt + timedelta(days=d)).date(), t)
                label = f"{week_col}+{d}@{t.strftime('%H:%M')}"
                candidates.append((label, dt))

    return candidates


# -----------------------------------------------------------
# TRY TO SCHEDULE ONE EXAM
# -----------------------------------------------------------
def schedule_exam(row, timetable_slots, existing_exams):
    # Parse instructor datetime
    try:
        inst_dt = parse_datetime(
            f"{row['Instructor Exam Date']} {row['Instructor Exam Time']}"
        )
    except:
        return None, "Invalid instructor date/time"

    duration = parse_duration(row["Duration"])
    exam_crn = str(row["CRN"]).strip()

    candidates = build_candidates(row, inst_dt)

    for label, start_dt in candidates:
        end_dt = start_dt + timedelta(minutes=duration)

        # NOAM/NOPM
        if not check_noam_nopm(row, start_dt, end_dt):
            continue

        # Class timetable conflict (except own class)
        if timetable_conflict(timetable_slots, start_dt, end_dt, ignore_crn=exam_crn):
            continue

        # Exam-to-exam conflict
        conflict = False
        for (other_s, other_e) in existing_exams:
            if overlaps(start_dt, end_dt, other_s, other_e):
                conflict = True
                break
        if conflict:
            continue

        # Found valid slot
        return (start_dt, end_dt, label), None

    return None, "No available slot"


# -----------------------------------------------------------
# MAIN SCHEDULING PROCESS
# -----------------------------------------------------------
def schedule_all(df, timetable):
    tag_slots_with_crn(df, timetable)

    results = []
    exams_for_student = {}

    for _, row in df.iterrows():
        sid = str(row["Student ID"]).strip()
        slots = timetable.get(sid, [])
        existing = exams_for_student.get(sid, [])

        scheduled, error = schedule_exam(row, slots, existing)

        out = row.to_dict()

        if scheduled:
            s, e, label = scheduled
            out["Scheduled Start"] = s.strftime("%Y-%m-%d %H:%M")
            out["Scheduled End"] = e.strftime("%Y-%m-%d %H:%M")
            out["Scheduled Label"] = label
            out["Schedule Status"] = "SCHEDULED"
            existing.append((s, e))
            exams_for_student[sid] = existing
        else:
            out["Scheduled Start"] = ""
            out["Scheduled End"] = ""
            out["Scheduled Label"] = ""
            out["Schedule Status"] = error

        results.append(out)

    outdf = pd.DataFrame(results)
    return outdf
