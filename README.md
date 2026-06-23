# 🚀 AI-Powered Slack Learning Coordinator

Welcome to our hackathon repository! This project contains **Feature 1: Proactive Struggling Learner Identification**. 

The application architecture functions as an event-driven engine: it monitors public Slack channels via real-time webhooks, tallies user question volume using an in-memory 2-column database structure, and triggers a private, highly-contextual administrative alert via the official Slack Real-Time Search (RTS) API once a student hits a threshold of 3 or more questions.

---

## Step 1: Clone the Project & Install Dependencies

1. Open your terminal on your machine and clone this repository:
   git clone <PASTE_YOUR_REPOSITORY_GITHUB_URL_HERE>
   cd <YOUR_REPOSITORY_FOLDER_NAME>

2. pip3 install flask slack_sdk

## Step 2: Download, Authenticate, and Start Ngrok

Because our Flask application runs locally (localhost:8080), it sits behind your local firewall. Slack operates in the public cloud and cannot send event notifications to your laptop without a secure public tunnel. We use Ngrok to bridge this gap.

1. Go to ngrok.com, sign up for a free account, and download the binary matching your operating system.

2. Open your terminal and link your local installation to your account using your personal authtoken (found on your Ngrok Web Dashboard):
    ngrok config add-authtoken YOUR_PERSONAL_AUTHTOKEN_HERE

3. Boot up the network tunnel to listen to our specific Flask backend port:
    ngrok http 8080

4. CRITICAL: Leave this terminal window running permanently! Copy the generated public forwarding URL. It will look exactly like this: https://xxxx-xxxx.ngrok-free.dev

## Step 3: Configure the Slack App Developer Portal
1. Navigate to the Slack App Management Dashboard and click on your app's configuration panel.

2. OAuth & Permissions Scopes Configuration:
    Scroll down to Scopes.

    Under Bot Token Scopes, add these five scopes: channels:history, chat:write, groups:history, im:history, mpim:history.

    Under User Token Scopes, add exactly: search:read (This is mandatory. Without it, the Real-Time Search API will reject our historical data queries).

3. Scroll back to the top of the OAuth page and click the large green Reinstall to Workspace button.

4. Copy your newly refreshed Bot Token (xoxb-...) and User Token (xoxp-...).

5. Acquire your Coordinator ID: Open your Slack workspace. Click your own Profile Picture -> Select Profile -> Click the three dots ... More -> Click Copy Member ID (This string starting with U acts as our ADMIN_SLACK_ID).

6. Event Subscriptions (The Real-Time Handshake):
    On the left sidebar, click Event Subscriptions and toggle it to On.

    In the Request URL text box, paste your active Ngrok forwarding URL from Step 2 and append /slack/events to the end of it. (Example: https://xxxx.ngrok-free.dev/slack/events). Wait 2 seconds for it to state Verified.

    Scroll down to Subscribe to bot events, click Add Bot User Event, and select message.channels. Click Save Changes.

## Step 4: Update Credentials & Boot the Backend

1. Open app.py in your code editor (VS Code) and paste our verified credentials into the top configuration block:
    SLACK_BOT_TOKEN = "xoxb-your-copied-bot-token"
    SLACK_USER_TOKEN = "xoxp-your-copied-user-token"
    ADMIN_SLACK_ID = "UXXXXXXXXXX"  # Paste your copied Member ID here
2. python3 app.py

## Step 5: Live Simulation Test
1. Enter your Slack sandbox workspace and open a public channel (such as #general).

2. Simulate a struggling student by sending 3 separate messages that explicitly end with a ? character.

3. Look at your Python terminal running app.py. You will see our database engine logging a custom 2-column matrix tracker tabular display, actively sorting users dynamically by question count.

4. Open the private Apps DM navigation tab on your Slack sidebar. You will notice our agent kept the public channel completely clear to preserve student confidence. Instead, it routed a clean, comprehensive AI Learning Coordinator Report directly to your DM feed, detailing the student's exact live search history logs!