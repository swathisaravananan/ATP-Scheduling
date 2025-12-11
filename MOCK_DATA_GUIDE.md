# Mock LIV25 Data Guide

Since LIV25 API is not yet integrated, this guide shows how to use mock room data for testing the room assignment workflow.

## Quick Start

The simplest way to get started:

```python
from service.pipeline2 import Pipeline2
from utils.mock_liv25_data import create_sample_mock_rooms
import pandas as pd

# Create mock rooms
mock_rooms = create_sample_mock_rooms()

# Load exam data
exam_df = pd.read_csv("result1.csv")

# Initialize and run
p2 = Pipeline2(liv25_rooms_df=mock_rooms, use_ilp=True)
result = p2.process_room_assignment(exam_data_df=exam_df)
```

## Mock Data Functions

### 1. `create_sample_mock_rooms()`

Creates a simple set of 20 mock rooms for quick testing.

```python
from utils.mock_liv25_data import create_sample_mock_rooms

rooms_df = create_sample_mock_rooms()
```

**Output**: DataFrame with 20 rooms, capacities 10-30, available 8 AM - 10 PM.

---

### 2. `generate_mock_rooms(num_rooms, ...)`

Generates a customizable set of mock rooms.

```python
from utils.mock_liv25_data import generate_mock_rooms
from datetime import datetime

rooms_df = generate_mock_rooms(
    num_rooms=50,
    start_date=datetime(2025, 12, 1),
    end_date=datetime(2025, 12, 31),
    base_capacity=20,
    capacity_range=(10, 50)
)
```

**Parameters**:
- `num_rooms`: Number of rooms to generate (default: 50)
- `start_date`: Start date for availability (default: today)
- `end_date`: End date for availability (default: 30 days from start)
- `base_capacity`: Base room capacity (default: 20)
- `capacity_range`: (min, max) capacity range (default: (10, 50))

---

### 3. `generate_mock_rooms_for_exams(exam_groups, ...)` ⭐ **Recommended**

Generates mock rooms specifically tailored to your exam time slots. This ensures rooms are available during exam times.

```python
from utils.mock_liv25_data import generate_mock_rooms_for_exams
from utils.group_exams import group_exam_timings

# First, group your exams
exam_groups = group_exam_timings(exam_df)

# Generate rooms for those time slots
rooms_df = generate_mock_rooms_for_exams(
    exam_groups=exam_groups,
    num_rooms_per_slot=5,  # 5 rooms per unique time slot
    capacity_range=(15, 40)  # Rooms with 15-40 capacity
)
```

**Parameters**:
- `exam_groups`: List of exam group dicts from `group_exam_timings()`
- `num_rooms_per_slot`: Number of rooms per time slot (default: 5)
- `capacity_range`: (min, max) capacity range (default: (15, 40))

**Why this is recommended**: 
- Rooms are guaranteed to be available during exam times
- Number of rooms scales with your exam schedule
- More realistic for testing

---

### 4. `load_mock_rooms_from_csv(file_path)`

Loads mock rooms from a CSV file, or generates new ones if file doesn't exist.

```python
from utils.mock_liv25_data import load_mock_rooms_from_csv

rooms_df = load_mock_rooms_from_csv("mock_rooms.csv")
```

If the file doesn't exist, it will generate new mock rooms and save them.

---

## Example Workflows

### Example 1: Simple Testing

```python
from service.pipeline2 import Pipeline2
from utils.mock_liv25_data import create_sample_mock_rooms
import pandas as pd

# Quick test with sample rooms
mock_rooms = create_sample_mock_rooms()
exam_df = pd.read_csv("result1.csv")

p2 = Pipeline2(liv25_rooms_df=mock_rooms, use_ilp=True)
result = p2.process_room_assignment(exam_data_df=exam_df)
result.to_csv("result_with_mock_rooms.csv", index=False)
```

### Example 2: Realistic Testing (Recommended)

```python
from service.pipeline2 import Pipeline2
from utils.mock_liv25_data import generate_mock_rooms_for_exams
from utils.group_exams import group_exam_timings
import pandas as pd

# Load and group exams
exam_df = pd.read_csv("result1.csv")
exam_groups = group_exam_timings(exam_df)

# Generate rooms tailored to exam schedule
mock_rooms = generate_mock_rooms_for_exams(
    exam_groups=exam_groups,
    num_rooms_per_slot=5,
    capacity_range=(15, 40)
)

# Run assignment
p2 = Pipeline2(liv25_rooms_df=mock_rooms, use_ilp=True)
result = p2.process_room_assignment(exam_data_df=exam_df)
result.to_csv("result_with_mock_rooms.csv", index=False)

# Save mock rooms for reuse
mock_rooms.to_csv("mock_rooms.csv", index=False)
```

### Example 3: Custom Mock Data

```python
import pandas as pd
from datetime import datetime

# Create custom room data
rooms_df = pd.DataFrame([
    {
        'location': 'LIB-2101A',
        'start time': datetime(2025, 12, 15, 8, 0),
        'end time': datetime(2025, 12, 15, 22, 0),
        'capacity': 25
    },
    {
        'location': 'SCI-3105B',
        'start time': datetime(2025, 12, 15, 8, 0),
        'end time': datetime(2025, 12, 15, 22, 0),
        'capacity': 30
    },
    # Add more rooms...
])

# Use with Pipeline2
p2 = Pipeline2(liv25_rooms_df=rooms_df, use_ilp=True)
result = p2.process_room_assignment(exam_data_df=exam_df)
```

---

## Mock Room Data Format

The mock data generator creates DataFrames with these columns:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `location` | string | Room identifier | `"LIB-2101A"` |
| `start time` | datetime | Room availability start | `2025-12-15 08:00:00` |
| `end time` | datetime | Room availability end | `2025-12-15 22:00:00` |
| `capacity` | int | Room capacity | `25` |

---

## Room Naming Convention

Mock rooms use this naming pattern:
- Format: `{BUILDING}-{FLOOR}{ROOM_NUM}{TYPE}`
- Examples: `LIB-2101A`, `SCI-3105B`, `ENG-4102C`
- Buildings: LIB, SCI, ENG, BUS, ART, HALL
- Floors: 1-5
- Room numbers: 100-599
- Types: A, B, C, D, E

---

## Tips

1. **For realistic testing**: Use `generate_mock_rooms_for_exams()` - it ensures rooms match your exam schedule
2. **For quick testing**: Use `create_sample_mock_rooms()` - fast and simple
3. **Save mock data**: Save generated rooms to CSV for reuse: `rooms_df.to_csv("mock_rooms.csv")`
4. **Adjust capacity**: Modify `capacity_range` to match your needs
5. **Scale rooms**: Increase `num_rooms_per_slot` if you have many students per time slot

---

## Files

- **`utils/mock_liv25_data.py`**: Mock data generation functions
- **`example_simple_mock.py`**: Simplest example
- **`example_room_assignment.py`**: Full workflow example with mock data
- **`example_ilp_room_assignment.py`**: ILP-specific example with mock data

---

## Next Steps

Once LIV25 API is integrated, you can replace mock data with real API calls:

```python
# Instead of:
rooms_df = create_sample_mock_rooms()

# Use:
from utils.liv25_api import LIV25API
liv25 = LIV25API(base_url="...", api_key="...")
rooms_df = liv25.get_all_rooms()  # Or use API search
```

The rest of your code remains the same!

