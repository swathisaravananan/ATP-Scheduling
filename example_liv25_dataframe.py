"""
Example: Using LIV25 room data from DataFrame/CSV with columns:
- location
- start time  
- end time
- capacity (optional)

This example shows how to use mock data when LIV25 API is not available.
"""

from service.pipeline2 import Pipeline2
from utils.mock_liv25_data import generate_mock_rooms_for_exams, create_sample_mock_rooms, load_mock_rooms_from_csv
from utils.group_exams import group_exam_timings
import pandas as pd

# Load exam data first
exam_df = pd.read_csv("result1.csv")
exam_groups = group_exam_timings(exam_df)

# Option 1: Generate mock rooms tailored to exam time slots (Recommended for testing)
print("Generating mock rooms for exam time slots...")
rooms_df = generate_mock_rooms_for_exams(
    exam_groups=exam_groups,
    num_rooms_per_slot=5,  # 5 rooms per time slot
    capacity_range=(15, 40)  # Rooms with 15-40 capacity
)
print(f"Generated {len(rooms_df)} mock rooms")

# Option 2: Use simple sample mock rooms
# rooms_df = create_sample_mock_rooms()

# Option 3: Load from CSV if you've saved mock rooms before
# rooms_df = load_mock_rooms_from_csv("mock_rooms.csv")

# Option 4: Load rooms from your own CSV file
# rooms_df = pd.read_csv("liv25_rooms.csv")  # Update with your file path

# Option 5: Create DataFrame directly (for testing specific scenarios)
# rooms_df = pd.DataFrame([
#     {
#         'location': 'Room 101',
#         'start time': '2025-12-16 08:00:00',
#         'end time': '2025-12-16 22:00:00',
#         'capacity': 20
#     },
#     {
#         'location': 'Room 102',
#         'start time': '2025-12-16 08:00:00',
#         'end time': '2025-12-16 22:00:00',
#         'capacity': 15
#     },
# ])

# Option 6: Load from Google Sheets
# from utils.access_google_sheets import get_sheet_as_df
# rooms_df = get_sheet_as_df("LIV25 Rooms", "Available Rooms")

# Initialize Pipeline2 with DataFrame (no API needed)
p2 = Pipeline2(
    liv25_rooms_df=rooms_df,
    use_ilp=True,  # Use ILP optimizer
    ilp_objective='minimize_rooms'
)

# Process room assignment
print("\nProcessing room assignment...")
result_with_rooms = p2.process_room_assignment(exam_data_df=exam_df)

# Results will have:
# - Assigned Room ID
# - Assigned Room Name  
# - Assigned Room Location (from 'location' column)
# - Room Assignment Status

print("\nRoom Assignment Summary:")
print(f"Total exams: {len(result_with_rooms)}")
assigned = result_with_rooms[result_with_rooms['Room Assignment Status'].str.contains('Assigned', na=False)]
print(f"Assigned rooms: {len(assigned)}")
print(f"Unassigned: {len(result_with_rooms) - len(assigned)}")

# Save results
result_with_rooms.to_csv("result_with_rooms.csv", index=False)
print("\nResults saved to result_with_rooms.csv")

# Save mock rooms for future use
rooms_df.to_csv("mock_rooms.csv", index=False)
print("Mock rooms saved to mock_rooms.csv")
