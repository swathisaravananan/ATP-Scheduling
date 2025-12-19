
import pandas as pd
from utils.group_exams import group_exam_timings, get_room_requirements
from utils.liv25_api import LIV25API, search_rooms_for_exams
from utils.access_google_sheets import get_sheet_as_df, update_sheet_with_df_with_columns

# Optional Gurobi import
try:
    from utils.gurobi_room_optimizer import build_and_solve_ilp, apply_ilp_assignments_to_dataframe
    GUROBI_AVAILABLE = True
except ImportError:
    GUROBI_AVAILABLE = False
    build_and_solve_ilp = None
    apply_ilp_assignments_to_dataframe = None


class Pipeline2:
    def __init__(self, liv25_base_url: str = None, liv25_api_key: str = None, 
                 liv25_rooms_df: pd.DataFrame = None, use_ilp: bool = True,
                 ilp_objective: str = 'minimize_rooms'):
        """
        Initialize Pipeline2 for room assignment.
        
        Args:
            liv25_base_url: Base URL for LIV25 API
            liv25_api_key: API key for LIV25 authentication
            liv25_rooms_df: DataFrame with room data (alternative to API).
                           Should have columns: 'location', 'start time', 'end time', 'capacity'
            use_ilp: If True, use Gurobi ILP optimizer for room assignment (default: True)
            ilp_objective: Objective function for ILP ('minimize_rooms' or 'minimize_weighted')
        """
        self.liv25_client = LIV25API(base_url=liv25_base_url, api_key=liv25_api_key)
        self.liv25_rooms_df = liv25_rooms_df
        self.use_ilp = use_ilp
        self.ilp_objective = ilp_objective
    
    def get_exam_data_from_master_sheet(self, file_name: str = "FA25 NEW MOCK", 
                                        sheet_name: str = "Exam Schedule"):
        """
        Get exam data from master sheet (after scheduling is complete).
        
        Args:
            file_name: Name of the Google Sheet
            sheet_name: Name of the sheet tab
        
        Returns:
            DataFrame with exam data
        """
        df = get_sheet_as_df(file_name, sheet_name)
        return df
    
    def group_exam_timings(self, df: pd.DataFrame) -> list:
        """
        Group exams by their scheduled timings.
        
        Args:
            df: DataFrame with scheduled exam data
        
        Returns:
            List of grouped exam dictionaries
        """
        return group_exam_timings(df)
    
    def search_rooms_in_liv25(self, exam_groups: list) -> list:
        """
        Search for available rooms in LIV25 for grouped exam timings.
        Can use either API or DataFrame as data source.
        
        Args:
            exam_groups: List of grouped exam dictionaries
        
        Returns:
            List of dictionaries with exam groups and available rooms
        """
        # Get room requirements
        room_requirements = get_room_requirements(exam_groups)
        
        # Search for rooms - use DataFrame if provided, otherwise use API
        if self.liv25_rooms_df is not None:
            # Use DataFrame source
            results = []
            for req in room_requirements:
                available_rooms = self.liv25_client.get_rooms_from_dataframe(
                    df=self.liv25_rooms_df,
                    start_time=req['start_time'],
                    end_time=req['end_time'],
                    capacity=req['min_capacity']
                )
                results.append({
                    'start_time': req['start_time'],
                    'end_time': req['end_time'],
                    'student_count': req['student_count'],
                    'required_capacity': req['min_capacity'],
                    'available_rooms': available_rooms,
                    'room_count': len(available_rooms),
                    'crns': req['crns']
                })
            return results
        else:
            # Use API
            room_search_results = search_rooms_for_exams(room_requirements, self.liv25_client)
            return room_search_results
    
    def _prepare_rooms_dataframe(self, room_search_results: list) -> pd.DataFrame:
        """
        Prepare a unified rooms DataFrame from room_search_results.
        
        Args:
            room_search_results: Results from room search
        
        Returns:
            DataFrame with columns: location, start time, end time, capacity
        """
        all_rooms = []
        seen_rooms = set()  # Track unique rooms by location
        
        for result in room_search_results:
            for room in result.get('available_rooms', []):
                location = (
                    room.get('location') or 
                    room.get('id') or 
                    room.get('room_id') or 
                    room.get('name') or 
                    ''
                )
                
                if not location or location in seen_rooms:
                    continue
                
                seen_rooms.add(location)
                
                room_dict = {
                    'location': location,
                    'start time': room.get('start time') or room.get('start_time'),
                    'end time': room.get('end time') or room.get('end_time'),
                    'capacity': room.get('capacity', 1)
                }
                
                # Copy other room properties
                for key, value in room.items():
                    if key not in ['location', 'id', 'room_id', 'name', 'start time', 'start_time', 
                                  'startTime', 'end time', 'end_time', 'endTime', 'capacity']:
                        room_dict[key] = value
                
                all_rooms.append(room_dict)
        
        if not all_rooms:
            return pd.DataFrame(columns=['location', 'start time', 'end time', 'capacity'])
        
        return pd.DataFrame(all_rooms)
    
    def assign_rooms(self, df: pd.DataFrame, room_search_results: list, 
                     exam_groups: list = None) -> pd.DataFrame:
        """
        Assign rooms to exams based on available rooms from LIV25.
        Uses Gurobi ILP optimizer if use_ilp=True, otherwise uses greedy assignment.
        
        Args:
            df: DataFrame with exam data
            room_search_results: Results from room search
            exam_groups: List of exam group dicts (required if use_ilp=True)
        
        Returns:
            DataFrame with room assignments added
        """
        if self.use_ilp and GUROBI_AVAILABLE:
            return self._assign_rooms_ilp(df, room_search_results, exam_groups)
        else:
            if self.use_ilp and not GUROBI_AVAILABLE:
                print("Warning: ILP requested but Gurobi not available. Using greedy algorithm.")
            return self._assign_rooms_greedy(df, room_search_results)
    
    def _assign_rooms_ilp(self, df: pd.DataFrame, room_search_results: list,
                          exam_groups: list) -> pd.DataFrame:
        """
        Assign rooms using Gurobi ILP optimizer.
        
        Args:
            df: DataFrame with exam data
            room_search_results: Results from room search
            exam_groups: List of exam group dicts
        
        Returns:
            DataFrame with room assignments added
        """
        if not GUROBI_AVAILABLE:
            print("Warning: Gurobi not available. Falling back to greedy algorithm.")
            return self._assign_rooms_greedy(df, room_search_results)
        
        if not exam_groups:
            # Fallback to greedy if no exam groups provided
            return self._assign_rooms_greedy(df, room_search_results)
        
        # Prepare rooms DataFrame
        rooms_df = self._prepare_rooms_dataframe(room_search_results)
        
        if rooms_df.empty:
            # No rooms available
            df = df.copy()
            df['Assigned Room ID'] = ''
            df['Assigned Room Name'] = ''
            df['Assigned Room Location'] = ''
            df['Room Assignment Status'] = 'No rooms available'
            return df
        
        print(f"Solving ILP for {len(exam_groups)} exam groups and {len(rooms_df)} rooms...")
        
        # Solve ILP
        ilp_result = build_and_solve_ilp(
            exam_groups=exam_groups,
            rooms_df=rooms_df,
            objective=self.ilp_objective
        )
        
        status = ilp_result.get('status', 'UNKNOWN')
        print(f"ILP Status: {status}")
        if ilp_result.get('objective_value') is not None:
            print(f"ILP Objective Value: {ilp_result['objective_value']:.2f}")
        print(f"ILP Solve Time: {ilp_result.get('solve_time', 0):.2f} seconds")
        
        # Apply assignments to DataFrame
        df_with_rooms = apply_ilp_assignments_to_dataframe(df, exam_groups, ilp_result, rooms_df=rooms_df)
        
        return df_with_rooms
    
    def _assign_rooms_greedy(self, df: pd.DataFrame, room_search_results: list) -> pd.DataFrame:
        """
        Assign rooms using greedy algorithm (original implementation).
        
        Args:
            df: DataFrame with exam data
            room_search_results: Results from room search
        
        Returns:
            DataFrame with room assignments added
        """
        # Create a mapping from (start_time, end_time) to available rooms
        room_map = {}
        for result in room_search_results:
            key = (result['start_time'], result['end_time'])
            room_map[key] = result['available_rooms']
        
        # Add room assignment columns
        df['Assigned Room ID'] = ''
        df['Assigned Room Name'] = ''
        df['Assigned Room Location'] = ''  # Store location column value
        df['Room Assignment Status'] = ''
        
        # Parse datetime columns for matching
        df['Scheduled Start'] = pd.to_datetime(df['Scheduled Start'], errors='coerce')
        df['Scheduled End'] = pd.to_datetime(df['Scheduled End'], errors='coerce')
        
        # Track room assignments to avoid double-booking
        room_assignments = {}  # {(start, end, room_id): [student_ids]}
        
        for idx, row in df.iterrows():
            if row['Schedule Status'] != 'SCHEDULED':
                df.at[idx, 'Room Assignment Status'] = 'No room needed - exam not scheduled'
                continue
            
            start_time = row['Scheduled Start']
            end_time = row['Scheduled End']
            
            if pd.isna(start_time) or pd.isna(end_time):
                df.at[idx, 'Room Assignment Status'] = 'Invalid time slot'
                continue
            
            key = (start_time, end_time)
            
            if key not in room_map or not room_map[key]:
                df.at[idx, 'Room Assignment Status'] = 'No rooms available'
                continue
            
            # Find an available room
            student_id = str(row['Student ID'])
            assigned = False
            
            for room in room_map[key]:
                # Handle location column (primary identifier)
                room_id = (
                    room.get('location') or 
                    room.get('id') or 
                    room.get('room_id') or 
                    room.get('name') or 
                    ''
                )
                # Room name can be location or a separate name field
                room_name = (
                    room.get('name') or 
                    room.get('room_name') or 
                    room.get('location') or 
                    room_id
                )
                room_capacity = room.get('capacity', 1)
                
                # Verify room availability time matches exam time
                room_start = room.get('start time') or room.get('start_time')
                room_end = room.get('end time') or room.get('end_time')
                
                # If room has specific time windows, verify they cover the exam time
                if room_start and room_end:
                    try:
                        from datetime import datetime
                        room_start_dt = pd.to_datetime(room_start)
                        room_end_dt = pd.to_datetime(room_end)
                        # Check if exam time fits within room availability window
                        if start_time < room_start_dt or end_time > room_end_dt:
                            continue  # Room not available for this time slot
                    except:
                        pass  # If parsing fails, assume room is available
                
                # Check if room is already assigned for this time slot
                assignment_key = (start_time, end_time, room_id)
                current_assignments = room_assignments.get(assignment_key, [])
                
                # Check capacity (assuming 1 student per room for individual exams)
                if len(current_assignments) < room_capacity:
                    # Assign room
                    df.at[idx, 'Assigned Room ID'] = room_id
                    df.at[idx, 'Assigned Room Name'] = room_name
                    df.at[idx, 'Assigned Room Location'] = room.get('location', room_id)  # Store location column
                    df.at[idx, 'Room Assignment Status'] = 'Assigned'
                    
                    # Track assignment
                    if assignment_key not in room_assignments:
                        room_assignments[assignment_key] = []
                    room_assignments[assignment_key].append(student_id)
                    
                    assigned = True
                    break
            
            if not assigned:
                df.at[idx, 'Room Assignment Status'] = 'No available rooms with capacity'
        
        # Add Status column (alias for Room Assignment Status)
        if 'Room Assignment Status' in df.columns:
            df['Status'] = df['Room Assignment Status']
        else:
            df['Status'] = ''
        
        return df
    
    def update_master_sheet_with_rooms(self, df: pd.DataFrame, 
                                      file_name: str = "FA25 NEW MOCK",
                                      sheet_name: str = "Exam Schedule"):
        """
        Update master sheet with room assignments.
        
        Args:
            df: DataFrame with room assignments
            file_name: Name of the Google Sheet
            sheet_name: Name of the sheet tab
        """
        # Use key columns for updating (assuming Student ID and Scheduled Start are unique)
        key_columns = ['Student ID', 'CRN', 'Scheduled Start']
        update_sheet_with_df_with_columns(file_name, sheet_name, df, key_columns)
    
    def update_exam_information_sheet(self, df: pd.DataFrame,
                                      file_name: str = "FA25 NEW MOCK",
                                      sheet_name: str = "EXAM INFORMATION"):
        """
        Update EXAM INFORMATION sheet with room assignments.
        
        Args:
            df: DataFrame with room assignments
            file_name: Name of the Google Sheet
            sheet_name: Name of the sheet tab
        """
        # Remove unwanted columns before updating
        df_to_update = df.copy()
        columns_to_remove = [
            'Assigned Room ID', 
            'Assigned Room Location',
            '5:00 pm the day AFTER the exam',
            '5:00 pm the day BEFORE the exam',
            '5:00 pm the day of the exam',
            '5:00 pm up to a week AFTER the exam',
            '8:00 am the day AFTER the exam',
            '8:00 am the day BEFORE the exam',
            '8:00 am the day of the exam',
            '8:00 am up to a week AFTER the exam'
        ]
        for col in columns_to_remove:
            if col in df_to_update.columns:
                df_to_update = df_to_update.drop(columns=[col])
        
        # Ensure 'Status' column exists (alias for Room Assignment Status for clarity)
        if 'Room Assignment Status' in df_to_update.columns:
            df_to_update['Status'] = df_to_update['Room Assignment Status']
        else:
            df_to_update['Status'] = ''
        
        # Use key columns for updating (assuming Student ID and CRN are unique identifiers)
        key_columns = ['Student ID', 'CRN', 'Scheduled Start']
        print(f"Updating {sheet_name} sheet in {file_name} with room assignments...")
        removed_count = sum(1 for col in columns_to_remove if col in df.columns)
        print(f"  (Removed {removed_count} columns)")
        update_sheet_with_df_with_columns(file_name, sheet_name, df_to_update, key_columns)
        print(f"Successfully updated {sheet_name} sheet")
        
        # Report unassigned students
        unassigned = df_to_update[~df_to_update['Room Assignment Status'].str.contains('Assigned', na=False)]
        if len(unassigned) > 0:
            print(f"\n⚠️  WARNING: {len(unassigned)} student(s) did not get room assignments:")
            for idx, row in unassigned.iterrows():
                student_id = row.get('Student ID', 'N/A')
                crn = row.get('CRN', 'N/A')
                status = row.get('Room Assignment Status', 'N/A')
                print(f"  • Student {student_id} (CRN {crn}): {status}")
        else:
            print(f"\n✓ All students successfully assigned to rooms!")
    
    def process_room_assignment(self, exam_data_file: str = None, 
                                exam_data_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Complete room assignment workflow:
        1. Get exam data
        2. Group exam timings
        3. Search rooms in LIV25
        4. Assign rooms
        5. Update "Exam Schedule" sheet in Google Sheets
        6. Update "EXAM INFORMATION" sheet in Google Sheets
        
        Args:
            exam_data_file: Path to CSV file with exam data (optional)
            exam_data_df: DataFrame with exam data (optional)
        
        Returns:
            DataFrame with room assignments (includes columns: Assigned Room ID, 
            Assigned Room Name, Assigned Room Location, Room Assignment Status)
        """
        # Load exam data
        if exam_data_df is not None:
            df = exam_data_df.copy()
        elif exam_data_file:
            df = pd.read_csv(exam_data_file)
        else:
            # Get from master sheet
            df = self.get_exam_data_from_master_sheet()
        
        # Group exam timings
        print("Grouping exam timings...")
        exam_groups = self.group_exam_timings(df)
        print(f"Found {len(exam_groups)} unique exam time slots")
        
        # Search rooms in LIV25
        print("Searching for rooms in LIV25...")
        room_search_results = self.search_rooms_in_liv25(exam_groups)
        print(f"Room search completed for {len(room_search_results)} time slots")
        
        # Assign rooms
        print("Assigning rooms to exams...")
        df_with_rooms = self.assign_rooms(df, room_search_results, exam_groups=exam_groups)
        
        # Update master sheet (if it exists)
        try:
            print("Updating master sheet with room assignments...")
            self.update_master_sheet_with_rooms(df_with_rooms)
        except Exception as e:
            print(f"Note: Could not update 'Exam Schedule' sheet: {e}")
            print("Continuing with EXAM INFORMATION sheet update...")
        
        # Update EXAM INFORMATION sheet
        print("Updating EXAM INFORMATION sheet with room assignments...")
        self.update_exam_information_sheet(df_with_rooms)
        
        return df_with_rooms