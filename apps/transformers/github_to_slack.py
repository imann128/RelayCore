"""
Transforms a GitHub push event payload into a Slack incoming webhook message.

GitHub push payload reference:
  https://docs.github.com/en/webhooks/webhook-events-and-payloads#push

Slack message format reference:
  https://api.slack.com/messaging/composing
"""

from .base import BaseTransformer


class GitHubToSlackTransformer(BaseTransformer):

    def transform(self, payload: dict) -> dict:
        repo    = payload.get('repository', {}).get('full_name', 'unknown/repo')
        pusher  = payload.get('pusher', {}).get('name', 'unknown')
        ref     = payload.get('ref', 'unknown')
        commits = payload.get('commits', [])

        # Build a concise commit list (max 5 to avoid Slack message spam)
        commit_lines = []
        for commit in commits[:5]:
            sha     = commit.get('id', '')[:7]
            message = commit.get('message', '').splitlines()[0]  # first line only
            commit_lines.append(f"• `{sha}` {message}")

        commit_text = '\n'.join(commit_lines) if commit_lines else '_No commits_'

        return {
            'text': f':rocket: *{pusher}* pushed to `{ref}` on *{repo}*\n{commit_text}'
        }
