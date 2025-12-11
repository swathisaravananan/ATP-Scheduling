# Room Assignment Workflow

This document describes the room assignment functionality that groups exam timings and searches for available rooms in LIV25.

## Overview

The room assignment workflow consists of:
1. **Grouping Exam Timings**: Groups exams that have the same scheduled start and end times
2. **Searching LIV25**: Searches for available rooms in LIV25 for each exam time slot
3. **Room Assignment**: Assigns rooms to individual exams based on availability and capacity

## Files Created

### 1. `utils/group_exams.py`
Contains functions to:
- `group_exam_timings(df)`: Groups exams by their scheduled start/end times
- `get_room_requirements(groups)`: Calculates room requirements for each group

### 2. `utils/liv25_api.py`
Contains the `LIV25API` class for:
- `get_available_rooms()`: Search for available rooms in a time slot
- `get_all_rooms()`: Get all rooms from LIV25
- `reserve_room()`: Reserve a room for an exam

### 3. `service/pipeline2.py`
Implements the complete room assignment workflow:
- `process_room_assignment()`: Main method that orchestrates the entire workflow
- `group_exam_timings()`: Groups exams
- `search_rooms_in_liv25()`: Searches for rooms
- `assign_rooms()`: Assigns rooms to exams
- `update_master_sheet_with_rooms()`: Updates Google Sheets with assignments

## Usage

### Basic Usage

```python
from service.runner import Runner

# Initialize with LIV25 credentials
runner = Runner(
    liv25_base_url="https://liv25.example.com/api",
    liv25_api_key="your-api-key"
)

# Run complete pipeline (scheduling + room assignment)
result = runner.pipeline(include_room_assignment=True)
```

### Using Pipeline2 Directly

```python
from service.pipeline2 import Pipeline2
import pandas as pd

# Initialize Pipeline2
p2 = Pipeline2(
    liv25_base_url="https://liv25.example.com/api",
    liv25_api_key="your-api-key"
)

# Load scheduled exam data
df = pd.read_csv("result1.csv")

# Process room assignment
result_with_rooms = p2.process_room_assignment(exam_data_df=df)
result_with_rooms.to_csv("result_with_rooms.csv", index=False)
```

### Step-by-Step Usage

```python
from service.pipeline2 import Pipeline2
from utils.group_exams import group_exam_timings, get_room_requirements
import pandas as pd

# 1. Load exam data
df = pd.read_csv("result1.csv")

# 2. Group exam timings
exam_groups = group_exam_timings(df)

# 3. Get room requirements
room_requirements = get_room_requirements(exam_groups)

# 4. Search rooms in LIV25
p2 = Pipeline2(liv25_base_url="...", liv25_api_key="...")
room_search_results = p2.search_rooms_in_liv25(exam_groups)

# 5. Assign rooms
df_with_rooms = p2.assign_rooms(df, room_search_results)
```

## Configuration

### LIV25 API Configuration

You need to configure the LIV25 API endpoint and authentication:

1. **Base URL**: Update `LIV25API.__init__()` default base_url or pass it when initializing
2. **API Key**: Pass the API key when creating the `LIV25API` or `Pipeline2` instance

### Example Configuration

```python
# In handler.py or your main script
LIV25_BASE_URL = os.getenv("LIV25_BASE_URL", "https://liv25.example.com/api")
LIV25_API_KEY = os.getenv("LIV25_API_KEY", "your-default-key")

runner = Runner(liv25_base_url=LIV25_BASE_URL, liv25_api_key=LIV25_API_KEY)
```

## LIV25 Data Source Options

You can use LIV25 room data from two sources:

### Option 1: DataFrame/CSV (Recommended for testing)
If you have room data in a CSV or DataFrame with columns:
- `location`: Room identifier (required)
- `start time`: Room availability start time (optional)
- `end time`: Room availability end time (optional)
- `capacity`: Room capacity (optional)

```python
import pandas as pd
from service.pipeline2 import Pipeline2

# Load rooms from CSV
rooms_df = pd.read_csv("liv25_rooms.csv")
p2 = Pipeline2(liv25_rooms_df=rooms_df)
```

### Option 2: LIV25 API

The `LIV25API` class expects the LIV25 API to have the following endpoints:

### GET `/rooms/search`
Search for available rooms.

**Query Parameters:**
- `start_time`: ISO format datetime (e.g., "2025-12-16T18:00:00")
- `end_time`: ISO format datetime
- `capacity`: Minimum room capacity
- `special_needs`: Boolean for special accommodations

**Expected Response:**
```json
{
  "rooms": [
    {
      "location": "Room 101",
      "start time": "2025-12-16T08:00:00",
      "end time": "2025-12-16T22:00:00",
      "capacity": 20,
      ...
    }
  ]
}
```

**Note**: The code handles column name variations:
- `location` can also be `id`, `room_id`, or `name`
- `start time` can also be `start_time` or `startTime`
- `end time` can also be `end_time` or `endTime`

### GET `/rooms`
Get all available rooms.

### POST `/rooms/{room_id}/reserve`
Reserve a room.

**Request Body:**
```json
{
  "start_time": "2025-12-16T18:00:00",
  "end_time": "2025-12-16T22:30:00",
  "exam_details": {...}
}
```

**Note**: You may need to adjust the API endpoints and request/response formats based on your actual LIV25 API documentation.

## Output

The room assignment process adds the following columns to the exam DataFrame:

- `Assigned Room ID`: ID of the assigned room (from `location` column)
- `Assigned Room Name`: Name of the assigned room
- `Assigned Room Location`: Location value from the `location` column
- `Room Assignment Status`: Status of room assignment
  - "Assigned": Room successfully assigned
  - "No room needed - exam not scheduled": Exam was not scheduled
  - "Invalid time slot": Missing or invalid scheduled time
  - "No rooms available": No rooms found in LIV25
  - "No available rooms with capacity": Rooms found but all at capacity

## Dependencies

Make sure to install the required package:

```bash
pip install requests
```

## Notes

- The room assignment logic assumes 1 student per room for individual exams. You can modify the capacity logic in `assign_rooms()` if needed.
- Room assignments are tracked to prevent double-booking of the same room for the same time slot.
- The workflow only processes exams with status "SCHEDULED".

