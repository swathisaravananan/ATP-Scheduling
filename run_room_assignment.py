#!/usr/bin/env python3
"""
Simple script to run room assignment workflow.

Usage:
    python3 run_room_assignment.py [--num-exams N] [--no-ilp]

Options:
    --num-exams N    : Process only first N scheduled exams (default: all)
    --no-ilp         : Use greedy algorithm instead of ILP
"""

import pandas as pd
import sys
from service.pipeline2 import Pipeline2
from utils.mock_liv25_data import generate_mock_rooms_for_exams
from utils.group_exams import group_exam_timings

def main():
    # Parse arguments
    num_exams = None
    use_ilp = True
    
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--num-exams' and i < len(sys.argv) - 1:
            num_exams = int(sys.argv[i + 1])
        elif arg == '--no-ilp':
            use_ilp = False
    
    print('='*70)
    print('ATP EXAM ROOM ASSIGNMENT')
    print('='*70)
    print()
    
    # Load scheduled exams
    print('Step 1: Loading scheduled exams...')
    exam_df = pd.read_csv('result1.csv')
    exam_df = exam_df[exam_df['Schedule Status'] == 'SCHEDULED']
    
    if num_exams:
        exam_df = exam_df.head(num_exams)
        print(f'   Processing first {num_exams} scheduled exams')
    else:
        print(f'   Processing all {len(exam_df)} scheduled exams')
    print()
    
    # Group exams
    print('Step 2: Grouping exam timings...')
    exam_groups = group_exam_timings(exam_df)
    print(f'   Found {len(exam_groups)} unique exam time slots')
    print()
    
    # Generate mock rooms
    print('Step 3: Generating room data...')
    mock_rooms = generate_mock_rooms_for_exams(
        exam_groups=exam_groups,
        num_rooms_per_slot=3,
        capacity_range=(10, 30),
        use_real_room_names=True
    )
    print(f'   Generated {len(mock_rooms)} rooms')
    print()
    
    # Initialize Pipeline2
    print('Step 4: Initializing room assignment...')
    optimizer = 'ILP' if use_ilp else 'Greedy'
    print(f'   Using {optimizer} optimizer')
    p2 = Pipeline2(liv25_rooms_df=mock_rooms, use_ilp=use_ilp)
    print()
    
    # Run room assignment
    print('Step 5: Running room assignment workflow...')
    print('   This will update Google Sheets: EXAM INFORMATION')
    print()
    
    result = p2.process_room_assignment(exam_data_df=exam_df)
    
    # Show results
    print('='*70)
    print('RESULTS')
    print('='*70)
    print()
    
    assigned = result[result['Room Assignment Status'].str.contains('Assigned', na=False)]
    unassigned = result[~result['Room Assignment Status'].str.contains('Assigned', na=False)]
    
    print(f'Total exams processed: {len(result)}')
    print(f'  ✓ Assigned to rooms: {len(assigned)}')
    print(f'  ✗ Not assigned: {len(unassigned)}')
    print()
    
    if len(assigned) > 0:
        room_name_col = 'Assigned Room Name'
        unique_rooms = assigned[room_name_col].nunique()
        print(f'Unique rooms used: {unique_rooms}')
        print(f'Sample assignments:')
        for idx, row in assigned.head(5).iterrows():
            student_id = row['Student ID']
            room_name = row[room_name_col]
            print(f'  • Student {student_id:6s} → {room_name}')
        print()
    
    if len(unassigned) > 0:
        print('='*70)
        print('⚠️  UNASSIGNED STUDENTS REPORT')
        print('='*70)
        print(f'Total unassigned: {len(unassigned)}')
        print()
        print('Students who did NOT get room assignments:')
        for idx, row in unassigned.iterrows():
            student_id = row['Student ID']
            crn = row['CRN']
            status = row['Room Assignment Status']
            schedule_status = row.get('Schedule Status', 'N/A')
            print(f'  • Student {student_id:6s} | CRN {crn:4s} | Schedule: {schedule_status:20s} | Reason: {status}')
        print()
        print('='*70)
    else:
        print('✓ All students successfully assigned to rooms!')
        print()
    
    # Save results
    output_file = 'result_with_rooms.csv'
    result.to_csv(output_file, index=False)
    print(f'Results saved to {output_file}')
    print()
    print('='*70)
    print('✓ COMPLETE!')
    print('='*70)
    print()
    print('Google Sheet updated: FA25 NEW MOCK → EXAM INFORMATION')
    print('Check your sheet for room assignments!')
    
    return result

if __name__ == '__main__':
    main()
