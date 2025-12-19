"""
Gurobi-based Integer Linear Programming optimizer for room assignment.

This module implements an ILP model to optimally assign exam groups (buckets) to rooms,
respecting capacity constraints, availability windows, and preventing overlapping exams
from sharing the same room.
"""

import gurobipy as gp
from gurobipy import GRB
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings


def build_and_solve_ilp(exam_groups: List[Dict], rooms_df: pd.DataFrame,
                        objective: str = 'minimize_rooms',
                        time_overlap_tolerance_minutes: int = 0) -> Dict:
    """
    Build and solve an ILP to assign exam groups to rooms optimally.
    
    Args:
        exam_groups: List of dicts from utils.group_exams.group_exam_timings(df)
            Each dict contains:
              - 'start_time' (datetime): Exam start time
              - 'end_time' (datetime): Exam end time
              - 'student_count' (int): Number of students in this group
              - 'student_ids' (list): List of student IDs
              - 'crns' (list): List of CRNs
              - 'duration' (minutes): Exam duration
              - 'exam_records' (list): List of exam record dicts
        
        rooms_df: pandas DataFrame with room info. Must have:
            - 'location' (str): Room identifier
            - 'start time' (datetime or str): Room availability start
            - 'end time' (datetime or str): Room availability end
            - 'capacity' (int): Room capacity
        
        objective: Objective function type
            - 'minimize_rooms': Minimize total number of rooms used (default)
            - 'minimize_weighted': Minimize weighted room usage (by capacity)
        
        time_overlap_tolerance_minutes: Minutes of tolerance for considering exams overlapping.
            Default 0 means exact overlap detection.
    
    Returns:
        assignment_map: Dict mapping exam group index to list of assigned room locations.
            Format: {group_idx: [room_location1, room_location2, ...]}
        
        Also includes:
            - 'status': 'OPTIMAL', 'INFEASIBLE', 'TIME_LIMIT', etc.
            - 'objective_value': Optimal objective value
            - 'solve_time': Time taken to solve (seconds)
            - 'model': Gurobi model object (for inspection)
    """
    if not exam_groups:
        return {
            'assignment_map': {},
            'status': 'NO_EXAMS',
            'objective_value': 0,
            'solve_time': 0,
            'model': None
        }
    
    if rooms_df.empty:
        return {
            'assignment_map': {},
            'status': 'NO_ROOMS',
            'objective_value': 0,
            'solve_time': 0,
            'model': None
        }
    
    # Normalize room DataFrame columns
    rooms_df = rooms_df.copy()
    col_map = _normalize_room_columns(rooms_df)
    
    # Prepare data structures
    n_groups = len(exam_groups)
    room_locations = rooms_df[col_map['location']].unique().tolist()
    n_rooms = len(room_locations)
    
    # Create room info dictionary for quick lookup
    room_info = {}
    for _, row in rooms_df.iterrows():
        location = str(row[col_map['location']]).strip()
        if not location or location.lower() == 'nan':
            continue
        
        # Parse capacity
        capacity = 1
        if 'capacity' in col_map:
            try:
                capacity = int(float(row[col_map['capacity']]))
            except:
                capacity = 1
        
        # Parse availability times
        room_start = None
        room_end = None
        if 'start time' in col_map:
            try:
                room_start = pd.to_datetime(row[col_map['start time']])
            except:
                pass
        if 'end time' in col_map:
            try:
                room_end = pd.to_datetime(row[col_map['end time']])
            except:
                pass
        
        room_info[location] = {
            'capacity': capacity,
            'start_time': room_start,
            'end_time': room_end
        }
    
    # Create model
    model = gp.Model("RoomAssignment")
    model.setParam('OutputFlag', 0)  # Suppress Gurobi output
    
    # Decision variables following handwritten formulation:
    # x_ij = 1 if exam group i is assigned to room j, 0 otherwise
    x = {}
    for i in range(n_groups):
        for r in room_locations:
            x[i, r] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{r}")
    
    # y_j = 1 if room j is being used, 0 otherwise
    room_used = {}
    for r in room_locations:
        room_used[r] = model.addVar(vtype=GRB.BINARY, name=f"y_{r}")
    
    # Update model to integrate new variables
    model.update()
    
    # Constraint 1: Each exam group must be assigned to exactly one room
    # Following handwritten formulation: Σ x_ij = 1 for each bucket i
    for i in range(n_groups):
        model.addConstr(
            gp.quicksum(x[i, r] for r in room_locations) == 1,
            name=f"assignment_group_{i}"
        )
    
    # Constraint 2: Capacity constraint - total students in room j cannot exceed capacity
    # Following handwritten formulation: Σ n_i * x_ij ≤ C_j for each room j
    for r in room_locations:
        total_students = gp.quicksum(
            exam_groups[i]['student_count'] * x[i, r]
            for i in range(n_groups)
        )
        model.addConstr(
            total_students <= room_info[r]['capacity'],
            name=f"capacity_room_{r}"
        )
    
    # Constraint 3: Room availability - exam time must fit within room's availability window
    for i in range(n_groups):
        group = exam_groups[i]
        exam_start = pd.to_datetime(group['start_time'])
        exam_end = pd.to_datetime(group['end_time'])
        
        for r in room_locations:
            room_start = room_info[r]['start_time']
            room_end = room_info[r]['end_time']
            
            # If room has availability window, enforce it
            if room_start is not None and room_end is not None:
                # Room is available if: room_start <= exam_start and exam_end <= room_end
                # If room is not available, force x[i,r] = 0
                
                # Check if exam starts before room is available
                if exam_start < room_start:
                    # Room not available - force x[i,r] = 0
                    model.addConstr(x[i, r] == 0, name=f"availability_start_{i}_{r}")
                
                # Check if exam ends after room availability ends
                if exam_end > room_end:
                    # Room not available - force x[i,r] = 0
                    model.addConstr(x[i, r] == 0, name=f"availability_end_{i}_{r}")
    
    # Constraint 4: No overlapping exams in the same room
    # If two exam groups overlap in time, they cannot both use the same room
    for i in range(n_groups):
        for j in range(i + 1, n_groups):
            group_i = exam_groups[i]
            group_j = exam_groups[j]
            
            # Check if exams overlap
            if _exams_overlap(group_i, group_j, time_overlap_tolerance_minutes):
                # They cannot share the same room
                for r in room_locations:
                    # x[i,r] + x[j,r] <= 1
                    model.addConstr(x[i, r] + x[j, r] <= 1, 
                                   name=f"no_overlap_{i}_{j}_{r}")
    
    # Constraint 5: Room availability window overlap constraint
    # NOTE: The handwritten formulation has y_j + y_k ≤ 1 if rooms j and k have overlapping availability.
    # However, this constraint seems to prevent using multiple rooms simultaneously, which doesn't make
    # sense for our use case where we need multiple rooms for different exams at the same time.
    # This constraint might apply to a different scenario (e.g., shared resources).
    # For now, we skip this constraint as it makes the problem infeasible when all rooms
    # have overlapping availability windows (which is common in our case).
    # 
    # If needed, this constraint could be:
    # - Applied only to rooms that share resources
    # - Applied only to specific time periods
    # - Removed if not applicable to our use case
    pass  # Skipping room overlap constraint for now
    
    # Constraint 6: Linking constraint x_ij ≤ y_j
    # Following handwritten formulation: if bucket i assigned to room j, then y_j = 1
    for i in range(n_groups):
        for r in room_locations:
            model.addConstr(x[i, r] <= room_used[r], name=f"linking_{i}_{r}")
    
    # Objective function
    if objective == 'minimize_rooms':
        # Following handwritten formulation: minimize Σ y_j
        obj = gp.quicksum(room_used[r] for r in room_locations)
    elif objective == 'minimize_weighted':
        # Minimize weighted room usage (prefer smaller rooms when possible)
        # Weight by inverse capacity to prefer smaller rooms
        obj = gp.quicksum(
            (1.0 / max(room_info[r]['capacity'], 1)) * x[i, r]
            for i in range(n_groups)
            for r in room_locations
        )
    else:
        # Default: minimize total capacity used (encourages using fewer, larger rooms)
        obj = gp.quicksum(
            room_info[r]['capacity'] * x[i, r]
            for i in range(n_groups)
            for r in room_locations
        )
    
    model.setObjective(obj, GRB.MINIMIZE)
    
    # Solve
    try:
        model.optimize()
        solve_time = model.Runtime
        
        # Extract solution
        assignment_map = {}
        if model.status == GRB.OPTIMAL:
            for i in range(n_groups):
                assigned_rooms = []
                for r in room_locations:
                    if x[i, r].X > 0.5:  # Binary variable, check if > 0.5
                        assigned_rooms.append(r)
                assignment_map[i] = assigned_rooms
            
            status = 'OPTIMAL'
            objective_value = model.ObjVal
        elif model.status == GRB.INFEASIBLE:
            status = 'INFEASIBLE'
            objective_value = None
            assignment_map = {}
        elif model.status == GRB.TIME_LIMIT:
            status = 'TIME_LIMIT'
            objective_value = model.ObjVal if model.SolCount > 0 else None
            # Extract best solution found
            assignment_map = {}
            if model.SolCount > 0:
                for i in range(n_groups):
                    assigned_rooms = []
                    for r in room_locations:
                        if x[i, r].X > 0.5:
                            assigned_rooms.append(r)
                    assignment_map[i] = assigned_rooms
        else:
            status = f'STATUS_{model.status}'
            objective_value = None
            assignment_map = {}
        
        return {
            'assignment_map': assignment_map,
            'status': status,
            'objective_value': objective_value,
            'solve_time': solve_time,
            'model': model
        }
    
    except gp.GurobiError as e:
        warnings.warn(f"Gurobi error: {e}")
        return {
            'assignment_map': {},
            'status': 'ERROR',
            'objective_value': None,
            'solve_time': 0,
            'model': model
        }
    except Exception as e:
        warnings.warn(f"Unexpected error in ILP solver: {e}")
        return {
            'assignment_map': {},
            'status': 'ERROR',
            'objective_value': None,
            'solve_time': 0,
            'model': None
        }


def _normalize_room_columns(rooms_df: pd.DataFrame) -> Dict[str, str]:
    """
    Normalize room DataFrame column names to standard format.
    
    Returns:
        Dictionary mapping standard names to actual column names
    """
    col_map = {}
    for col in rooms_df.columns:
        col_lower = col.lower().strip()
        if col_lower in ['location', 'id', 'room_id', 'name'] and 'location' not in col_map:
            col_map['location'] = col
        elif col_lower in ['start time', 'start_time', 'starttime'] and 'start time' not in col_map:
            col_map['start time'] = col
        elif col_lower in ['end time', 'end_time', 'endtime'] and 'end time' not in col_map:
            col_map['end time'] = col
        elif col_lower == 'capacity' and 'capacity' not in col_map:
            col_map['capacity'] = col
    
    # Ensure location exists
    if 'location' not in col_map:
        raise ValueError("Room DataFrame must have a 'location' column (or 'id', 'room_id', 'name')")
    
    return col_map


def _exams_overlap(group1: Dict, group2: Dict, tolerance_minutes: int = 0) -> bool:
    """
    Check if two exam groups overlap in time.
    
    Args:
        group1: First exam group dict with 'start_time' and 'end_time'
        group2: Second exam group dict with 'start_time' and 'end_time'
        tolerance_minutes: Tolerance for overlap detection
    
    Returns:
        True if exams overlap, False otherwise
    """
    start1 = pd.to_datetime(group1['start_time'])
    end1 = pd.to_datetime(group1['end_time'])
    start2 = pd.to_datetime(group2['start_time'])
    end2 = pd.to_datetime(group2['end_time'])
    
    # Add tolerance
    start1 = start1 - pd.Timedelta(minutes=tolerance_minutes)
    end1 = end1 + pd.Timedelta(minutes=tolerance_minutes)
    start2 = start2 - pd.Timedelta(minutes=tolerance_minutes)
    end2 = end2 + pd.Timedelta(minutes=tolerance_minutes)
    
    # Overlap if: max(start1, start2) < min(end1, end2)
    return max(start1, start2) < min(end1, end2)


def apply_ilp_assignments_to_dataframe(df: pd.DataFrame, exam_groups: List[Dict],
                                       ilp_result: Dict, rooms_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Apply ILP assignment results to the original exam DataFrame.
    
    Args:
        df: Original exam DataFrame
        exam_groups: List of exam group dicts (same as passed to build_and_solve_ilp)
        ilp_result: Result dict from build_and_solve_ilp()
        rooms_df: Optional DataFrame with room info (for capacity lookup)
    
    Returns:
        DataFrame with room assignments added
    """
    df = df.copy()
    
    # Initialize assignment columns
    df['Assigned Room ID'] = ''
    df['Assigned Room Name'] = ''
    df['Assigned Room Location'] = ''
    df['Room Assignment Status'] = ''
    
    # Parse datetime columns
    df['Scheduled Start'] = pd.to_datetime(df['Scheduled Start'], errors='coerce')
    df['Scheduled End'] = pd.to_datetime(df['Scheduled End'], errors='coerce')
    
    assignment_map = ilp_result.get('assignment_map', {})
    
    if not assignment_map:
        # No assignments - mark all as unassigned
        df.loc[df['Schedule Status'] == 'SCHEDULED', 'Room Assignment Status'] = 'No rooms assigned by ILP'
        # Add Status column even when no assignments
        df['Status'] = df['Room Assignment Status']
        return df
    
    # Create mapping from (start_time, end_time) to assigned rooms
    time_to_rooms = {}
    for group_idx, assigned_rooms in assignment_map.items():
        if group_idx < len(exam_groups):
            group = exam_groups[group_idx]
            key = (group['start_time'], group['end_time'])
            time_to_rooms[key] = assigned_rooms
    
    # Build room capacity lookup
    room_capacities = {}
    if rooms_df is not None and not rooms_df.empty:
        col_map = _normalize_room_columns(rooms_df)
        for _, room_row in rooms_df.iterrows():
            location = str(room_row[col_map['location']]).strip()
            if 'capacity' in col_map:
                try:
                    capacity = int(float(room_row[col_map['capacity']]))
                    room_capacities[location] = capacity
                except:
                    room_capacities[location] = 1
            else:
                room_capacities[location] = 1
    
    # Track room assignments per time slot to distribute students
    room_usage = {}  # {(start, end, room): [student_ids]}
    
    # Assign rooms to each exam row
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
        
        if key not in time_to_rooms or not time_to_rooms[key]:
            df.at[idx, 'Room Assignment Status'] = 'No rooms assigned by ILP'
            continue
        
        # Get assigned rooms for this time slot
        assigned_rooms = time_to_rooms[key]
        student_id = str(row['Student ID'])
        
        # Find an available room (distribute students across assigned rooms)
        assigned = False
        for room_location in assigned_rooms:
            usage_key = (start_time, end_time, room_location)
            current_students = room_usage.get(usage_key, [])
            
            # Get room capacity from lookup (default: 1 for individual exams)
            room_capacity = room_capacities.get(room_location, 1)
            
            # Check if we can add more students to this room
            if len(current_students) < room_capacity:
                df.at[idx, 'Assigned Room ID'] = room_location
                df.at[idx, 'Assigned Room Name'] = room_location
                df.at[idx, 'Assigned Room Location'] = room_location
                df.at[idx, 'Room Assignment Status'] = 'Assigned (ILP)'
                
                if usage_key not in room_usage:
                    room_usage[usage_key] = []
                room_usage[usage_key].append(student_id)
                assigned = True
                break
        
        if not assigned:
            # All rooms at capacity - this shouldn't happen if ILP solved correctly
            # but handle gracefully
            df.at[idx, 'Room Assignment Status'] = 'All assigned rooms at capacity'
    
    # Add Status column (alias for Room Assignment Status)
    if 'Room Assignment Status' in df.columns:
        df['Status'] = df['Room Assignment Status']
    else:
        df['Status'] = ''
    
    return df

