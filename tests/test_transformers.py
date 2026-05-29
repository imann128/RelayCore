"""
Tests for all four concrete transformers.

Transformers are pure functions of the payload — no DB, no network.
These tests verify: correct output shape, field extraction, edge cases
(empty commits, missing fields, XSS escaping), and registry lookup.
"""

import pytest

from apps.transformers.registry import get_transformer, TRANSFORMER_REGISTRY
from apps.transformers.github_to_slack   import GitHubToSlackTransformer
from apps.transformers.github_to_discord import GitHubToDiscordTransformer
from apps.transformers.calendar_to_db    import CalendarToDatabaseTransformer
from apps.transformers.form_to_email     import FormToEmailTransformer


PUSH_PAYLOAD = {
    'ref': 'refs/heads/main',
    'pusher': {'name': 'iman'},
    'repository': {'full_name': 'org/repo'},
    'commits': [
        {'id': 'a1b2c3d4e5f6', 'message': 'Fix login bug\n\nLonger description', 'url': 'https://github.com/commit/a1b2c3d'},
        {'id': 'b2c3d4e5f6a7', 'message': 'Add tests', 'url': 'https://github.com/commit/b2c3d4e'},
    ],
}


class TestGitHubToSlackTransformer:

    def setup_method(self):
        self.t = GitHubToSlackTransformer()

    def test_output_has_text_key(self):
        result = self.t.transform(PUSH_PAYLOAD)
        assert 'text' in result

    def test_pusher_name_in_output(self):
        result = self.t.transform(PUSH_PAYLOAD)
        assert 'iman' in result['text']

    def test_repo_name_in_output(self):
        result = self.t.transform(PUSH_PAYLOAD)
        assert 'org/repo' in result['text']

    def test_ref_in_output(self):
        result = self.t.transform(PUSH_PAYLOAD)
        assert 'refs/heads/main' in result['text']

    def test_only_first_line_of_multiline_commit_message(self):
        result = self.t.transform(PUSH_PAYLOAD)
        assert 'Fix login bug' in result['text']
        assert 'Longer description' not in result['text']

    def test_max_5_commits_shown(self):
        many_commits = [
            {'id': f'abcdef{i}00000', 'message': f'Commit {i}', 'url': ''}
            for i in range(10)
        ]
        payload = {**PUSH_PAYLOAD, 'commits': many_commits}
        result = self.t.transform(payload)
        # Count bullet points — only 5 should appear
        assert result['text'].count('•') == 5

    def test_empty_commits_handled_gracefully(self):
        payload = {**PUSH_PAYLOAD, 'commits': []}
        result = self.t.transform(payload)
        assert 'No commits' in result['text']


class TestGitHubToDiscordTransformer:

    def setup_method(self):
        self.t = GitHubToDiscordTransformer()

    def test_output_has_content_key(self):
        result = self.t.transform(PUSH_PAYLOAD)
        assert 'content' in result

    def test_commit_url_in_output(self):
        result = self.t.transform(PUSH_PAYLOAD)
        assert 'https://github.com/commit/a1b2c3d' in result['content']

    def test_short_sha_used(self):
        result = self.t.transform(PUSH_PAYLOAD)
        assert 'a1b2c3d' in result['content']
        assert 'a1b2c3d4e5f6' not in result['content']   # full SHA not shown


class TestCalendarToDatabaseTransformer:

    def setup_method(self):
        self.t = CalendarToDatabaseTransformer()

    def test_returns_source_field(self):
        result = self.t.transform({})
        assert result['source'] == 'google_calendar'

    def test_extracts_channel_and_resource_ids(self):
        payload = {
            'channelId': 'my-channel-id',
            'resourceId': 'res-123',
            'resourceState': 'exists',
        }
        result = self.t.transform(payload)
        assert result['channel_id'] == 'my-channel-id'
        assert result['resource_id'] == 'res-123'
        assert result['resource_state'] == 'exists'

    def test_missing_fields_default_to_empty_string(self):
        result = self.t.transform({})
        for key in ('channel_id', 'resource_id', 'resource_uri', 'resource_state'):
            assert result[key] == ''


class TestFormToEmailTransformer:

    def setup_method(self):
        self.t = FormToEmailTransformer()

    def _valid_payload(self, **overrides):
        base = {
            'name': 'Iman',
            'email': 'iman@example.com',
            'subject': 'Question about pricing',
            'message': 'Hello there',
        }
        return {**base, **overrides}

    def test_subject_prefixed_with_contact_form(self):
        result = self.t.transform(self._valid_payload())
        assert result['subject'].startswith('[Contact Form]')

    def test_reply_to_is_submitter_email(self):
        result = self.t.transform(self._valid_payload())
        assert result['reply_to'] == 'iman@example.com'

    def test_name_and_email_in_text_body(self):
        result = self.t.transform(self._valid_payload())
        assert 'Iman' in result['text']
        assert 'iman@example.com' in result['text']

    def test_missing_email_raises_value_error(self):
        """Missing email = bad data — should NOT trigger Celery retries."""
        with pytest.raises(ValueError, match='email'):
            self.t.transform(self._valid_payload(email=''))

    def test_xss_escaped_in_html_body(self):
        """Malicious name field must be escaped in the HTML output."""
        payload = self._valid_payload(name='<script>alert(1)</script>')
        result = self.t.transform(payload)
        assert '<script>' not in result['html']
        assert '&lt;script&gt;' in result['html']


class TestTransformerRegistry:

    def test_all_four_transformers_registered(self):
        expected = {'github_to_slack', 'github_to_discord', 'calendar_to_db', 'form_to_email'}
        assert expected == set(TRANSFORMER_REGISTRY.keys())

    def test_get_transformer_returns_correct_class(self):
        assert get_transformer('github_to_slack') is GitHubToSlackTransformer
        assert get_transformer('form_to_email')   is FormToEmailTransformer

    def test_get_transformer_raises_for_unknown_key(self):
        with pytest.raises(ValueError, match='unknown_transformer'):
            get_transformer('unknown_transformer')
