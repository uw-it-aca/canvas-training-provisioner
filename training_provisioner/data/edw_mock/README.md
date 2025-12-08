# EDW Mock Data System

This directory contains mock data files for the Enterprise Data Warehouse (EDW) module when running in local development mode.

## How It Works

When `EDW_USE_MOCK_DATA = True` in Django settings, the EDW module will:

1. Detect the name of the calling function using Python's `inspect` module
2. Look for a JSON file named `{function_name}.json` in this directory
3. Load the mock data from that file and return it as a pandas DataFrame
4. Fall back to `default.json` if no specific file is found

## Mock Data File Format

Each JSON file should have this structure:

```json
{
  "data": [
    {"column1": "value1", "column2": "value2"},
    {"column1": "value3", "column2": "value4"}
  ],
  "columns": ["column1", "column2"],
  "description": "Brief description of what this mock data represents"
}
```

## Adding New Mock Data

To add mock data for a new function:

1. Create a new JSON file named after the function that calls EDW (e.g., `get_student_enrollments.json`)
2. Structure the JSON with the expected data format
3. Include a description to document what the mock data represents

## Example Usage

If you have a function like:

```python
def get_current_quarter():
    return execute_edw_query("SELECT AcademicContigYrQtrCode, AcademicYrName FROM quarters WHERE...")
```

Create a file `get_current_quarter.json` with the expected return data.