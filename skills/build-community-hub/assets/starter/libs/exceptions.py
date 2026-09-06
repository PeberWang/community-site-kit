# -*- coding: utf-8 -*-
"""Community Site Kit custom exceptions."""


class GiftboxException(Exception):
    """Base exception."""


class LLMServiceException(GiftboxException):
    """LLM call failed."""


class ConfigurationException(GiftboxException):
    """Invalid configuration."""


class FileUploadException(GiftboxException):
    """File upload failed."""


class FileDownloadException(GiftboxException):
    """A requested attachment is unavailable for authenticated download."""


class StoreException(GiftboxException):
    """JSON store read/write failed."""


class GuideConflictException(GiftboxException):
    """A guide changed after an editor or candidate started work."""


class GuideValidationException(GiftboxException):
    """A guide candidate did not pass the required publication checks."""
