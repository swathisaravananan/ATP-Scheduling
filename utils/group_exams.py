import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple


def group_exam_timings(df: pd.DataFrame) -> List[Dict]:
    """
    Group exams by their scheduled start and end times.
    Only includes exams with status 'SCHEDULED'.
    
    Args:
        df: DataFrame with columns 'Scheduled Start', 'Scheduled End', 'Schedule Status', 
            'Student ID', 'CRN', 'Duration'
    
    Returns:
        List of dictionaries, each containing:
        - 'start_time': datetime of exam start
        - 'end_time': datetime of exam end
        - 'student_count': number of students in this time slot
        - 'student_ids': list of student IDs
        - 'crns': list of unique CRNs
        - 'duration': duration in minutes
        - 'exam_records': list of row indices or records
    """
    # Filter only scheduled exams
    scheduled_df = df[df['Schedule Status'] == 'SCHEDULED'].copy()
    
    if scheduled_df.empty:
        return []
    
    # Parse datetime columns
    scheduled_df['Scheduled Start'] = pd.to_datetime(scheduled_df['Scheduled Start'], errors='coerce')
    scheduled_df['Scheduled End'] = pd.to_datetime(scheduled_df['Scheduled End'], errors='coerce')
    
    # Remove rows with invalid datetime
    scheduled_df = scheduled_df.dropna(subset=['Scheduled Start', 'Scheduled End'])
    
    if scheduled_df.empty:
        return []
    
    # Group by start and end time
    grouped = scheduled_df.groupby(['Scheduled Start', 'Scheduled End'])
    
    groups = []
    for (start_time, end_time), group in grouped:
        student_ids = group['Student ID'].tolist()
        crns = group['CRN'].unique().tolist()
        duration = group['Duration'].iloc[0] if not group['Duration'].isna().all() else None
        
        groups.append({
            'start_time': start_time,
            'end_time': end_time,
            'student_count': len(student_ids),
            'student_ids': student_ids,
            'crns': crns,
            'duration': duration,
            'exam_records': group.to_dict('records')
        })
    
    # Sort by start time
    groups.sort(key=lambda x: x['start_time'])
    
    return groups


def get_room_requirements(groups: List[Dict]) -> List[Dict]:
    """
    Calculate room requirements for each exam group.
    This can include capacity requirements, special needs, etc.
    
    Args:
        groups: List of grouped exam dictionaries from group_exam_timings()
    
    Returns:
        List of dictionaries with room requirements
    """
    requirements = []
    
    for group in groups:
        # Calculate minimum capacity needed (1 student per room for individual exams)
        # You can modify this logic based on your requirements
        min_capacity = group['student_count']
        
        # Check for special needs (NOAM, NOPM) from exam records
        has_special_needs = False
        for record in group['exam_records']:
            if record.get('NOAM') == 'Y' or record.get('NOPM') == 'Y':
                has_special_needs = True
                break
        
        requirements.append({
            'start_time': group['start_time'],
            'end_time': group['end_time'],
            'min_capacity': min_capacity,
            'student_count': group['student_count'],
            'has_special_needs': has_special_needs,
            'duration_minutes': group['duration'],
            'crns': group['crns']
        })
    
    return requirements


