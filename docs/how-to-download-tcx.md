# How to Manually Export TCX Files Using a Session Cookie

This guide details the definitive method for downloading your TCX workout files from MapMyRun. The project originally attempted to automate the login process with Selenium, but this proved unreliable due to modern web application security features like reCAPTCHA and dynamic login forms.

The most robust and successful method is to bypass the login form entirely by providing the script with the session cookie from an already authenticated browser session.

## Step-by-Step Instructions

### 1. Log into MapMyRun

In your web browser (e.g., Chrome, Firefox), navigate to `https://www.mapmyrun.com/` and log in with your username and password as you normally would.

### 2. Open Developer Tools

Once logged in, open your browser's Developer Tools. You can usually do this by pressing **F12** or **Ctrl+Shift+I** (Cmd+Option+I on Mac).

### 3. Find the Cookie Request Header

- Navigate to the **"Network"** tab in the Developer Tools.
- You may need to refresh the page (F5) to see network activity.
- Click on any request in the list that is being made to `www.mapmyrun.com`.
- A new pane will appear. Look for the **"Request Headers"** section.

### 4. Copy the Full Cookie String

- In the "Request Headers" section, find the header named **`Cookie:`**.
- The value will be a very long string containing many key-value pairs separated by semicolons (e.g., `notice_behavior=...; access-token=...; ...`).
- **Right-click** on the cookie header's value and select **"Copy value"**. Be sure to copy the entire string.

### 5. Update Your `.env` Configuration File

- Open the `config/.env` file in the project directory.
- Create or update the `MAPMYRUN_COOKIE_STRING` variable.
- **Crucially, you must wrap the entire cookie string you copied in SINGLE QUOTES (`'`)**. This is because the cookie string itself contains special characters (`#` and `"`) that will otherwise break the parser.

Your `config/.env` file should look like this:

```dotenv
# Use single quotes to wrap the entire string.
MAPMYRUN_COOKIE_STRING='notice_behavior=implied,eu; access-token=...; __privaci_latest_published_version=7'

# Strava API Credentials
STRAVA_CLIENT_ID=your_strava_client_id
STRAVA_CLIENT_SECRET=your_strava_client_secret
```

### 6. Run the Script

You are now ready to run the downloader. Execute the main script from the project root to test a single download:

```bash
python main.py
```

If the script runs successfully, you can proceed with the full migration plan. If the cookie expires in the future, you will need to repeat these steps to get a new one. 