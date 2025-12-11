import pandas as pd
import json
from datetime import datetime, timedelta, time
import re

# -------------------------
# Helper parsing functions
# -------------------------
def parse_date(d):
    if pd.isna(d):
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(d).strip(), fmt).date()
        except:
            pass
    return pd.to_datetime(d).date()

def parse_time(t):
    if pd.isna(t):
        return None
    s = str(t).strip().lower().replace(".", "")
    try:
        return pd.to_datetime(s).time()
    except:
        pass
    m = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)?', s)
    if m:
        hh = int(m.group(1))
        mm = int(m.group(2))
        ampm = m.group(3)
        if ampm:
            if ampm == "pm" and hh != 12:
                hh += 12
            if ampm == "am" and hh == 12:
                hh = 0
        return time(hh, mm)
    raise ValueError(f"Unrecognized time format: {t}")

def parse_duration_to_minutes(d):
    if pd.isna(d):
        return 0
    if isinstance(d, (int, float)):
        return int(d)
    s = str(d).strip().lower()
    m = re.match(r'(\d+):(\d{2})', s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.match(r'(?:(\d+)h)?\s*(?:(\d+)m)?', s)
    if m and (m.group(1) or m.group(2)):
        return int(m.group(1) or 0) * 60 + int(m.group(2) or 0)
    m = re.match(r'(\d+)\s*m', s)
    if m:
        return int(m.group(1))
    m = re.match(r'(\d+\.\d+)', s)
    if m:
        return int(float(m.group(1)) * 60)
    if s.isdigit():
        return int(s)
    raise ValueError(f"Unrecognized duration: {d}")

def dt_combine(d, t):
    return datetime.combine(d, t)

def overlaps(a_start, a_end, b_start, b_end):
    return not (a_end <= b_start or b_end <= a_start)

def weekday_name_from_date(d):
    return d.strftime("%A")

# ============================================================
#                 MAIN SCHEDULING FUNCTION
# ============================================================
def schedule_special_needs_exams(df, timetable_json):

    # -------------------------------------
    # Build student timetable from JSON
    # -------------------------------------
    student_timetable = {}
    for stu in timetable_json.get("students", []):
        sid = str(stu["student_id"])
        daymap = {}
        for item in stu.get("Timings", []):
            day = item["Day"].lower()
            slots = []
            for s in item["Slots"]:
                st = parse_time(s["start_time"])
                et = parse_time(s["end_time"])
                slots.append((st, et))
            daymap[day] = slots
        student_timetable[sid] = daymap

    # Map column names safely
    colmap = {c.lower().strip(): c for c in df.columns}

    def get_csv_flag(row, label):
        label = label.lower()
        for k,v in colmap.items():
            if label == k or label in k:
                val = row[v]
                if pd.isna(val):
                    return False
                return str(val).strip().upper() in ("Y","YES","1","TRUE")
        return False

    priority_labels = [
        ("same_time", "Instructor Exam Time"),
        ("day_of_8am", "8:00 am the day of the exam"),
        ("day_of_5pm", "5:00 pm the day of the exam"),
        ("day_before_8am", "8:00 am the day BEFORE the exam"),
        ("day_before_5pm", "5:00 pm the day BEFORE the exam"),
        ("day_after_8am", "8:00 am the day AFTER the exam"),
        ("day_after_5pm", "5:00 pm the day AFTER the exam"),
        ("week_after_8am", "8:00 am up to a week AFTER the exam"),
        ("week_after_5pm", "5:00 pm up to a week AFTER the exam"),
    ]

    # Mapping date offsets
    offset_map = {
        "day_of_8am": (0, time(8,0)),
        "day_of_5pm": (0, time(17,0)),
        "day_before_8am": (-1, time(8,0)),
        "day_before_5pm": (-1, time(17,0)),
        "day_after_8am": (1, time(8,0)),
        "day_after_5pm": (1, time(17,0)),
    }

    def candidate_starts(row):
        inst_date = parse_date(row[colmap["instructor exam date"]])
        inst_time = parse_time(row[colmap["instructor exam time"]])
        duration = parse_duration_to_minutes(row[colmap.get("duration", "Duration")])

        # Priority 1: Same time
        yield dt_combine(inst_date, inst_time), "same_time"

        # Other priority slots
        for key,label in priority_labels:
            if key == "same_time":
                continue
            if not get_csv_flag(row, label):
                continue

            if key in offset_map:
                days, t = offset_map[key]
                yield dt_combine(inst_date + timedelta(days=days), t), label

            elif key.startswith("week_after"):
                t = time(8,0) if "8am" in key else time(17,0)
                for d in range(1,8):
                    yield dt_combine(inst_date + timedelta(days=d), t), f"{label} (day+{d})"

    # NOAM/NOPM constraints
    def within_limits(start, end, noam, nopm):
        if noam and start.time() < time(9,0):
            return False
        if nopm and end.time() > time(18,0):
            return False
        return True

    # Check recurring timetable conflict
    def timetable_conflict(sid, start, end):
        day = weekday_name_from_date(start.date()).lower()
        if sid not in student_timetable:
            return False
        for st,et in student_timetable[sid].get(day, []):
            busy_start = dt_combine(start.date(), st)
            busy_end = dt_combine(start.date(), et)
            if overlaps(start, end, busy_start, busy_end):
                return True
        return False

    # Track student exam conflicts
    scheduled_intervals = {}

    output = []

    for _, row in df.iterrows():
        sid = str(row[colmap.get("student id", "Student ID")])
        crn = row[colmap.get("crn", "CRN")]

        inst_date = parse_date(row[colmap["instructor exam date"]])
        inst_time = parse_time(row[colmap["instructor exam time"]])
        duration = parse_duration_to_minutes(row[colmap.get("duration", "Duration")])
        noam = get_csv_flag(row, "NOAM")
        nopm = get_csv_flag(row, "NOPM")

        scheduled = False
        final_start = None
        final_end = None
        reason = None

        for start, why in candidate_starts(row):
            end = start + timedelta(minutes=duration)

            if not within_limits(start, end, noam, nopm):
                continue
            if timetable_conflict(sid, start, end):
                continue

            # check student's other scheduled exams
            if sid in scheduled_intervals:
                conflict = any(overlaps(start, end, s,e) for s,e,_ in scheduled_intervals[sid])
                if conflict:
                    continue

            # SUCCESS
            scheduled = True
            final_start = start
            final_end = end
            reason = why
            scheduled_intervals.setdefault(sid, []).append((start, end, crn))
            break

        output.append({
            "CRN": crn,
            "Student ID": sid,
            "Instructor Exam Date": inst_date,
            "Instructor Exam Time": inst_time,

            # separate date/time for readability
            "Scheduled Exam Date": final_start.date() if final_start else None,
            "Scheduled Start Time": final_start.time() if final_start else None,
            "Scheduled End Time": final_end.time() if final_end else None,

            "Duration (min)": duration,
            "Scheduled Reason": reason,
            "Status": "Scheduled" if scheduled else "Unable to schedule"
        })

    return pd.DataFrame(output)
