"""
Test the ILP formulation with a small dataset to verify it matches the handwritten formulation.
"""

from service.pipeline2 import Pipeline2
from utils.mock_liv25_data import create_sample_mock_rooms
import pandas as pd

# Step 1: Create a small subset of exam data for testing
print("Loading exam data...")
exam_df_full = pd.read_csv("result1.csv")

# Filter to only scheduled exams and take first 50 for testing
exam_df = exam_df_full[exam_df_full['Schedule Status'] == 'SCHEDULED'].head(50).copy()
print(f"Using {len(exam_df)} scheduled exams for testing")

# Step 2: Group exams first, then create rooms tailored to exam time slots
print("\nGrouping exams...")
from utils.group_exams import group_exam_timings
from utils.mock_liv25_data import generate_mock_rooms_for_exams

exam_groups = group_exam_timings(exam_df)
print(f"Grouped into {len(exam_groups)} exam time slots")

print("\nCreating mock room data tailored to exam times...")
# Generate rooms that match the exam time slots
mock_rooms = generate_mock_rooms_for_exams(
    exam_groups=exam_groups,
    num_rooms_per_slot=3,  # 3 rooms per time slot
    capacity_range=(10, 30)  # Rooms with 10-30 capacity
)
print(f"Generated {len(mock_rooms)} mock rooms")

# Step 3: Initialize Pipeline2 with ILP
print("\nInitializing Pipeline2 with ILP optimizer...")
p2 = Pipeline2(
    liv25_rooms_df=mock_rooms,
    use_ilp=True,  # Use ILP optimizer
    ilp_objective='minimize_rooms'
)

# Step 4: Process room assignment
print("\nProcessing room assignment with ILP...")
print("="*60)

# Manually call steps to avoid Google Sheets update
# exam_groups already created above
print(f"Using {len(exam_groups)} exam time slots")

room_search_results = p2.search_rooms_in_liv25(exam_groups)
print(f"Found rooms for {len(room_search_results)} time slots")

result = p2.assign_rooms(exam_df, room_search_results, exam_groups=exam_groups)

# Step 5: View results
print("\n" + "="*60)
print("ILP Formulation Test Results:")
print("="*60)
print(f"Total exams: {len(result)}")
assigned = result[result['Room Assignment Status'].str.contains('Assigned', na=False)]
print(f"Successfully assigned: {len(assigned)}")
print(f"Unassigned: {len(result) - len(assigned)}")

if len(assigned) > 0:
    print("\nSample assignments:")
    print(assigned[['Student ID', 'CRN', 'Scheduled Start', 'Assigned Room Location', 
                    'Room Assignment Status']].head(10))
    
    # Show assignment statistics
    print("\nAssignment Statistics:")
    print(f"Unique rooms used: {assigned['Assigned Room Location'].nunique()}")
    print(f"Rooms used: {sorted(assigned['Assigned Room Location'].unique())}")

# Save results
result.to_csv("test_ilp_result.csv", index=False)
print("\nTest results saved to test_ilp_result.csv")

