"""
Example: Update EXAM INFORMATION sheet in Google Sheets with room assignments.

This script demonstrates how to:
1. Load exam data with room assignments
2. Update the EXAM INFORMATION sheet in Google Sheets
"""

from service.pipeline2 import Pipeline2
from utils.mock_liv25_data import create_sample_mock_rooms
import pandas as pd

# Option 1: Update from a CSV file with room assignments
def update_from_csv(csv_file: str = "test_ilp_result.csv"):
    """
    Update EXAM INFORMATION sheet from a CSV file that already has room assignments.
    """
    print(f"Loading room assignments from {csv_file}...")
    df = pd.read_csv(csv_file)
    
    # Initialize Pipeline2
    p2 = Pipeline2()
    
    # Update EXAM INFORMATION sheet
    p2.update_exam_information_sheet(
        df=df,
        file_name="FA25 NEW MOCK",
        sheet_name="EXAM INFORMATION"
    )
    print("✓ EXAM INFORMATION sheet updated successfully!")


# Option 2: Run full room assignment and update sheets
def run_full_workflow():
    """
    Run complete room assignment workflow which automatically updates both sheets.
    """
    print("Running full room assignment workflow...")
    
    # Load exam data (from CSV or Google Sheets)
    exam_df = pd.read_csv("result1.csv")
    exam_df = exam_df[exam_df['Schedule Status'] == 'SCHEDULED'].head(50)
    
    # Create mock room data
    from utils.mock_liv25_data import generate_mock_rooms_for_exams
    from utils.group_exams import group_exam_timings
    
    exam_groups = group_exam_timings(exam_df)
    mock_rooms = generate_mock_rooms_for_exams(
        exam_groups=exam_groups,
        num_rooms_per_slot=3,
        capacity_range=(10, 30),
        use_real_room_names=True
    )
    
    # Initialize Pipeline2 with mock rooms
    p2 = Pipeline2(liv25_rooms_df=mock_rooms, use_ilp=True)
    
    # This will automatically update both "Exam Schedule" and "EXAM INFORMATION" sheets
    result = p2.process_room_assignment(exam_data_df=exam_df)
    
    print("✓ Full workflow completed!")
    print(f"✓ Updated {len(result)} rows with room assignments")
    print("✓ Both Google Sheets updated:")
    print("    - Exam Schedule")
    print("    - EXAM INFORMATION")
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "csv":
        # Update from existing CSV file
        csv_file = sys.argv[2] if len(sys.argv) > 2 else "test_ilp_result.csv"
        update_from_csv(csv_file)
    else:
        # Run full workflow
        run_full_workflow()

