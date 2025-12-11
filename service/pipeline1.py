import json
import pandas as pd
from utils.access_google_sheets import get_sheet_as_df, update_sheet_with_df


class Pipeline1:
    def __init__(self):
        pass

    def get_interested_faculty_info(self):
        df = get_sheet_as_df("Copy of ATP Participating Courses", "FA2025_NEW")
        column_name = 'If there is an academic conflict with a scheduled exam, the conflict exam options are...'
        values = ["8:00 am the day of the exam", "5:00 pm the day of the exam", "8:00 am the day BEFORE the exam",
                  "5:00 pm the day BEFORE the exam", "8:00 am the day AFTER the exam",
                  "5:00 pm the day AFTER the exam", "8:00 am up to a week AFTER the exam",
                  "5:00 pm up to a week AFTER the exam",
                  "Conflict exams will be managed internally, the student should contact the instructor", "Other"]
        for v in values:
            df[v] = df[column_name].apply( lambda lst: 'Y' if v in lst else 'N')
        update_sheet_with_df("FA25 NEW MOCK", "Sign Ups", df)
        v1 = ["CRN", "Class start timings", "Days the class is offered", "Instructor Exam Date",
                  "Instructor Exam Duration", "Instructor Exam Time"]
        v1.extend(values)
        df = df[v1]
        return df

    def get_student_info(self):
        df = get_sheet_as_df("Copy of ATP Participating Courses", "New Mock of AIM Student info")
        update_sheet_with_df("FA25 NEW MOCK", "Student Info", df)
        cols = ["School ID", "Tags"]
        df = df[cols]
        df["Multiplier"] = 1.5
        df.rename(columns={'School ID': 'Student ID'}, inplace=True)
        values = ["NOAM", "NOPM"]
        for v in values:
            df[v] = df["Tags"].apply( lambda lst: 'Y' if v in lst else 'N')
        return df

    def get_student_exams(self):
        df = get_sheet_as_df("Copy of ATP Participating Courses", "Student to Course link")
        df.rename(columns={'Course CRN': 'CRN'}, inplace=True)
        return df

    def get_timetables(self):
        path = "timetables/student_timetable.json"
        with open(path, "r") as file:
            timetables = json.load(file)
        return timetables
