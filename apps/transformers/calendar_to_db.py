"""
Transforms a Google Calendar webhook notification into a flat dict
suitable for inserting as a database row.

The header metadata gap (now fixed):
  Google Calendar sends important metadata in HTTP headers, not the body:
    X-Goog-Channel-ID        — your registered channel
    X-Goog-Resource-ID       — the calendar resource that changed
    X-Goog-Resource-State    — 'sync', 'exists', or 'not_exists'
    X-Goog-Resource-URI      — URI of the changed resource
    X-Goog-Channel-Expiration — when this channel registration expires

  The transformer only receives raw_payload. By the time it runs (inside
  a Celery task), the HTTP request is gone. The fix is in the view:
  ReceiveWebhookView._inject_provider_metadata() extracts all X-Goog-*
  headers at ingestion time and merges them into the payload under
  payload['__goog_meta'] before persisting to DB.

  This transformer reads from payload['__goog_meta'] — no DB access needed.

Google Calendar push notification reference:
  https://developers.google.com/calendar/api/guides/push
"""

from .base import BaseTransformer


class CalendarToDatabaseTransformer(BaseTransformer):

    def transform(self, payload: dict) -> dict:
        """
        Extract calendar notification metadata into a flat record dict.

        The destination for this transformer is expected to be an internal
        HTTP endpoint that writes the record to a database table.

        Args:
            payload: Parsed JSON body from Google Calendar, augmented with
                     '__goog_meta' dict injected by the ingestion view.

        Returns:
            A flat dict with normalized field names ready for DB insertion.
        """
        # Read from __goog_meta (injected by _inject_provider_metadata).
        # Fall back to top-level payload keys for backwards compatibility
        # with any deliveries ingested before the fix.
        meta = payload.get('__goog_meta', {})

        channel_id     = meta.get('channel_id')    or payload.get('channelId', '')
        resource_id    = meta.get('resource_id')   or payload.get('resourceId', '')
        resource_uri   = meta.get('resource_uri')  or payload.get('resourceUri', '')
        resource_state = meta.get('resource_state') or payload.get('resourceState', '')
        expiration     = meta.get('expiration')    or payload.get('expiration', '')

        # resource_state='sync' is a handshake ping — not a real change event.
        # Flag it so the consumer can decide whether to process or ignore.
        is_sync_ping = resource_state == 'sync'

        return {
            'channel_id':     channel_id,
            'resource_id':    resource_id,
            'resource_uri':   resource_uri,
            'resource_state': resource_state,
            'expiration':     expiration,
            'is_sync_ping':   is_sync_ping,
            'kind':           payload.get('kind', ''),
            'source':         'google_calendar',
        }
