"""LangGraph checkpointer factory — MySQL-backed (grill: resume on crash).

The checkpointer persists every step's State to MySQL so a crashed/restarted
process can resume an in-flight task from its last checkpoint instead of
restarting from scratch. Uses the third-party ``langgraph-checkpoint-mysql``
package (AIOMySQLSaver, async) against the same DATABASE_URL the rest of the
backend uses.

Lifecycle: a single shared AIOMySQLSaver is created lazily on first use and
setup() is awaited once to create the 4 checkpoint tables
(checkpoints/checkpoint_blobs/checkpoint_writes/checkpoint_migrations). The
saver is then passed to ``StateGraph.compile(checkpointer=...)`` and the runner
supplies ``config={"configurable": {"thread_id": task_id}}`` so each task's
checkpoint chain is keyed by its task_id.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from app.core.config import get_settings
from app.core.logging import get_logger

_log = get_logger(__name__)

# Module-level singleton; setup() runs once.
_checkpointer: Any = None
# Keep the async context manager referenced for the process lifetime. Dropping
# it without __aexit__ lets the async-generator finalizer GC-close it, which
# tears down the saver's underlying MySQL connection (the observed root cause
# of "Lost connection during query" on the first checkpoint read).
_cm: Any = None
_setup_done = False


def _mysql_url_for_aiomysql(url: str) -> str:
    """Normalize DATABASE_URL for AIOMySQLSaver.from_conn_string.

    SQLAlchemy URLs look like ``mysql://user:pass@host:port/db``. The MySQL
    saver's parser accepts standard ``mysql://``; we just strip any SQLAlchemy
    ``+driver`` suffix (e.g. ``mysql+pymysql://`` → ``mysql://``).
    """
    if "+" in url.split("://", 1)[0]:
        scheme, rest = url.split("://", 1)
        scheme = scheme.split("+", 1)[0]
        return f"{scheme}://{rest}"
    return url


def _mask_url(url: str) -> str:
    """Return a log-safe URL with the password redacted."""
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        user = parts.username or ""
        netloc = f"{user}:***@{host}"
        if parts.port:
            netloc += f":{parts.port}"
        return f"{parts.scheme}://{netloc}{parts.path}"
    except Exception:
        return "<unparseable-url>"


async def get_checkpointer() -> Any | None:
    """Return the shared AIOMySQLSaver, or None if the DB is unavailable.

    Returns None (not raises) on DB errors so the runner can fall back to
    in-memory execution without a checkpointer (no resume capability, but the
    run still proceeds — matching the observability "never block execution"
    principle).
    """
    global _checkpointer, _setup_done, _cm

    if _checkpointer is not None and _setup_done:
        # Diagnostic: probe the cached connection before reuse so we can tell
        # whether a task failure is caused by a stale MySQL connection (the
        # server may have dropped it via wait_timeout / restart / network).
        # reconnect=False on purpose: we only observe, we don't mask the
        # failure during reproduction.
        conn = getattr(_checkpointer, "conn", None)
        if conn is not None:
            # The saver serializes cursor access on this shared connection via
            # its own lock; the probe must use it too, otherwise it can race
            # with a concurrent task's in-flight checkpoint query and desync
            # the MySQL protocol.
            try:
                async with _checkpointer.lock:
                    await conn.ping(reconnect=False)
                _log.debug("checkpointer cached conn alive (ping ok)")
            except Exception as e:
                _log.warning(
                    "checkpointer cached conn DEAD (ping failed); subsequent task "
                    "runs will reuse it and fail until the process restarts",
                    error=str(e),
                    exc_info=True,
                )
        return _checkpointer

    settings = get_settings()
    if not settings.database_url:
        _log.warning("checkpointer disabled: DATABASE_URL not set")
        return None

    # Escape hatch: set FLOWGRAM_CHECKPOINTER=0 to disable (e.g. when the MySQL
    # user lacks CREATE permission or aiomysql connectivity is unstable).
    import os

    if os.environ.get("FLOWGRAM_CHECKPOINTER", "1") == "0":
        _log.info("checkpointer disabled by FLOWGRAM_CHECKPOINTER=0")
        return None

    try:
        from langgraph.checkpoint.mysql.aio import AIOMySQLSaver
    except ImportError:
        _log.warning("checkpointer disabled: langgraph-checkpoint-mysql not installed")
        return None

    url = _mysql_url_for_aiomysql(settings.database_url)
    try:
        # from_conn_string is an async context manager yielding a configured saver.
        # We keep the connection alive for the process lifetime by not exiting
        # the context; setup() creates the tables.
        cm = AIOMySQLSaver.from_conn_string(url)
        _log.info("mysql checkpointer connecting", url=_mask_url(url))
        # Hold the context manager so the connection survives past this call.
        _cm = cm
        _checkpointer = await cm.__aenter__()
        _log.info("mysql checkpointer connected", url=_mask_url(url))
        # Diagnostic: record server-side settings that govern when the server
        # drops idle connections (wait_timeout) or kills big queries.
        try:
            conn = getattr(_checkpointer, "conn", None)
            if conn is not None:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT VERSION(), @@wait_timeout, @@interactive_timeout, "
                        "@@connect_timeout, @@max_allowed_packet"
                    )
                    row = await cur.fetchone()
                    _log.info(
                        "mysql server vars",
                        version=row[0],
                        wait_timeout=row[1],
                        interactive_timeout=row[2],
                        connect_timeout=row[3],
                        max_allowed_packet=row[4],
                    )
        except Exception as e:
            _log.warning("could not read mysql server vars", error=str(e), exc_info=True)
        if not _setup_done:
            await _checkpointer.setup()
            _setup_done = True
            _log.info("mysql checkpointer ready (tables created)")
        return _checkpointer
    except Exception as e:
        _log.warning(
            "checkpointer setup failed, falling back to memory-only",
            error=str(e),
            url=_mask_url(url),
            exc_info=True,
        )
        _checkpointer = None
        _cm = None
        return None


def disable_checkpointer_for_tests() -> None:
    """Test hook: force get_checkpointer() to return None (pure in-memory runs)."""
    global _checkpointer, _setup_done, _cm
    _checkpointer = None
    _cm = None
    _setup_done = True  # prevent re-setup attempts
