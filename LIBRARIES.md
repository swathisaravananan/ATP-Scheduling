# Project Libraries and Dependencies

This document lists all the libraries used in the project, their purposes, and installation instructions.

## External Libraries (Third-Party)

### 1. **pandas** (>=1.5.0)
**Purpose**: Data manipulation and analysis
- Used for: Reading/writing CSV files, dataframes, data merging, filtering
- **Files using it**: 
  - `service/pipeline1.py`
  - `service/pipeline2.py`
  - `utils/access_google_sheets.py`
  - `utils/resolve_slots.py`
  - `utils/resolve_time.py`
  - `utils/group_exams.py`

**Installation**: `pip install pandas`

---

### 2. **gspread** (>=5.0.0)
**Purpose**: Google Sheets API client
- Used for: Reading from and writing to Google Sheets
- **Files using it**: `utils/access_google_sheets.py`

**Installation**: `pip install gspread`

---

### 3. **oauth2client** (>=4.1.3)
**Purpose**: Google OAuth2 authentication
- Used for: Authenticating with Google Sheets API using service account credentials
- **Files using it**: `utils/access_google_sheets.py`

**Note**: This library is deprecated in favor of `google-auth`, but still works. Consider migrating to `google-auth` and `google-auth-oauthlib` in the future.

**Installation**: `pip install oauth2client`

**Alternative (recommended for new projects)**: 
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2
```

---

### 4. **requests** (>=2.28.0)
**Purpose**: HTTP library for making API calls
- Used for: Interacting with LIV25 API to search and reserve rooms
- **Files using it**: `utils/liv25_api.py`

**Installation**: `pip install requests`

---

### 5. **python-dateutil** (>=2.8.0)
**Purpose**: Advanced date/time parsing
- Used for: Parsing various date/time formats robustly
- **Files using it**: `utils/resolve_slots.py`

**Installation**: `pip install python-dateutil`

---

### 6. **gurobipy** (>=10.0.0)
**Purpose**: Gurobi optimization solver for integer linear programming
- Used for: Optimal room assignment via ILP
- **Files using it**: `utils/gurobi_room_optimizer.py`

**Installation**: `pip install gurobipy`

**Note**: Gurobi requires a license. Academic users can obtain a free academic license from [Gurobi](https://www.gurobi.com/academia/academic-program-and-licenses/).

---

## Standard Library Modules (Built-in)

These come with Python and don't need installation:

### 1. **json**
- **Purpose**: JSON parsing and serialization
- **Files using it**: 
  - `service/pipeline1.py`
  - `utils/resolve_slots.py`
  - `utils/resolve_time.py`
  - `utils/liv25_api.py`

### 2. **os**
- **Purpose**: Operating system interface
- **Files using it**: 
  - `handler.py`
  - `service/runner.py`

### 3. **datetime**
- **Purpose**: Date and time manipulation
- **Files using it**: 
  - `utils/resolve_slots.py`
  - `utils/resolve_time.py`
  - `utils/group_exams.py`
  - `utils/liv25_api.py`

### 4. **typing**
- **Purpose**: Type hints for better code documentation
- **Files using it**: 
  - `utils/liv25_api.py`
  - `utils/group_exams.py`

### 5. **re**
- **Purpose**: Regular expressions
- **Files using it**: `utils/resolve_time.py`

---

## Installation

### Quick Install (All Dependencies)

```bash
pip install -r requirements.txt
```

**Note**: Gurobi requires a license. After installing `gurobipy`, you'll need to:
1. Obtain a Gurobi license (free for academic use)
2. Activate it: `grbgetkey <license-key>`

### Manual Installation

```bash
pip install pandas>=1.5.0
pip install gspread>=5.0.0
pip install oauth2client>=4.1.3
pip install requests>=2.28.0
pip install python-dateutil>=2.8.0
pip install gurobipy>=10.0.0
```

---

## Library Usage Summary

| Library | Primary Use Case | Files |
|---------|-----------------|-------|
| pandas | Data manipulation, CSV/DataFrame operations | Multiple files |
| gspread | Google Sheets read/write | `utils/access_google_sheets.py` |
| oauth2client | Google API authentication | `utils/access_google_sheets.py` |
| requests | HTTP API calls (LIV25) | `utils/liv25_api.py` |
| python-dateutil | Date/time parsing | `utils/resolve_slots.py` |
| gurobipy | ILP optimization | `utils/gurobi_room_optimizer.py` |
| json | JSON file handling | Multiple files |
| datetime | Date/time operations | Multiple files |
| typing | Type hints | `utils/liv25_api.py`, `utils/group_exams.py` |
| re | Regular expressions | `utils/resolve_time.py` |
| os | System operations | `handler.py`, `service/runner.py` |

---

## Optional/Alternative Libraries

### For Google Sheets (Modern Alternative)
If you want to migrate from `oauth2client` to the newer Google Auth libraries:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2
```

Then update `utils/access_google_sheets.py` to use:
```python
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
```

### For Better Type Checking
If you want stricter type checking:

```bash
pip install mypy
```

### For Testing
If you want to add tests:

```bash
pip install pytest pytest-cov
```

---

## Version Compatibility

- **Python**: 3.7+ (recommended: 3.8+)
- **pandas**: Works with Python 3.7+
- **gspread**: Requires Python 3.6+
- **oauth2client**: Works with Python 2.7+ and 3.x
- **requests**: Works with Python 3.6+
- **python-dateutil**: Works with Python 3.6+

---

## Notes

1. **oauth2client** is deprecated but still functional. Consider migrating to `google-auth` for future-proofing.
2. All libraries are actively maintained except `oauth2client`.
3. The project uses standard library modules where possible to minimize external dependencies.


