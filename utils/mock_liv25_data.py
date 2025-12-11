"""
Mock LIV25 room data generator for testing room assignment without API integration.

This module provides functions to generate realistic mock room data that can be used
for testing the ILP optimizer and room assignment workflow.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random


def generate_mock_rooms(num_rooms: int = 50,
                       start_date: datetime = None,
                       end_date: datetime = None,
                       base_capacity: int = 20,
                       capacity_range: tuple = (10, 50)) -> pd.DataFrame:
    """
    Generate mock room data for LIV25.
    
    Args:
        num_rooms: Number of rooms to generate
        start_date: Start date for room availability (default: today)
        end_date: End date for room availability (default: 30 days from start)
        base_capacity: Base room capacity
        capacity_range: (min, max) capacity range for random variation
    
    Returns:
        DataFrame with columns: location, start time, end time, capacity
    """
    if start_date is None:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if end_date is None:
        end_date = start_date + timedelta(days=30)
    
    rooms = []
    
    # Generate room names (mix of building types)
    building_prefixes = ['LIB', 'SCI', 'ENG', 'BUS', 'ART', 'HALL']
    room_types = ['A', 'B', 'C', 'D', 'E']
    
    for i in range(num_rooms):
        building = random.choice(building_prefixes)
        floor = random.randint(1, 5)
        room_num = random.randint(100, 599)
        room_type = random.choice(room_types)
        
        location = f"{building}-{floor}{room_num:03d}{room_type}"
        
        # Random capacity within range
        capacity = random.randint(capacity_range[0], capacity_range[1])
        
        # Room availability window (most rooms available 8 AM - 10 PM)
        # Some rooms have different hours
        if random.random() < 0.8:  # 80% of rooms: standard hours
            room_start = start_date.replace(hour=8, minute=0)
            room_end = end_date.replace(hour=22, minute=0)
        else:  # 20% of rooms: extended or limited hours
            if random.random() < 0.5:
                room_start = start_date.replace(hour=6, minute=0)  # Early morning
                room_end = end_date.replace(hour=23, minute=0)  # Late night
            else:
                room_start = start_date.replace(hour=9, minute=0)  # Late start
                room_end = end_date.replace(hour=18, minute=0)  # Early end
        
        rooms.append({
            'location': location,
            'start time': room_start,
            'end time': room_end,
            'capacity': capacity
        })
    
    return pd.DataFrame(rooms)


def generate_mock_rooms_for_exams(exam_groups: List[Dict],
                                  num_rooms_per_slot: int = 5,
                                  capacity_range: tuple = (15, 40)) -> pd.DataFrame:
    """
    Generate mock rooms specifically tailored to exam time slots.
    Ensures rooms are available during exam times.
    
    Args:
        exam_groups: List of exam group dicts from group_exam_timings()
        num_rooms_per_slot: Number of rooms to generate per unique time slot
        capacity_range: (min, max) capacity range
    
    Returns:
        DataFrame with columns: location, start time, end time, capacity
    """
    if not exam_groups:
        return generate_mock_rooms(num_rooms=20)
    
    rooms = []
    building_prefixes = ['LIB', 'SCI', 'ENG', 'BUS', 'ART', 'HALL']
    room_types = ['A', 'B', 'C', 'D', 'E']
    
    # Get unique time slots
    time_slots = {}
    for group in exam_groups:
        start = pd.to_datetime(group['start_time'])
        end = pd.to_datetime(group['end_time'])
        key = (start.date(), start.time(), end.time())
        
        if key not in time_slots:
            time_slots[key] = {
                'start_time': start,
                'end_time': end,
                'student_count': group['student_count']
            }
    
    room_counter = 1
    
    for (date, start_time, end_time), slot_info in time_slots.items():
        # Generate rooms for this time slot
        required_capacity = slot_info['student_count']
        rooms_needed = max(num_rooms_per_slot, 
                          (required_capacity // capacity_range[1]) + 1)
        
        for i in range(rooms_needed):
            building = random.choice(building_prefixes)
            floor = random.randint(1, 5)
            room_num = 100 + room_counter
            room_type = random.choice(room_types)
            
            location = f"{building}-{floor}{room_num:03d}{room_type}"
            capacity = random.randint(capacity_range[0], capacity_range[1])
            
            # Room availability: start 1 hour before exam, end 1 hour after
            room_start = slot_info['start_time'] - timedelta(hours=1)
            room_end = slot_info['end_time'] + timedelta(hours=1)
            
            rooms.append({
                'location': location,
                'start time': room_start,
                'end time': room_end,
                'capacity': capacity
            })
            
            room_counter += 1
    
    return pd.DataFrame(rooms)


def load_mock_rooms_from_csv(file_path: str = "mock_rooms.csv") -> pd.DataFrame:
    """
    Load mock rooms from a CSV file, or generate if file doesn't exist.
    
    Args:
        file_path: Path to CSV file
    
    Returns:
        DataFrame with room data
    """
    try:
        df = pd.read_csv(file_path)
        # Ensure datetime columns are parsed
        if 'start time' in df.columns:
            df['start time'] = pd.to_datetime(df['start time'])
        if 'end time' in df.columns:
            df['end time'] = pd.to_datetime(df['end time'])
        return df
    except FileNotFoundError:
        print(f"Mock rooms file not found: {file_path}")
        print("Generating new mock rooms...")
        df = generate_mock_rooms()
        df.to_csv(file_path, index=False)
        print(f"Saved mock rooms to {file_path}")
        return df


def create_sample_mock_rooms() -> pd.DataFrame:
    """
    Create a small sample of mock rooms for quick testing.
    
    Returns:
        DataFrame with 20 sample rooms
    """
    return generate_mock_rooms(
        num_rooms=20,
        base_capacity=20,
        capacity_range=(10, 30)
    )

