"""
Example script showing how to use the room assignment workflow with mock LIV25 data.

This script demonstrates:
1. Generating mock room data
2. Grouping exam timings
3. Assigning rooms to exams using ILP optimizer
"""

from service.pipeline2 import Pipeline2
from utils.mock_liv25_data import generate_mock_rooms_for_exams, create_sample_mock_rooms
from utils.group_exams import group_exam_timings
import pandas as pd

# Load scheduled exam data
print("Loading exam data...")
exam_df = pd.read_csv("result1.csv")

# Option 1: Generate mock rooms tailored to exam time slots (Recommended)
print("Generating mock rooms for exam time slots...")
exam_groups = group_exam_timings(exam_df)
mock_rooms_df = generate_mock_rooms_for_exams(
    exam_groups=exam_groups,
    num_rooms_per_slot=5,  # 5 rooms per time slot
    capacity_range=(15, 40)  # Rooms with 15-40 capacity
)
print(f"Generated {len(mock_rooms_df)} mock rooms")

# Option 2: Use simple sample mock rooms
# mock_rooms_df = create_sample_mock_rooms()

# Option 3: Load from CSV if you've saved mock rooms before
# from utils.mock_liv25_data import load_mock_rooms_from_csv
# mock_rooms_df = load_mock_rooms_from_csv("mock_rooms.csv")

# Initialize Pipeline2 with mock room data and ILP enabled
p2 = Pipeline2(
    liv25_rooms_df=mock_rooms_df,
    use_ilp=True,  # Use Gurobi ILP optimizer
    ilp_objective='minimize_rooms'  # Minimize number of rooms used
)

# Process room assignment
print("\nProcessing room assignment...")
result_with_rooms = p2.process_room_assignment(exam_data_df=exam_df)

print("\n" + "="*50)
print("Room Assignment Summary:")
print("="*50)
print(f"Total exams: {len(result_with_rooms)}")
assigned = result_with_rooms[result_with_rooms['Room Assignment Status'].str.contains('Assigned', na=False)]
print(f"Assigned rooms: {len(assigned)}")
unassigned = result_with_rooms[~result_with_rooms['Room Assignment Status'].str.contains('Assigned', na=False)]
print(f"Unassigned: {len(unassigned)}")

if len(unassigned) > 0:
    print("\nUnassigned reasons:")
    print(unassigned['Room Assignment Status'].value_counts())

# Save results
result_with_rooms.to_csv("result_with_rooms.csv", index=False)
print(f"\nResults saved to result_with_rooms.csv")

# Save mock rooms for future use
mock_rooms_df.to_csv("mock_rooms.csv", index=False)
print(f"Mock rooms saved to mock_rooms.csv")


