"""
Transforms a GitHub push event payload into a Discord webhook message.

Discord webhook format reference:
  https://discord.com/developers/docs/resources/webhook#execute-webhook
"""

from .base import BaseTransformer


class GitHubToDiscordTransformer(BaseTransformer):

    def transform(self, payload: dict) -> dict:
        repo    = payload.get('repository', {}).get('full_name', 'unknown/repo')
        pusher  = payload.get('pusher', {}).get('name', 'unknown')
        ref     = payload.get('ref', 'unknown')
        commits = payload.get('commits', [])

        commit_lines = []
        for commit in commits[:5]:
            sha     = commit.get('id', '')[:7]
            message = commit.get('message', '').splitlines()[0]
            url     = commit.get('url', '')
            commit_lines.append(f"[`{sha}`]({url}) {message}")

        commit_text = '\n'.join(commit_lines) if commit_lines else '_No commits_'

        return {
            'content': f'**{pusher}** pushed to `{ref}` on **{repo}**\n{commit_text}'
        }
