# Daily Dev Activity Report

This repository contains a GitHub Actions workflow that automatically generates and posts daily development activity reports to Slack using Claude AI.

## Setup

### Required Secrets

You must configure the following secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

1. **ANTHROPIC_API_KEY**: Your Anthropic API key for Claude
   - Get one at: https://console.anthropic.com/
   
2. **SLACK_WEBHOOK_URL**: Your Slack webhook URL for posting messages
   - Create one at: https://api.slack.com/messaging/webhooks

Note: `GITHUB_TOKEN` is automatically provided by GitHub Actions and does not need to be set manually.

## How It Works

1. **Schedule**: The workflow runs daily at 22:00 UTC (≈ 5pm ET)
2. **Activity Collection**: A Python script collects the last 24 hours of:
   - Pull Requests (all states: open, closed, merged)
   - Commits on the default branch
3. **AI Summary**: Claude generates a developer-grouped summary in Slack-friendly Markdown
4. **Slack Notification**: The summary is posted to your configured Slack channel

## Testing the Workflow

You can test the workflow without waiting for the scheduled run:

1. Go to your GitHub repository
2. Click on the **Actions** tab
3. Select **Daily Dev Activity Report** from the workflow list
4. Click **Run workflow** button (top right)
5. Select the branch (usually `main` or `master`)
6. Click the green **Run workflow** button

The workflow will execute immediately and you can monitor its progress in real-time. Once complete, check your Slack channel for the activity report.

## Workflow Files

- `.github/workflows/daily-dev-report.yml` - Main workflow definition
- `.github/scripts/collect_activity_single_repo.py` - Python script that collects GitHub activity

## Troubleshooting

- **No activity reported**: The workflow only reports activity from the last 24 hours. Make sure there's recent PR or commit activity.
- **Slack not receiving messages**: Verify your `SLACK_WEBHOOK_URL` secret is correctly configured.
- **Claude errors**: Check that your `ANTHROPIC_API_KEY` is valid and has sufficient credits.

