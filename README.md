# ATP Exam Scheduling and Room Assignment System

An intelligent exam scheduling and room assignment system that uses Integer Linear Programming (ILP) to optimally assign exams to rooms while respecting constraints such as room capacity, availability windows, and preventing overlapping exams.

## 📋 Overview

This project automates the complex process of:
1. **Exam Scheduling**: Schedules exams for students based on faculty preferences, student timetables, and special needs (NOAM/NOPM)
2. **Room Assignment**: Optimally assigns scheduled exams to available rooms using Gurobi ILP optimizer

The system integrates with Google Sheets for data input/output and supports both API-based and mock data for room availability.

## ✨ Features

### Exam Scheduling
- **Conflict Resolution**: Automatically resolves scheduling conflicts based on faculty-approved alternatives
- **Special Needs Support**: Handles NOAM (No Morning) and NOPM (No Afternoon) constraints
- **Priority-Based Scheduling**: Uses faculty preferences for alternative exam times
- **Timetable Integration**: Checks against student class schedules to avoid conflicts

### Room Assignment
- **Gurobi ILP Optimizer**: Uses integer linear programming for optimal room assignments
- **Constraint Satisfaction**:
  - Room capacity limits
  - Room availability windows
  - Prevents overlapping exams in the same room
- **Multiple Algorithms**: Supports both ILP (optimal) and greedy (fast) assignment
- **Mock Data Support**: Can work without LIV25 API using generated mock room data

## 🏗️ Architecture

### Pipeline Structure

```
Pipeline1 (Data Collection)
    ↓
Exam Scheduling (resolve_slots.py)
    ↓
Pipeline2 (Room Assignment)
    ├── Group Exams by Time Slots
    ├── Search Available Rooms (LIV25 API or Mock Data)
    └── Assign Rooms (ILP or Greedy)
```

### Key Components

- **`service/pipeline1.py`**: Collects faculty and student data from Google Sheets
- **`service/pipeline2.py`**: Handles room assignment workflow
- **`service/runner.py`**: Orchestrates the complete pipeline
- **`utils/resolve_slots.py`**: Exam scheduling logic with conflict resolution
- **`utils/gurobi_room_optimizer.py`**: ILP-based room assignment optimizer
- **`utils/group_exams.py`**: Groups exams by time slots for batch processing
- **`utils/liv25_api.py`**: LIV25 room API integration
- **`utils/mock_liv25_data.py`**: Mock room data generator for testing

## 🚀 Installation

### Prerequisites

- Python 3.7+ (recommended: 3.8+)
- Gurobi license (for ILP optimizer) - [Free for academic use](https://www.gurobi.com/academia/academic-program-and-licenses/)

### Step 1: Clone the Repository

```bash
git clone https://github.com/swathisaravananan/ATP-Scheduling.git
cd ATP-Scheduling
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Key Dependencies:**
- `pandas` - Data manipulation
- `gspread` - Google Sheets API
- `oauth2client` - Google authentication
- `gurobipy` - ILP optimizer (requires license)
- `python-dateutil` - Date/time parsing
- `requests` - HTTP requests

### Step 3: Configure Google Sheets Access

1. Create a Google Cloud service account
2. Download the JSON credentials file
3. Place it in `keys/` directory (e.g., `keys/atp-poc1-4e72f50119bc.json`)
4. Share your Google Sheets with the service account email

### Step 4: Set Up Gurobi (Optional - for ILP optimizer)

```bash
pip install gurobipy
# Get academic license from: https://www.gurobi.com/academia/
grbgetkey <your-license-key>
```

**Note**: The system works without Gurobi using the greedy algorithm, but ILP provides optimal solutions.

## 📖 Usage

### Quick Start (Using Mock Data)

The simplest way to test the system:

```bash
python3 example_simple_mock.py
```

This will:
1. Generate mock room data
2. Load exam data from `result1.csv`
3. Assign rooms using the greedy algorithm
4. Save results to `result_with_mock_rooms.csv`

### Complete Workflow

#### Option 1: Run Complete Pipeline

```python
from service.runner import Runner

# Initialize runner
runner = Runner()

# Run complete pipeline (scheduling + room assignment)
result = runner.pipeline(include_room_assignment=True)
```

#### Option 2: Step-by-Step Execution

```python
from service.pipeline1 import Pipeline1
from service.pipeline2 import Pipeline2
from utils.resolve_slots import schedule_all
from utils.mock_liv25_data import generate_mock_rooms_for_exams
from utils.group_exams import group_exam_timings
import pandas as pd

# Step 1: Get data and schedule exams
p1 = Pipeline1()
faculty_data = p1.get_interested_faculty_info()
student_data = p1.get_student_info()
student_course = p1.get_student_exams()
timetables = p1.get_timetables()

# Merge data
merged_data = faculty_data.merge(student_data, on="CRN")
merged_data = merged_data.merge(student_course, on="Student ID")

# Schedule exams
scheduled_exams = schedule_all(merged_data, timetables)
scheduled_exams.to_csv("result1.csv", index=False)

# Step 2: Assign rooms
exam_groups = group_exam_timings(scheduled_exams)
mock_rooms = generate_mock_rooms_for_exams(exam_groups)

p2 = Pipeline2(liv25_rooms_df=mock_rooms, use_ilp=True)
result = p2.process_room_assignment(exam_data_df=scheduled_exams)
result.to_csv("result_with_rooms.csv", index=False)
```

### Using ILP Optimizer

```python
from service.pipeline2 import Pipeline2
from utils.mock_liv25_data import generate_mock_rooms_for_exams
from utils.group_exams import group_exam_timings
import pandas as pd

# Load exam data
exam_df = pd.read_csv("result1.csv")
exam_groups = group_exam_timings(exam_df)

# Generate rooms
rooms_df = generate_mock_rooms_for_exams(
    exam_groups=exam_groups,
    num_rooms_per_slot=5,
    capacity_range=(15, 40)
)

# Initialize with ILP
p2 = Pipeline2(
    liv25_rooms_df=rooms_df,
    use_ilp=True,  # Enable ILP optimizer
    ilp_objective='minimize_rooms'  # or 'minimize_weighted'
)

# Process
result = p2.process_room_assignment(exam_data_df=exam_df)
```

### Using LIV25 API (When Available)

```python
from service.pipeline2 import Pipeline2

p2 = Pipeline2(
    liv25_base_url="https://liv25.example.com/api",
    liv25_api_key="your-api-key",
    use_ilp=True
)

result = p2.process_room_assignment(exam_data_file="result1.csv")
```

## 📁 Project Structure

```
ATP-Scheduling/
├── service/
│   ├── pipeline1.py          # Data collection and exam scheduling
│   ├── pipeline2.py          # Room assignment workflow
│   └── runner.py             # Main pipeline orchestrator
├── utils/
│   ├── resolve_slots.py      # Exam scheduling with conflict resolution
│   ├── resolve_time.py       # Alternative scheduling algorithm
│   ├── group_exams.py        # Group exams by time slots
│   ├── gurobi_room_optimizer.py  # ILP room assignment optimizer
│   ├── liv25_api.py          # LIV25 API integration
│   ├── mock_liv25_data.py    # Mock room data generator
│   └── access_google_sheets.py  # Google Sheets integration
├── keys/                     # Google service account credentials (not in repo)
├── timetables/              # Student timetable JSON files
├── handler.py               # Entry point
├── requirements.txt         # Python dependencies
├── example_simple_mock.py   # Simple example with mock data
├── example_ilp_room_assignment.py  # ILP example
└── README.md               # This file
```

## 🔧 Configuration

### Google Sheets Setup

1. Create Google Sheets with the following structure:
   - **Faculty Data**: CRN, exam dates, preferences, etc.
   - **Student Data**: Student IDs, tags (NOAM/NOPM), etc.
   - **Student-Course Links**: Mapping students to courses

2. Update sheet names in `service/pipeline1.py`:
   ```python
   get_sheet_as_df("Your Sheet Name", "Sheet Tab Name")
   ```

### LIV25 API Configuration

If using LIV25 API, update in `utils/liv25_api.py` or pass when initializing:
```python
Pipeline2(liv25_base_url="your-url", liv25_api_key="your-key")
```

## 📊 Input/Output Format

### Input: Exam Data (CSV/Google Sheets)

Required columns:
- `CRN` - Course Reference Number
- `Student ID` - Student identifier
- `Instructor Exam Date` - Preferred exam date
- `Instructor Exam Time` - Preferred exam time
- `Duration` - Exam duration in minutes
- `NOAM` / `NOPM` - Special needs flags
- Conflict resolution preference columns

### Output: Scheduled Exams with Room Assignments

Added columns:
- `Scheduled Start` - Assigned exam start time
- `Scheduled End` - Assigned exam end time
- `Schedule Status` - Scheduling status
- `Assigned Room Location` - Assigned room
- `Room Assignment Status` - Room assignment status

## 🧪 Testing

### Test ILP Formulation

```bash
python3 test_ilp_formulation.py
```

This tests the ILP optimizer with a small dataset to verify it matches the handwritten formulation.

### Test with Mock Data

```bash
python3 example_simple_mock.py
```

## 📚 Documentation

- **[GUROBI_ILP_INTEGRATION.md](GUROBI_ILP_INTEGRATION.md)** - Detailed ILP optimizer documentation
- **[ROOM_ASSIGNMENT_README.md](ROOM_ASSIGNMENT_README.md)** - Room assignment workflow guide
- **[MOCK_DATA_GUIDE.md](MOCK_DATA_GUIDE.md)** - Using mock data for testing
- **[LIBRARIES.md](LIBRARIES.md)** - Complete library dependencies guide

## 🔬 ILP Formulation

The room assignment uses an Integer Linear Programming model:

**Decision Variables:**
- `x_ij` = 1 if exam group i is assigned to room j, 0 otherwise
- `y_j` = 1 if room j is used, 0 otherwise

**Objective:**
- Minimize Σ y_j (minimize number of rooms used)

**Constraints:**
1. Each exam group assigned to exactly one room: Σ x_ij = 1
2. Room capacity: Σ n_i * x_ij ≤ C_j
3. Room availability windows
4. No overlapping exams in same room
5. Linking: x_ij ≤ y_j

See `GUROBI_ILP_INTEGRATION.md` for complete formulation details.

## ⚠️ Important Notes

1. **Sensitive Files**: The `keys/` directory containing service account credentials is excluded from the repository. Add your own credentials locally.

2. **Gurobi License**: For large problems, an unrestricted Gurobi license may be required. Academic licenses are free.

3. **Google Sheets**: Ensure your service account has access to the Google Sheets you're using.

4. **Data Privacy**: Be careful with student data. Ensure compliance with privacy regulations.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is for academic/research purposes. Please ensure compliance with your institution's policies.

## 🙏 Acknowledgments

- Gurobi Optimization for the ILP solver
- Google Sheets API for data integration
- All contributors and testers

---

For questions or issues, please open an issue on GitHub.

