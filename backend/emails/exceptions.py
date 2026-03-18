class EmailReplyError(Exception):
    """Base exception for email reply generation failures."""


class EmailReplyQuotaExceededError(EmailReplyError):
    """Raised when the upstream AI provider quota is exhausted."""
