"""
Transforms an HTML contact form submission into an email-service payload.

Targets a generic transactional email API shape compatible with SendGrid,
Mailgun, and Postmark, so the destination URL can be swapped without
changing this transformer.

Expected inbound payload:
  {
    "name":    "Iman",
    "email":   "user@example.com",
    "subject": "Question about pricing",
    "message": "Hello, I wanted to ask..."
  }

Output:
  {
    "to":       "team@yourcompany.com",
    "from":     "no-reply@yourcompany.com",
    "subject":  "[Contact Form] Question about pricing",
    "text":     "From: Iman <user@example.com>\n\nHello, I wanted to ask...",
    "html":     "<p><strong>From:</strong> Iman ...",
    "reply_to": "user@example.com"
  }

Known limitation: to/from addresses are hardcoded constants. A production
deployment would make these configurable per-Route via a JSON field on the
Route model.
"""

from .base import BaseTransformer

RECIPIENT_EMAIL = 'team@yourcompany.com'
SENDER_EMAIL    = 'no-reply@yourcompany.com'


class FormToEmailTransformer(BaseTransformer):

    def transform(self, payload: dict) -> dict:
        name    = payload.get('name', 'Anonymous').strip()
        email   = payload.get('email', '').strip()
        subject = payload.get('subject', '(No subject)').strip()
        message = payload.get('message', '').strip()

        # Raises ValueError for bad data — not retried by the delivery task.
        # Retries are reserved for transient network/server failures.
        if not email:
            raise ValueError("Form submission missing required field: 'email'")

        text_body = f"From: {name} <{email}>\n\n{message}"
        html_body = (
            f"<p><strong>From:</strong> {self._escape(name)} "
            f"&lt;{self._escape(email)}&gt;</p>"
            f"<p>{self._escape(message).replace(chr(10), '<br>')}</p>"
        )

        return {
            'to':      RECIPIENT_EMAIL,
            'from':    SENDER_EMAIL,
            'subject': f'[Contact Form] {subject}',
            'text':    text_body,
            'html':    html_body,
            # Reply-To lets the team reply directly to the submitter
            'reply_to': email,
        }

    @staticmethod
    def _escape(text: str) -> str:
        """Minimal HTML escaping to prevent XSS in the HTML body."""
        return (
            text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
        )
