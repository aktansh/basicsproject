# Deploy Learning Tracker

The professor can use the public demo without an account. Each browser session starts with four fictional tasks and 50% completion. Edits disappear on a fresh session. The optional saved workspace is for real, shared records.

## 1. Put the source on GitHub

1. Extract the project ZIP. Open the folder containing app.py, tracker.py, database.py and requirements.txt.
2. Sign in at https://github.com/new. Name the repository learning-tracker, choose Public so the professor can read the source without signing in, and create the repository. Leave initialization options unchecked.
3. On the empty repository page choose **uploading an existing file**. Upload the contents of the extracted folder at the repository root. Include original/ for the initial Python prototype, tests/ and .gitignore. Enable hidden files in your file manager if necessary. Upload only the supplied project files. GitHub's web uploader does not apply local ignore rules.
4. Commit to main. Check the Code tab: app.py and requirements.txt must be immediately visible. Copy the repository address from the browser. That is your source-code link.

Alternatively, with Git installed, open a terminal in the extracted folder. Run each line individually, replacing YOUR-ACCOUNT with your GitHub username:

```sh
git init -b main
git add .
git status --short
git commit -m "Prepare Learning Tracker for Streamlit Community Cloud"
git remote add origin https://github.com/YOUR-ACCOUNT/learning-tracker.git
git push -u origin main
```

## 2. Deploy the public demo

1. Sign in at https://share.streamlit.io with GitHub and allow access to the repository.
2. Choose **Create app**, then the option to deploy from GitHub. Select your repository, branch main, and entrypoint app.py (at the root).
3. Choose an available app subdomain. In **Advanced settings**, select Python 3.12. To show a **Python source on GitHub** button in the app, paste the following into Secrets, replacing the example with the repository address copied above:

```toml
repository_url = "https://github.com/YOUR-ACCOUNT/learning-tracker"
```

4. Click **Deploy**. Wait for the dashboard and check the build logs if installation fails. In the app's sharing settings, enable public viewing. Copy the actual https://…streamlit.app address from the running app.
5. Future pushes to the selected branch update the deployment. Keep the app URL for your submission.

## 3. Optional persistent PostgreSQL workspace

1. Create an external PostgreSQL database. Get the provider's TLS-enabled connection URI and use a database role that can connect and create/read/write the learning_tracker_tasks table in its default schema.
2. Open the app's settings on Community Cloud. In **Secrets**, keep repository_url at the top and add the following block. Replace both examples privately. Use the provider's connection URI with its required SSL settings and URL-encoded credentials.

```toml
[postgres]
url = "postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require"
workspace_password = "REPLACE-WITH-A-LONG-RANDOM-PASSWORD"
```

3. Save settings and reboot the app if necessary. Visitors still land in Sample demo. Choose **Saved workspace** and enter the workspace password. On first access the app creates an empty table. Everyone who knows this password shares editing access. Sample tasks never enter this table.
4. Add one test task in the saved workspace. Reload, select Saved workspace, and unlock it again. Confirm the task remains, then delete it. If the database is offline the saved workspace shows an error. The demo remains available from the sidebar.
5. For local testing only, put the same settings in .streamlit/secrets.toml. Keep that file private. Historical tasks.json files from the original prototype stay local. The deployed app starts its saved workspace empty.

## 4. Test the professor's experience

1. Close existing private windows, open a fresh incognito/private window, and paste the deployed app URL. Confirm the dashboard opens without requesting a login. A sleeping app may need time to wake.
2. Confirm the sample banner, four tasks, two completed, 50% completion, and the pie chart. On **Deadlines**, find the English task due today.
3. Add a Studies task named “Professor test” with tomorrow's deadline. The dashboard should show five tasks and 40% completion. Check **Done** on the Tasks tab. The result should become 60% and its deadline should disappear. Uncheck it, then delete it. Confirm the original 50%.
4. Change a sample task, then reload. Confirm you get a fresh sample set. Open the source button (or the repository link separately) while signed out and check that app.py and original/app.py are readable.
5. Send your professor the copied live URL and repository URL. The live URL alone is enough to test the app. The source button lets them reach GitHub from the same page.

## Local checks for the project owner

From the project root with Python 3.12 installed:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python -m streamlit run app.py
```

The automated checks cover the sample dashboard and task controls. Follow the saved-workspace check above using your database.

Official guides: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy and https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
