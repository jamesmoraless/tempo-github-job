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


REQUEST_TIMEOUT = 30


def github_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def github_get(url: str, token: str, params: Optional[Dict[str, Any]] = None) -> Any:
    response = requests.get(url, headers=github_headers(token), params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_default_branch(owner: str, repo: str, token: str) -> str:
    """Get the default branch name for the repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}"

    data = github_get(url, token)
    return data["default_branch"]


def get_pull_request_details(owner: str, repo: str, token: str, number: int) -> Dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
    return github_get(url, token)


def get_prs_since(owner: str, repo: str, token: str, since: datetime) -> List[Dict[str, Any]]:
    """Fetch PRs updated since the given datetime."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

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
        
        page_prs = github_get(url, token, params=params)
        
        if not page_prs:
            break
        
        # Filter PRs updated since the cutoff time
        for pr in page_prs:
            updated_at = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))
            if updated_at >= since:
                pr_details: Dict[str, Any] = {}
                try:
                    pr_details = get_pull_request_details(owner, repo, token, pr["number"])
                except requests.RequestException as exc:
                    print(f"Warning: Failed to fetch details for PR #{pr['number']}: {exc}", file=sys.stderr)
                    pr_details = {}

                user_info = pr.get("user") or {}
                prs.append({
                    "number": pr["number"],
                    "title": pr["title"],
                    "user_login": user_info.get("login"),
                    "user_html_url": user_info.get("html_url"),
                    "state": pr["state"],
                    "merged": pr.get("merged_at") is not None,
                    "updated_at": pr["updated_at"],
                    "html_url": pr.get("html_url"),
                    "additions": pr_details.get("additions"),
                    "deletions": pr_details.get("deletions"),
                    "changed_files": pr_details.get("changed_files"),
                    "commits": pr_details.get("commits"),
                    "mergeable_state": pr_details.get("mergeable_state"),
                    "merged_at": pr_details.get("merged_at"),
                    "base_ref": (pr_details.get("base") or {}).get("ref"),
                    "head_ref": (pr_details.get("head") or {}).get("ref"),
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
        
        page_commits = github_get(url, token, params=params)
        
        if not page_commits:
            break
        
        for commit in page_commits:
            commit_author_info = (commit.get("commit") or {}).get("author") or {}
            commit_date_iso = commit_author_info.get("date")
            if not commit_date_iso:
                # Fallback to committer date if author date missing
                commit_committer_info = (commit.get("commit") or {}).get("committer") or {}
                commit_date_iso = commit_committer_info.get("date")
            if not commit_date_iso:
                continue

            commit_date = datetime.fromisoformat(commit_date_iso.replace("Z", "+00:00"))
            if commit_date >= since:
                commit_entry: Dict[str, Any] = {
                    "sha": commit["sha"],
                    "short_sha": commit["sha"][0:7],
                    "message": commit["commit"]["message"].split("\n")[0],  # First line only
                    "html_url": commit.get("html_url"),
                    "author_login": (commit.get("author") or {}).get("login"),
                    "author_name": commit_author_info.get("name"),
                    "author_email": commit_author_info.get("email"),
                    "date": commit_date_iso,
                }

                try:
                    commit_details = github_get(commit["url"], token)
                except requests.RequestException as exc:
                    print(f"Warning: Failed to fetch details for commit {commit['sha']}: {exc}", file=sys.stderr)
                    commit_details = {}

                stats = commit_details.get("stats") or {}
                files = commit_details.get("files") or []

                commit_entry.update({
                    "additions": stats.get("additions"),
                    "deletions": stats.get("deletions"),
                    "total_changes": stats.get("total"),
                    "files_changed": len(files) if isinstance(files, list) else None,
                })

                commits.append(commit_entry)
        
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

