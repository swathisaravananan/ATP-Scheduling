"""
Example: Using Gurobi ILP optimizer for room assignment.

This example demonstrates:
1. Loading exam data
2. Grouping exams
3. Loading room data
4. Solving ILP for optimal room assignment
5. Applying results to DataFrame
"""

from service.pipeline2 import Pipeline2
import pandas as pd

# ============================================
# Option 1: Use Pipeline2 with ILP (Recommended)
# ============================================

# Option 1: Generate mock rooms tailored to exam time slots (Recommended)
from utils.mock_liv25_data import generate_mock_rooms_for_exams, create_sample_mock_rooms
from utils.group_exams import group_exam_timings

# Load exam data first to generate appropriate rooms
exam_df = pd.read_csv("result1.csv")
exam_groups = group_exam_timings(exam_df)

# Generate mock rooms that match exam time slots
rooms_df = generate_mock_rooms_for_exams(
    exam_groups=exam_groups,
    num_rooms_per_slot=5,  # 5 rooms per time slot
    capacity_range=(15, 40)  # Rooms with 15-40 capacity
)
print(f"Generated {len(rooms_df)} mock rooms")

# Option 2: Use simple sample mock rooms
# rooms_df = create_sample_mock_rooms()

# Option 3: Load from CSV if you've saved mock rooms before
# from utils.mock_liv25_data import load_mock_rooms_from_csv
# rooms_df = load_mock_rooms_from_csv("mock_rooms.csv")

# Option 4: Manual DataFrame (for testing specific scenarios)
# rooms_df = pd.DataFrame([
#     {
#         'location': 'Room 101',
#         'start time': '2025-12-15 08:00:00',
#         'end time': '2025-12-15 22:00:00',
#         'capacity': 20
#     },
#     {
#         'location': 'Room 102',
#         'start time': '2025-12-15 08:00:00',
#         'end time': '2025-12-15 22:00:00',
#         'capacity': 15
#     },
# ])

# Initialize Pipeline2 with ILP enabled
p2 = Pipeline2(
    liv25_rooms_df=rooms_df,
    use_ilp=True,  # Enable ILP optimizer
    ilp_objective='minimize_rooms'  # or 'minimize_weighted'
)

# Load scheduled exam data (already loaded above for room generation)
# exam_df = pd.read_csv("result1.csv")

# Process room assignment (automatically uses ILP)
print("Processing room assignment with ILP...")
result_with_rooms = p2.process_room_assignment(exam_data_df=exam_df)

print("\nRoom Assignment Summary:")
print(f"Total exams: {len(result_with_rooms)}")
assigned = result_with_rooms[result_with_rooms['Room Assignment Status'] == 'Assigned (ILP)']
print(f"Assigned rooms (ILP): {len(assigned)}")
print(f"Unassigned: {len(result_with_rooms) - len(assigned)}")

# Save results
result_with_rooms.to_csv("result_with_rooms_ilp.csv", index=False)
print("\nResults saved to result_with_rooms_ilp.csv")

# ============================================
# Option 2: Direct ILP Usage (Advanced)
# ============================================

from utils.gurobi_room_optimizer import build_and_solve_ilp, apply_ilp_assignments_to_dataframe
from utils.group_exams import group_exam_timings

# Group exams
print("\nGrouping exams...")
exam_groups = group_exam_timings(exam_df)
print(f"Found {len(exam_groups)} exam groups")

# Solve ILP
print("Solving ILP...")
ilp_result = build_and_solve_ilp(
    exam_groups=exam_groups,
    rooms_df=rooms_df,
    objective='minimize_rooms'
)

print(f"ILP Status: {ilp_result['status']}")
if ilp_result['objective_value'] is not None:
    print(f"Objective Value: {ilp_result['objective_value']}")
print(f"Solve Time: {ilp_result['solve_time']:.2f} seconds")

# Apply results
result_df = apply_ilp_assignments_to_dataframe(
    df=exam_df,
    exam_groups=exam_groups,
    ilp_result=ilp_result,
    rooms_df=rooms_df
)

print(f"\nAssigned {len(result_df[result_df['Room Assignment Status'] == 'Assigned (ILP)'])} exams")

# ============================================
# Option 3: Compare ILP vs Greedy
# ============================================

print("\n" + "="*50)
print("Comparing ILP vs Greedy Algorithm")
print("="*50)

# ILP assignment
p2_ilp = Pipeline2(liv25_rooms_df=rooms_df, use_ilp=True)
result_ilp = p2_ilp.process_room_assignment(exam_data_df=exam_df)

# Greedy assignment
p2_greedy = Pipeline2(liv25_rooms_df=rooms_df, use_ilp=False)
result_greedy = p2_greedy.process_room_assignment(exam_data_df=exam_df)

# Compare
ilp_assigned = len(result_ilp[result_ilp['Room Assignment Status'].str.contains('Assigned', na=False)])
greedy_assigned = len(result_greedy[result_greedy['Room Assignment Status'].str.contains('Assigned', na=False)])

print(f"ILP assigned: {ilp_assigned} exams")
print(f"Greedy assigned: {greedy_assigned} exams")
print(f"Difference: {ilp_assigned - greedy_assigned} exams")

