#!/usr/bin/env python3
"""
Collects the last 24 hours of GitHub activity (PRs and commits) for the current repository.
Outputs JSON to stdout.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional


def get_default_branch(owner: str, repo: str, token: str) -> str:
    """Get the default branch name for the repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["default_branch"]


def get_prs_since(owner: str, repo: str, token: str, since: datetime) -> List[Dict[str, Any]]:
    """Fetch PRs updated since the given datetime."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    prs = []
    page = 1
    per_page = 50
    
    while True:
        params = {
            "state": "all",
            "sort": "updated",
            "direction": "desc",
            "per_page": per_page,
            "page": page
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        page_prs = response.json()
        
        if not page_prs:
            break
        
        # Filter PRs updated since the cutoff time
        for pr in page_prs:
            updated_at = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))
            if updated_at >= since:
                prs.append({
                    "number": pr["number"],
                    "title": pr["title"],
                    "user": pr["user"]["login"] if pr["user"] else None,
                    "state": pr["state"],
                    "merged": pr.get("merged_at") is not None,
                    "updated_at": pr["updated_at"]
                })
            else:
                # Since PRs are sorted by updated_at descending, we can stop here
                return prs
        
        # If we got fewer results than per_page, we're done
        if len(page_prs) < per_page:
            break
        
        page += 1
    
    return prs


def get_commits_since(owner: str, repo: str, token: str, branch: str, since: datetime) -> List[Dict[str, Any]]:
    """Fetch commits on the default branch since the given datetime."""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    commits = []
    page = 1
    per_page = 50
    
    while True:
        params = {
            "sha": branch,
            "since": since.isoformat(),
            "per_page": per_page,
            "page": page
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        page_commits = response.json()
        
        if not page_commits:
            break
        
        for commit in page_commits:
            commit_date = datetime.fromisoformat(commit["commit"]["author"]["date"].replace("Z", "+00:00"))
            if commit_date >= since:
                commits.append({
                    "sha": commit["sha"],
                    "message": commit["commit"]["message"].split("\n")[0],  # First line only
                    "author": commit["author"]["login"] if commit.get("author") else None,
                    "date": commit["commit"]["author"]["date"]
                })
        
        # If we got fewer results than per_page, we're done
        if len(page_commits) < per_page:
            break
        
        page += 1
    
    return commits


def main():
    # Read environment variables
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    
    if not repository:
        print("Error: GITHUB_REPOSITORY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    owner, repo = repository.split("/", 1)
    
    # Calculate 24 hours ago in UTC
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    
    # Get default branch
    try:
        default_branch = get_default_branch(owner, repo, token)
    except Exception as e:
        print(f"Error getting default branch: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Collect PRs
    try:
        prs = get_prs_since(owner, repo, token, since)
    except Exception as e:
        print(f"Error fetching PRs: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Collect commits
    try:
        commits = get_commits_since(owner, repo, token, default_branch, since)
    except Exception as e:
        print(f"Error fetching commits: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Build output JSON
    output = {
        "repo": repository,
        "since": since.isoformat(),
        "prs": prs,
        "commits": commits
    }
    
    # Output JSON to stdout
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

