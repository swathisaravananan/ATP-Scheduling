import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# ---- AUTH HELPERS ----
def _get_client(creds_json_path="keys/atp-poc1-4e72f50119bc.json"):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_json_path, scope)
    client = gspread.authorize(creds)
    return client


# ---- FUNCTION 1: Read entire sheet as pandas df ----
def get_sheet_as_df(file_name, sheet_name):
    client = _get_client()
    sheet = client.open(file_name).worksheet(sheet_name)
    data = sheet.get_all_records()  # returns list of dicts
    df = pd.DataFrame(data)
    return df


# ---- FUNCTION 2: Update sheet using key columns ----
def update_sheet_with_df_with_columns(file_name, sheet_name, new_df, key_columns):
    client = _get_client()
    sheet = client.open(file_name).worksheet(sheet_name)

    # Read existing sheet
    existing_df = pd.DataFrame(sheet.get_all_records())

    # If sheet is empty, write the new df entirely
    if existing_df.empty:
        sheet.clear()
        sheet.update([new_df.columns.tolist()] + new_df.values.tolist())
        return

    # Merge logic – treat key columns as a composite primary key
    merged_df = existing_df.set_index(key_columns).combine_first(
        new_df.set_index(key_columns)
    ).reset_index()

    # Update entire sheet (simplest and safe)
    sheet.clear()
    sheet.update([merged_df.columns.tolist()] + merged_df.values.tolist())


def update_sheet_with_df(file_name, sheet_name, new_df):
    client = _get_client()
    sheet = client.open(file_name).worksheet(sheet_name)
    sheet.clear()
    sheet.update([new_df.columns.tolist()] + new_df.values.tolist())
    return True


# print(get_sheet_as_df("Copy of ATP Participating Courses", "FA2025_NEW"))