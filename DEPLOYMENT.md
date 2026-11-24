# Learning Tracker

Run these commands from the directory containing app.py.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

## Streamlit Community Cloud

Update the existing repository with the contents of this folder, including .streamlit/config.toml and style.css. Keep the existing deployment pointed at the same repository, branch and app.py entrypoint. Python 3.12 or 3.13 is recommended. The demo opens without credentials and starts each new session with four sample tasks. The original local JSON prototype is archived in original/app.py.

Store optional settings in Community Cloud Secrets or in a local .streamlit/secrets.toml, which the included .gitignore excludes from source control.

```toml
repository_url = "https://github.com/YOUR-ACCOUNT/learning-tracker"

[postgres]
url = "postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
workspace_password = "SET-A-PRIVATE-WORKSPACE-PASSWORD"
```

## Existing PostgreSQL databases

The first authenticated access checks the schema inside a transaction. The database role needs permission to create the table for a new workspace or alter the existing learning_tracker_tasks table for the one-time migration. Existing DATE values become TIMESTAMPTZ at 23:59 in Asia/Almaty on their original calendar dates. Task IDs, titles, categories, completion state and creation times are retained. Concurrent app instances serialize schema checks. Schedule the first access when a short exclusive table lock is acceptable. Subsequent task changes use row-level writes.

## Deadline entry

Append one expression to the title or enter it in Quick deadline. Press Enter or leave the field to preview it. Adjust either picker before saving. For a literal task title containing a date or a weekday, use manual entry. Conflicting dates and ambiguous numeric dates require correction. A bare weekday means its next occurrence; “next Monday” means Monday of the next calendar week. The Next week shortcut adds seven days. All deadlines use Almaty time.

## Check a deployed instance

Open the demo in a fresh session. Add “Professor test tomorrow at 18:00”, confirm the parsed title and deadline, and check it in Active Tasks. Completion should move from 50% to 40% on creation and to 60% on completion. Restore it under Tasks and delete it to return to 50%. For persistent storage, repeat with a disposable task in Saved workspace and verify it survives a fresh login.

Community Cloud deployment guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Manual task priorities

The same first-access migration adds urgent and important Boolean columns with false defaults and permits undated tasks. Existing records retain their IDs, timestamps and deadlines and initially appear in Quadrant IV. The role must have ALTER permission. Use Edit in Tasks or Move in the matrix to reclassify a task. Sorting and filtering are session preferences.
