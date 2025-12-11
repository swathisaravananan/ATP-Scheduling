# Gurobi ILP Integration for Room Assignment

This document describes the Gurobi-based Integer Linear Programming (ILP) optimizer integrated into the room assignment workflow.

## Overview

The ILP optimizer replaces the greedy room assignment algorithm with an optimal solution that:
- **Respects room capacities**: Ensures total student count per exam group doesn't exceed assigned room capacities
- **Respects room availability windows**: Only assigns rooms that are available during the exam time
- **Prevents overlapping exams**: Ensures no two overlapping exam groups share the same room
- **Minimizes room usage**: Optimizes to use the minimum number of rooms (or weighted objective)

## Architecture

### Files

1. **`utils/gurobi_room_optimizer.py`**
   - `build_and_solve_ilp()`: Main ILP solver function
   - `apply_ilp_assignments_to_dataframe()`: Applies ILP results to exam DataFrame
   - Helper functions for overlap detection and column normalization

2. **`service/pipeline2.py`**
   - Modified `assign_rooms()` to use ILP when `use_ilp=True`
   - `_assign_rooms_ilp()`: ILP-based assignment
   - `_assign_rooms_greedy()`: Fallback greedy algorithm

## ILP Formulation

### Decision Variables

- `x[i, r]`: Binary variable = 1 if exam group `i` is assigned to room `r`, 0 otherwise

### Constraints

1. **Capacity Constraint**: For each exam group `i`:
   ```
   Σ(room_capacity[r] * x[i, r]) >= student_count[i]
   ```
   Ensures total capacity of assigned rooms covers all students.

2. **Availability Constraint**: For each exam group `i` and room `r`:
   - If exam starts before room is available: `x[i, r] = 0`
   - If exam ends after room availability ends: `x[i, r] = 0`

3. **No Overlap Constraint**: For overlapping exam groups `i` and `j`:
   ```
   x[i, r] + x[j, r] <= 1  for all rooms r
   ```
   Prevents overlapping exams from sharing the same room.

### Objective Functions

1. **`minimize_rooms`** (default): Minimize number of distinct rooms used
   - Uses indicator variables `room_used[r]` for each room
   - Objective: `minimize Σ(room_used[r])`

2. **`minimize_weighted`**: Minimize weighted room usage
   - Prefers smaller rooms when possible
   - Objective: `minimize Σ((1/capacity[r]) * x[i, r])`

## Usage

### Basic Usage

```python
from service.pipeline2 import Pipeline2
import pandas as pd

# Initialize with ILP enabled (default)
p2 = Pipeline2(
    liv25_rooms_df=rooms_df,  # DataFrame with room data
    use_ilp=True,              # Enable ILP optimizer
    ilp_objective='minimize_rooms'  # or 'minimize_weighted'
)

# Process room assignment
exam_df = pd.read_csv("result1.csv")
result = p2.process_room_assignment(exam_data_df=exam_df)
```

### Disable ILP (Use Greedy Algorithm)

```python
p2 = Pipeline2(
    liv25_rooms_df=rooms_df,
    use_ilp=False  # Use greedy algorithm instead
)
```

### Direct ILP Usage

```python
from utils.gurobi_room_optimizer import build_and_solve_ilp, apply_ilp_assignments_to_dataframe
from utils.group_exams import group_exam_timings

# Group exams
exam_groups = group_exam_timings(exam_df)

# Solve ILP
ilp_result = build_and_solve_ilp(
    exam_groups=exam_groups,
    rooms_df=rooms_df,
    objective='minimize_rooms'
)

# Apply results
result_df = apply_ilp_assignments_to_dataframe(
    df=exam_df,
    exam_groups=exam_groups,
    ilp_result=ilp_result,
    rooms_df=rooms_df
)
```

## Input Requirements

### Exam Groups

List of dictionaries from `group_exam_timings()`, each containing:
- `start_time`: datetime - Exam start time
- `end_time`: datetime - Exam end time
- `student_count`: int - Number of students
- `student_ids`: list - Student IDs
- `crns`: list - Course CRNs
- `duration`: float - Exam duration in minutes
- `exam_records`: list - Original exam records

### Rooms DataFrame

DataFrame with columns:
- `location` (required): Room identifier
- `start time` (optional): Room availability start time
- `end time` (optional): Room availability end time
- `capacity` (optional, default=1): Room capacity

Column name variations are handled automatically:
- `location` / `id` / `room_id` / `name`
- `start time` / `start_time` / `startTime`
- `end time` / `end_time` / `endTime`

## Output

### ILP Result Dictionary

```python
{
    'assignment_map': {
        0: ['Room 101', 'Room 102'],  # Exam group 0 assigned to these rooms
        1: ['Room 103'],              # Exam group 1 assigned to this room
        ...
    },
    'status': 'OPTIMAL',  # or 'INFEASIBLE', 'TIME_LIMIT', etc.
    'objective_value': 5.0,  # Optimal objective value
    'solve_time': 0.23,  # Seconds
    'model': <Gurobi model object>
}
```

### DataFrame Output

The exam DataFrame is updated with:
- `Assigned Room ID`: Room identifier
- `Assigned Room Name`: Room name
- `Assigned Room Location`: Room location
- `Room Assignment Status`: Status (e.g., "Assigned (ILP)")

## Performance Considerations

- **Problem Size**: ILP solve time increases with:
  - Number of exam groups
  - Number of available rooms
  - Number of overlapping exam pairs

- **Typical Performance**:
  - Small problems (< 50 groups, < 100 rooms): < 1 second
  - Medium problems (50-200 groups, 100-500 rooms): 1-10 seconds
  - Large problems (> 200 groups, > 500 rooms): May require time limits

- **Time Limits**: Set via Gurobi parameters:
  ```python
  model.setParam('TimeLimit', 60)  # 60 second limit
  ```

## Troubleshooting

### Infeasible Solutions

If ILP returns `INFEASIBLE`:
1. Check room capacities are sufficient for student counts
2. Verify room availability windows cover exam times
3. Ensure enough rooms are available for overlapping exams

### Slow Performance

1. Reduce problem size by filtering rooms/exams
2. Set time limits: `model.setParam('TimeLimit', 30)`
3. Use greedy algorithm as fallback: `use_ilp=False`

### Installation Issues

Gurobi requires a license. Install via:
```bash
pip install gurobipy
```

For academic use, obtain a free academic license from Gurobi.

## Integration with Existing Workflow

The ILP optimizer is seamlessly integrated:

1. **Exam Scheduling** (Pipeline1 + resolve_slots): Creates scheduled exams
2. **Grouping** (group_exam_timings): Groups exams by time slots
3. **Room Search** (search_rooms_in_liv25): Finds available rooms
4. **ILP Assignment** (assign_rooms with use_ilp=True): Optimally assigns rooms
5. **Update Sheets** (update_master_sheet_with_rooms): Updates Google Sheets

## Example

See `example_ilp_room_assignment.py` for a complete working example.

