# Refact.ai Reddit Signal Monitor

A Flexus bot that automatically monitors Reddit every Monday at 9:00 AM UTC and generates a structured weekly signal report saved to the **Reports** section.

## What it does

- Scans **r/programming**, **r/SoftwareEngineering**, and **r/AskProgramming** (configurable)
- Analyzes posts for signals relevant to Refact.ai: product mentions, competitor comparisons, developer pain points, feature ideas, and content opportunities
- Saves a structured Markdown report to `/reports/reddit-signals/refact_weekly_reddit_signals_YYYY_MM_DD`
- Runs automatically every **Monday at 9:00 AM UTC**, or on-demand when asked

## Setup

### 1. Create a Reddit App

1. Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **Create App** at the bottom
3. Fill in:
   - **Name**: e.g. `refact-reddit-signals`
   - **Type**: select **script**
   - **Redirect URI**: `http://localhost:8080` (placeholder, not used)
4. Click **Create app**
5. Copy the **client ID** (shown under the app name) and the **client secret**

### 2. Configure the bot

In the bot's setup chat, enter:
- **Reddit Client ID**: from step above
- **Reddit Client Secret**: from step above
- **User Agent**: leave as default, or use `yourapp/1.0`
- **Subreddits**: comma or plus-separated list (default covers the main ones)

Run `verify_reddit_credentials` to confirm everything works.

## Report structure

Each report covers:
1. Product mentions & sentiment
2. Pain points & feature requests
3. Competitor mentions
4. Content opportunities
5. Product ideas
6. Top posts analyzed

Reports are saved under **Reports → reddit-signals** in the Flexus UI.
