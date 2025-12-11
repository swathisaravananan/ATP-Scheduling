import requests
from typing import Dict, List, Optional, Union
from datetime import datetime
import json
import pandas as pd


class LIV25API:
    """
    Client for interacting with LIV25 API to search for available rooms.
    """
    
    def __init__(self, base_url: str = None, api_key: str = None):
        """
        Initialize LIV25 API client.
        
        Args:
            base_url: Base URL for LIV25 API (e.g., "https://liv25.example.com/api")
            api_key: API key for authentication (if required)
        """
        self.base_url = base_url or "https://liv25.example.com/api"  # Update with actual URL
        self.api_key = api_key
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def get_available_rooms(self, start_time: datetime, end_time: datetime, 
                           capacity: int = 1, special_needs: bool = False) -> List[Dict]:
        """
        Search for available rooms in LIV25 for a given time slot.
        
        Args:
            start_time: Start datetime of the exam
            end_time: End datetime of the exam
            capacity: Minimum room capacity required
            special_needs: Whether special accommodations are needed
        
        Returns:
            List of available rooms with their details. Each room dict should have:
            - 'location' (or 'id', 'room_id', 'name'): Room identifier
            - 'start time' (or 'start_time'): Room availability start time
            - 'end time' (or 'end_time'): Room availability end time
            - Other room properties (capacity, etc.)
        """
        # Format datetime for API
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Construct API endpoint (adjust based on actual LIV25 API structure)
        endpoint = f"{self.base_url}/rooms/search"
        
        payload = {
            'start_time': start_str,
            'end_time': end_str,
            'capacity': capacity,
            'special_needs': special_needs
        }
        
        try:
            response = self.session.get(endpoint, params=payload, timeout=30)
            response.raise_for_status()
            
            # Parse response (adjust based on actual API response format)
            data = response.json()
            
            # Expected response format: {"rooms": [{"location": "...", "start time": "...", "end time": "...", ...}]}
            rooms = []
            if isinstance(data, dict) and 'rooms' in data:
                rooms = data['rooms']
            elif isinstance(data, list):
                rooms = data
            else:
                return []
            
            # Normalize column names to handle variations
            normalized_rooms = []
            for room in rooms:
                normalized_room = {}
                # Handle location column (can be 'location', 'id', 'room_id', 'name')
                normalized_room['location'] = (
                    room.get('location') or 
                    room.get('id') or 
                    room.get('room_id') or 
                    room.get('name') or 
                    ''
                )
                # Handle start time column
                normalized_room['start time'] = (
                    room.get('start time') or 
                    room.get('start_time') or 
                    room.get('startTime') or
                    start_str  # Fallback to requested time
                )
                # Handle end time column
                normalized_room['end time'] = (
                    room.get('end time') or 
                    room.get('end_time') or 
                    room.get('endTime') or
                    end_str  # Fallback to requested time
                )
                # Copy other properties
                for key, value in room.items():
                    if key not in ['location', 'id', 'room_id', 'name', 'start time', 'start_time', 'startTime', 
                                  'end time', 'end_time', 'endTime']:
                        normalized_room[key] = value
                
                normalized_rooms.append(normalized_room)
            
            return normalized_rooms
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching rooms from LIV25: {e}")
            return []
    
    def get_all_rooms(self) -> List[Dict]:
        """
        Get all rooms from LIV25 (for initial data load).
        
        Returns:
            List of all rooms with normalized column names:
            - 'location': Room identifier
            - 'start time': Room availability start time
            - 'end time': Room availability end time
        """
        endpoint = f"{self.base_url}/rooms"
        
        try:
            response = self.session.get(endpoint, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            rooms = []
            if isinstance(data, dict) and 'rooms' in data:
                rooms = data['rooms']
            elif isinstance(data, list):
                rooms = data
            else:
                return []
            
            # Normalize column names
            normalized_rooms = []
            for room in rooms:
                normalized_room = {}
                normalized_room['location'] = (
                    room.get('location') or 
                    room.get('id') or 
                    room.get('room_id') or 
                    room.get('name') or 
                    ''
                )
                normalized_room['start time'] = room.get('start time') or room.get('start_time') or room.get('startTime')
                normalized_room['end time'] = room.get('end time') or room.get('end_time') or room.get('endTime')
                # Copy other properties
                for key, value in room.items():
                    if key not in ['location', 'id', 'room_id', 'name', 'start time', 'start_time', 'startTime', 
                                  'end time', 'end_time', 'endTime']:
                        normalized_room[key] = value
                
                normalized_rooms.append(normalized_room)
            
            return normalized_rooms
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching all rooms from LIV25: {e}")
            return []
    
    def get_rooms_from_dataframe(self, df: pd.DataFrame, start_time: datetime, 
                                 end_time: datetime, capacity: int = 1) -> List[Dict]:
        """
        Get available rooms from a DataFrame (e.g., from CSV or Google Sheets).
        DataFrame should have columns: 'location', 'start time', 'end time', and optionally 'capacity'.
        
        Args:
            df: DataFrame with room data
            start_time: Start datetime of the exam
            end_time: End datetime of the exam
            capacity: Minimum room capacity required
        
        Returns:
            List of available rooms that match the time slot and capacity
        """
        if df.empty:
            return []
        
        # Normalize column names (handle case variations)
        col_map = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in ['location', 'id', 'room_id', 'name']:
                col_map['location'] = col
            elif col_lower in ['start time', 'start_time', 'starttime']:
                col_map['start time'] = col
            elif col_lower in ['end time', 'end_time', 'endtime']:
                col_map['end time'] = col
            elif col_lower == 'capacity':
                col_map['capacity'] = col
        
        if 'location' not in col_map:
            print("Warning: 'location' column not found in room data")
            return []
        
        available_rooms = []
        
        for _, row in df.iterrows():
            # Get location
            location = str(row[col_map['location']]).strip()
            if not location or location.lower() == 'nan':
                continue
            
            # Check capacity if column exists
            if 'capacity' in col_map:
                room_capacity = row[col_map['capacity']]
                try:
                    room_capacity = int(float(room_capacity))
                    if room_capacity < capacity:
                        continue
                except:
                    pass
            
            # Check time availability if columns exist
            room_start = None
            room_end = None
            
            if 'start time' in col_map:
                room_start = row[col_map['start time']]
            if 'end time' in col_map:
                room_end = row[col_map['end time']]
            
            # If time columns exist, verify room is available for the requested time
            if room_start is not None and room_end is not None:
                try:
                    room_start_dt = pd.to_datetime(room_start)
                    room_end_dt = pd.to_datetime(room_end)
                    # Room is available if exam time fits within room's availability window
                    if start_time < room_start_dt or end_time > room_end_dt:
                        continue
                except:
                    # If parsing fails, assume room is available
                    pass
            
            # Build room dictionary
            room_dict = {
                'location': location,
                'start time': room_start if room_start is not None else start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'end time': room_end if room_end is not None else end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            }
            
            # Add capacity if available
            if 'capacity' in col_map:
                try:
                    room_dict['capacity'] = int(float(row[col_map['capacity']]))
                except:
                    room_dict['capacity'] = 1
            
            # Copy other columns
            for col in df.columns:
                if col not in col_map.values():
                    room_dict[col] = row[col]
            
            available_rooms.append(room_dict)
        
        return available_rooms
    
    def reserve_room(self, room_id: str, start_time: datetime, end_time: datetime, 
                    exam_details: Dict) -> bool:
        """
        Reserve a room in LIV25.
        
        Args:
            room_id: ID of the room to reserve
            start_time: Start datetime
            end_time: End datetime
            exam_details: Additional exam information
        
        Returns:
            True if reservation successful, False otherwise
        """
        endpoint = f"{self.base_url}/rooms/{room_id}/reserve"
        
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        payload = {
            'start_time': start_str,
            'end_time': end_str,
            'exam_details': exam_details
        }
        
        try:
            response = self.session.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error reserving room {room_id}: {e}")
            return False


def search_rooms_for_exams(room_requirements: List[Dict], 
                          liv25_client: LIV25API) -> List[Dict]:
    """
    Search for available rooms for multiple exam time slots.
    
    Args:
        room_requirements: List of room requirement dictionaries from get_room_requirements()
        liv25_client: LIV25API client instance
    
    Returns:
        List of dictionaries with exam groups and their available rooms
    """
    results = []
    
    for req in room_requirements:
        available_rooms = liv25_client.get_available_rooms(
            start_time=req['start_time'],
            end_time=req['end_time'],
            capacity=req['min_capacity'],
            special_needs=req['has_special_needs']
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

