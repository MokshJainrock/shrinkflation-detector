# Keep the Streamlit app awake (backup setup)

The repo already has two GitHub Actions workflows:

- `keep-alive-ping.yml` — lightweight URL ping every 15 minutes
- `keep-alive.yml` — full headless browser visit to wake the app and run the live scan

GitHub's scheduler can lag (often 2–4 hours instead of every 30 minutes). For a more reliable backup, add **cron-job.org** (free).

## Step 1: Create a cron-job.org account

Go to [cron-job.org](https://cron-job.org) and sign up (free).

## Step 2: Add a ping job (prevents sleep)

Create a cron job with:

| Field | Value |
|-------|-------|
| Title | Shrinkflation ping |
| URL | `https://shrinkflation-detector-t2ltg2v33krb7w2fsdup4a.streamlit.app/` |
| Schedule | Every 10 minutes |
| Request method | GET |
| Follow redirects | Yes |

This keeps traffic hitting the app so it is less likely to sleep.

## Step 3: Add a scan job (optional, recommended)

This triggers the full browser workflow in GitHub, independent of GitHub's cron queue.

### Create a GitHub token

1. GitHub → Settings → Developer settings → Fine-grained personal access tokens
2. Generate a token scoped to `MokshJainrock/shrinkflation-detector` only
3. Permissions: **Actions → Read and write**
4. Copy the token (you will not see it again)

### Create the cron job

| Field | Value |
|-------|-------|
| Title | Shrinkflation full scan |
| URL | `https://api.github.com/repos/MokshJainrock/shrinkflation-detector/dispatches` |
| Schedule | Every 30 minutes |
| Request method | POST |

**Headers:**

```
Authorization: Bearer YOUR_GITHUB_TOKEN
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
Content-Type: application/json
User-Agent: ShrinkflationKeepAlive/1.0
```

**Body:**

```json
{
  "event_type": "streamlit-scan"
}
```

Replace `YOUR_GITHUB_TOKEN` with the token from above. Store it only in cron-job.org, never in this repo.

## What each layer does

| Layer | Wakes sleeping app | Runs live scan |
|-------|-------------------|----------------|
| `keep-alive-ping.yml` | No | No |
| cron-job.org GET ping | No | No |
| `keep-alive.yml` (Playwright) | Yes | Yes |
| cron-job.org POST dispatch | Yes (via Playwright workflow) | Yes |

Use the ping jobs to prevent sleep. Use the Playwright workflow (GitHub schedule or cron-job.org dispatch) to wake the app and collect live data.

## Check that it is working

- GitHub Actions tab: runs for both workflows should appear regularly
- Live app header: `last scan` should update over time
- Live Tracking tab: `Live Products Tracked` should grow during the fill phase
