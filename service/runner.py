from service.pipeline1 import Pipeline1
from service.pipeline2 import Pipeline2
from utils.resolve_time import schedule_special_needs_exams
from utils.resolve_slots import schedule_all
import os

class Runner:
    def __init__(self, liv25_base_url: str = None, liv25_api_key: str = None, 
                 liv25_rooms_df = None):
        """
        Initialize Runner.
        
        Args:
            liv25_base_url: Base URL for LIV25 API
            liv25_api_key: API key for LIV25 authentication
            liv25_rooms_df: DataFrame with room data (alternative to API).
                           Should have columns: 'location', 'start time', 'end time', 'capacity'
        """
        self.p1 = Pipeline1()
        self.p2 = Pipeline2(liv25_base_url=liv25_base_url, liv25_api_key=liv25_api_key,
                           liv25_rooms_df=liv25_rooms_df)
        pass

    def pipeline(self, include_room_assignment: bool = True):
        """
        Main pipeline workflow:
        1. Get faculty and student data (Pipeline1)
        2. Schedule exams (Pipeline1)
        3. Group exam timings and assign rooms (Pipeline2)
        
        Args:
            include_room_assignment: Whether to run room assignment workflow
        """
        # Workflow 1 & 2: Schedule exams
        print("=== Starting Workflow 1 & 2: Exam Scheduling ===")
        faculty_data = self.p1.get_interested_faculty_info()
        student_data = self.p1.get_student_info()
        student_course = self.p1.get_student_exams()
        st_timetables = self.p1.get_timetables()
        student_data = student_data.merge(student_course, how="left", on="Student ID")
        faculty_data = faculty_data.merge(student_data, how="left", on="CRN")
        faculty_data["Duration"] = faculty_data["Instructor Exam Duration"] * faculty_data["Multiplier"]
        faculty_data.drop(columns=["Instructor Exam Duration", "Multiplier"], inplace=True)
        # result = schedule_special_needs_exams(faculty_data, st_timetables)
        result = schedule_all(faculty_data, st_timetables)
        result.to_csv("result1.csv", index=False)
        print(f"Exam scheduling completed. Results saved to result1.csv")
        
        # Workflow 3: Room assignment (if enabled)
        if include_room_assignment:
            print("\n=== Starting Workflow 3: Room Assignment ===")
            # Use the scheduled results for room assignment
            result_with_rooms = self.p2.process_room_assignment(exam_data_df=result)
            result_with_rooms.to_csv("result_with_rooms.csv", index=False)
            print(f"Room assignment completed. Results saved to result_with_rooms.csv")
            
            # Note: process_room_assignment already updates both "Exam Schedule" and "EXAM INFORMATION" sheets
            print("Google Sheets updated with room assignments:")
            print("  - Exam Schedule sheet")
            print("  - EXAM INFORMATION sheet")
            
            return result_with_rooms
        
        return result