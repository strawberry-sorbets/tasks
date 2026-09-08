"""
Resets checked-off tasks in a Notion database on a daily/weekly basis.

Requires a Notion database with these properties:
  - Name       (Title)
  - Done       (Checkbox)
  - Frequency  (Select, with options "Daily" and "Weekly")

Environment variables required:
  - NOTION_TOKEN         Your Notion integration's secret token
  - NOTION_DATABASE_ID   The ID of your to-do database
"""

import os
import datetime
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

NOTION_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

QUERY_URL = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
PAGE_URL = "https://api.notion.com/v1/pages/{}"


def get_all_tasks():
    """Fetch every page (task) in the database, handling pagination."""
    tasks = []
    payload = {}
    while True:
        resp = requests.post(QUERY_URL, headers=HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
        tasks.extend(data["results"])
        if data.get("has_more"):
            payload["start_cursor"] = data["next_cursor"]
        else:
            break
    return tasks


def uncheck_task(page_id):
    """Set the Done checkbox back to unchecked for a given page."""
    url = PAGE_URL.format(page_id)
    payload = {"properties": {"Done": {"checkbox": False}}}
    resp = requests.patch(url, headers=HEADERS, json=payload)
    resp.raise_for_status()


def main():
    today = datetime.date.today()
    is_monday = today.weekday() == 0  # Monday == 0, adjust if you want a different weekly reset day

    tasks = get_all_tasks()
    reset_count = 0

    for task in tasks:
        props = task["properties"]

        freq_prop = props.get("Frequency", {}).get("select")
        freq = freq_prop["name"] if freq_prop else None

        is_done = props.get("Done", {}).get("checkbox", False)
        if not is_done:
            continue  # already unchecked, nothing to reset

        if freq == "Daily":
            uncheck_task(task["id"])
            reset_count += 1
        elif freq == "Weekly" and is_monday:
            uncheck_task(task["id"])
            reset_count += 1

    print(f"Reset {reset_count} task(s) on {today.isoformat()}")


if __name__ == "__main__":
    main()
  name: Reset Notion Tasks

on:
  schedule:
    # Runs every day at 06:00 UTC. Adjust for your timezone,
    # since GitHub Actions cron always uses UTC.
    - cron: "0 6 * * *"
  workflow_dispatch: {}  # lets you trigger it manually from the Actions tab to test

jobs:
  reset:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install requests
      - name: Run reset script
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
        run: python reset_tasks.py
