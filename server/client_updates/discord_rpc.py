"""Discord Rich Presence integration.

Talks to the local Discord desktop app over its IPC socket via pypresence. This
is entirely best-effort: if Discord isn't running, isn't installed, or the
connection drops mid-game, every call here just quietly no-ops instead of
raising -- Rich Presence must never be able to crash or block the game.

pypresence's connect()/update() are both SYNCHRONOUS, BLOCKING calls under the
hood (they run an asyncio event loop to completion on whatever thread calls
them) -- calling them directly from the main game loop stalls every frame
while Discord's IPC round-trips, and connect() attempts in particular can hang
noticeably when Discord isn't running. So all of it runs on one dedicated
background worker thread here, the same way network.py keeps HTTP calls off
the main thread; the game thread only ever touches a queue and a couple of
plain booleans/timestamps.
"""
import time
import threading
import queue

try:
    from pypresence import Presence
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False

CLIENT_ID = "1544396219814649896"
LARGE_IMAGE_KEY = "image_2026-09-01_132517251"
SMALL_IMAGE_KEY = "image_2026-09-01_133325918"
LARGE_IMAGE_TEXT = "Polygon Rush"

# Discord rate-limits presence updates to roughly one per 15 seconds; anything
# faster than that risks the update just being dropped. We debounce well under
# that instead of calling update() every time the caller's state changes.
_MIN_UPDATE_INTERVAL = 16.0


class DiscordRPC:
    def __init__(self):
        self._rpc = None
        self._connected = False
        self._last_update_time = 0.0
        self._last_payload = None
        self._session_start = int(time.time())
        self._jobs = queue.Queue()
        self._worker = None
        if _AVAILABLE:
            self._worker = threading.Thread(target=self._run_worker, daemon=True)
            self._worker.start()

    def _run_worker(self):
        while True:
            job = self._jobs.get()
            if job is None:
                self._discard_rpc()
                return
            kind, payload = job
            try:
                if kind == "connect":
                    if self._rpc is None:
                        self._rpc = Presence(CLIENT_ID)
                    self._rpc.connect()
                    self._connected = True
                elif kind == "update":
                    if self._rpc is not None:
                        self._rpc.update(**payload)
                elif kind == "close":
                    self._discard_rpc()
                    return
            except Exception:
                # Discord not running / connection dropped / IPC hiccup -- drop
                # the connection and let a later "connect" job re-establish it.
                self._discard_rpc()

    def _discard_rpc(self):
        # Always explicitly close pypresence's connection here rather than just
        # dropping the reference and letting the garbage collector find it later.
        # pypresence opens its Discord IPC pipe via asyncio, and if that object
        # is instead cleaned up by a random later GC pass (possibly on another
        # thread, possibly after the loop's already torn down), asyncio's
        # Windows ProactorEventLoop pipe transport can end up __del__'d in a
        # half-closed state where even building the warning message crashes
        # ("Exception ignored in: ProactorBasePipeTransport.__del__ ... I/O
        # operation on closed pipe") -- harmless, but noisy console spam. Closing
        # synchronously here, right where we already know the connection is
        # being torn down, gives it a clean, ordinary shutdown path instead.
        self._connected = False
        if self._rpc is not None:
            try:
                self._rpc.close()
            except Exception:
                pass
        self._rpc = None

    @property
    def _is_connected(self):
        return self._connected

    def connect(self):
        """Best-effort connect. Safe to call repeatedly (e.g. retry from the
        main loop) -- queued to the worker thread, never blocks the caller."""
        if not _AVAILABLE or self._connected or self._worker is None:
            return
        self._jobs.put(("connect", None))

    def update(self, details=None, state=None, small_text=None, use_start_time=True, force=False):
        """details/state are the two lines of text Discord shows (details on
        top). Call this whenever the player's high-level activity changes
        (menu, editing, playing a level, etc) -- not every frame. Debounced
        internally, and the actual IPC call is queued to the worker thread."""
        if not self._connected:
            return
        now = time.time()
        payload_key = (details, state, small_text)
        if not force and payload_key == self._last_payload and (now - self._last_update_time) < _MIN_UPDATE_INTERVAL:
            return
        if not force and (now - self._last_update_time) < 1.0:
            # Never hammer it even for a genuinely new state -- Discord will just
            # ignore updates sent too close together anyway.
            return
        kwargs = {
            "large_image": LARGE_IMAGE_KEY,
            "large_text": LARGE_IMAGE_TEXT,
            "small_image": SMALL_IMAGE_KEY,
        }
        if details:
            kwargs["details"] = details
        if state:
            kwargs["state"] = state
        if small_text:
            kwargs["small_text"] = small_text
        if use_start_time:
            kwargs["start"] = self._session_start
        self._last_update_time = now
        self._last_payload = payload_key
        self._jobs.put(("update", kwargs))

    def reset_timer(self):
        """Restarts the 'elapsed' counter Discord shows (e.g. when a new level
        attempt or editing session begins) rather than showing time since the
        whole game process launched."""
        self._session_start = int(time.time())

    def close(self):
        if self._worker is not None:
            self._jobs.put(("close", None))
