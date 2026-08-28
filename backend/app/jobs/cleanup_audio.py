"""Hard-delete expired opt-in voice notes.

TENANCY: This job does not return audio or transcripts to any client. It
deletes rows past expires_at (30 days) and the files they point at.
"""

from app.db import get_session_factory
from app.logging_policy import configure_logging, get_logger
from app.services.audio_store import cleanup_expired_audio


def main() -> None:
    configure_logging()
    logger = get_logger()
    db = get_session_factory()()
    try:
        deleted = cleanup_expired_audio(db)
        logger.info("cleanup_job_finished", expired_count=deleted)
    finally:
        db.close()


if __name__ == "__main__":
    main()
