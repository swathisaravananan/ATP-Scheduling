"""
Simple example using mock LIV25 room data.

This is the simplest way to test room assignment without LIV25 API.
"""

from service.pipeline2 import Pipeline2
from utils.mock_liv25_data import create_sample_mock_rooms
import pandas as pd

# Step 1: Create mock room data
print("Creating mock room data...")
mock_rooms = create_sample_mock_rooms()
print(f"Created {len(mock_rooms)} mock rooms")
print("\nSample rooms:")
print(mock_rooms.head())

# Step 2: Load exam data
print("\nLoading exam data...")
exam_df = pd.read_csv("result1.csv")
print(f"Loaded {len(exam_df)} exam records")

# Step 3: Initialize Pipeline2 with mock rooms
# Try ILP first, fall back to greedy if license issue
try:
    import gurobipy
    use_ilp = True
    print("Using ILP optimizer (following handwritten formulation)")
except ImportError:
    use_ilp = False
    print("Gurobi not found - using greedy algorithm")

p2 = Pipeline2(
    liv25_rooms_df=mock_rooms,
    use_ilp=use_ilp  # Using greedy algorithm
)

# Step 4: Process room assignment (skip Google Sheets update)
print("\nProcessing room assignment...")
# We'll manually call the steps to avoid Google Sheets update
exam_groups = p2.group_exam_timings(exam_df)
room_search_results = p2.search_rooms_in_liv25(exam_groups)
result = p2.assign_rooms(exam_df, room_search_results, exam_groups=exam_groups)

# Step 5: View results
print("\n" + "="*50)
print("Results:")
print("="*50)
print(f"Total exams: {len(result)}")
assigned = result[result['Room Assignment Status'].str.contains('Assigned', na=False)]
print(f"Successfully assigned: {len(assigned)}")
print(f"Unassigned: {len(result) - len(assigned)}")

# Show some assigned exams
if len(assigned) > 0:
    print("\nSample assignments:")
    print(assigned[['Student ID', 'CRN', 'Scheduled Start', 'Assigned Room Location', 
                    'Room Assignment Status']].head(10))

# Save results
result.to_csv("result_with_mock_rooms.csv", index=False)
print("\nResults saved to result_with_mock_rooms.csv")

# Save mock rooms for future use
mock_rooms.to_csv("mock_rooms.csv", index=False)
print("Mock rooms saved to mock_rooms.csv")

