"""OpenDNA exception hierarchy.

All custom exceptions inherit from OpenDnaError so callers can catch them
in one place. User-facing error messages are designed to be clear and actionable.
"""

from __future__ import annotations


class OpenDnaError(Exception):
    """Base class for all OpenDNA exceptions."""

    user_message: str = "An unexpected error occurred."
    suggestion: str = ""

    def __init__(self, message: str = "", suggestion: str = ""):
        super().__init__(message or self.user_message)
        self.user_message = message or self.user_message
        if suggestion:
            self.suggestion = suggestion

    def to_dict(self) -> dict:
        return {
            "error": self.__class__.__name__,
            "message": self.user_message,
            "suggestion": self.suggestion,
        }


class InvalidSequenceError(OpenDnaError):
    user_message = "The sequence contains invalid characters."
    suggestion = "Use only standard amino acid one-letter codes (ACDEFGHIKLMNPQRSTVWY)."


class SequenceTooLongError(OpenDnaError):
    user_message = "The sequence is too long for this operation."
    suggestion = "Try a shorter sequence, or use a GPU for sequences longer than 250 residues."


class StructureNotFoundError(OpenDnaError):
    user_message = "No structure available for this protein."
    suggestion = "Run 'Predict Structure' first to fold the protein."


class ModelNotAvailableError(OpenDnaError):
    user_message = "The required ML model is not available on this system."
    suggestion = "Models download automatically on first use. Check your internet connection."


class HardwareLimitError(OpenDnaError):
    user_message = "Your hardware doesn't have enough resources for this operation."
    suggestion = "Try a smaller protein, or use cloud burst mode for large jobs."


class JobNotFoundError(OpenDnaError):
    user_message = "Job not found."
    suggestion = "Check the job ID, or look in Dashboard → Recent Jobs."


class ProjectNotFoundError(OpenDnaError):
    user_message = "Project not found."
    suggestion = "Check the project name, or list available projects via the API."


class ExternalServiceError(OpenDnaError):
    user_message = "An external service (UniProt, PDB, AlphaFold) is not responding."
    suggestion = "Check your internet connection. The service may be temporarily down."


class MutationFormatError(OpenDnaError):
    user_message = "Invalid mutation format."
    suggestion = "Use standard format like K48R (from-position-to)."


class LlmProviderError(OpenDnaError):
    user_message = "No LLM provider is available."
    suggestion = (
        "Install Ollama from https://ollama.com and pull a model (e.g. 'ollama pull llama3.2:3b'),"
        " or set ANTHROPIC_API_KEY / OPENAI_API_KEY environment variables."
    )


def to_friendly(exc: Exception) -> dict:
    """Convert any exception to a user-friendly dict.

    OpenDnaError instances get their suggestion attached. Other exceptions
    are wrapped with a generic friendly message.
    """
    if isinstance(exc, OpenDnaError):
        return exc.to_dict()

    # Map common Python errors to friendly messages
    if isinstance(exc, FileNotFoundError):
        return {
            "error": "FileNotFoundError",
            "message": f"File not found: {exc}",
            "suggestion": "Check the path is correct.",
        }
    if isinstance(exc, PermissionError):
        return {
            "error": "PermissionError",
            "message": str(exc),
            "suggestion": "Check file permissions or close any application using the file.",
        }
    if isinstance(exc, ConnectionError):
        return {
            "error": "ConnectionError",
            "message": "Could not connect to a remote service.",
            "suggestion": "Check your internet connection.",
        }
    if isinstance(exc, TimeoutError):
        return {
            "error": "TimeoutError",
            "message": "The operation timed out.",
            "suggestion": "Try again, or use a smaller input.",
        }
    if isinstance(exc, MemoryError):
        return {
            "error": "MemoryError",
            "message": "Out of memory.",
            "suggestion": "Try a smaller protein or close other applications.",
        }
    if isinstance(exc, ImportError):
        return {
            "error": "ImportError",
            "message": f"Missing dependency: {exc}",
            "suggestion": "Run `pip install -e \".[dev]\"` to install all dependencies.",
        }

    return {
        "error": exc.__class__.__name__,
        "message": str(exc),
        "suggestion": "If this keeps happening, please open an issue at https://github.com/dyber-pqc/OpenDNA/issues",
    }
