#!/usr/bin/env python3
"""
Fetch GitHub issues via gh CLI for a given repo and time window.

Usage:
    fetch_issues.py --repo owner/repo --days 7 -o issues_raw.json
    fetch_issues.py --repo owner/repo --days 14 --limit 300 -o issues_raw.json

Requires: gh CLI installed and authenticated (gh auth login).
No external Python dependencies (stdlib only).
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone


def fetch_issues(repo: str, since_date: str, limit: int = 200) -> list[dict]:
    """Fetch issues from a GitHub repo created on or after since_date."""
    cmd = [
        "gh", "issue", "list",
        "-R", repo,
        "--search", f"created:>={since_date}",
        "--state", "all",
        "--limit", str(limit),
        "--json", "number,title,body,labels,state,createdAt,updatedAt,url,author",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print(f"Error: gh CLI timed out for repo '{repo}'", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'gh' CLI not found. Install from https://cli.github.com/", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "authentication" in stderr.lower() or "auth" in stderr.lower():
            print("Error: gh CLI not authenticated. Run 'gh auth login'.", file=sys.stderr)
        else:
            print(f"Error: gh CLI failed for repo '{repo}':\n{stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        issues = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Error: failed to parse gh output as JSON: {e}", file=sys.stderr)
        sys.exit(1)

    return issues


def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub issues via gh CLI")
    parser.add_argument("--repo", required=True, help="GitHub repo in owner/repo format")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default: 7)")
    parser.add_argument("--limit", type=int, default=200, help="Max issues to fetch (default: 200)")
    parser.add_argument("-o", "--output", default="issues_raw.json", help="Output JSON file path")
    args = parser.parse_args()

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")

    print(f"Fetching issues from {args.repo} since {since} ...", file=sys.stderr)
    issues = fetch_issues(args.repo, since, args.limit)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(issues, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(issues)} issues to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
