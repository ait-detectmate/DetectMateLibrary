"""A FIFO queue for original log lines with background disk spill and refill.

Accept immutable bytes, typically from open(input_path, "rb"). Lines are
written and returned unchanged: no JSON, text encoding, or pickling.
The next 10,000 lines stay ready in RAM by default. Overflow is queued for
batched background writes. When RAM drops below the refill threshold, the
worker reloads the oldest spilled lines.

The simple interface is add_line(line) and get_line() -> bytes | None.
Adding a line accepts it immediately without waiting for disk or capacity.
Pending overflow has no count or per-line size limit. If incoming data is
faster than the writer, pending lines can therefore grow in RAM. Written
batches release their line references immediately, allowing memory reuse;
Python does not necessarily return that memory to the operating system.
get_line returns None if nothing is ready now, including during a refill.
Both methods use short shared locks. All file I/O happens in the worker.

The raw spool and its ".lengths" sidecar must not already exist. The sidecar
keeps line boundaries exact even without trailing newlines. Use a real disk
directory, not tmpfs. These files are temporary, not a durable log archive:
normal close removes them and discards remaining unprocessed work. Drain
the queue first. Initialization and close wait for the worker.
"""

from collections import deque
from pathlib import Path
from queue import Empty
from struct import Struct
from threading import Condition, Event, Thread


class DiskBackedQueue:
    _LENGTH = Struct("<Q")

    def __init__(self, path, ram_limit=10_000, refill_at=5_000,
                 batch_size=1_000):
        """Create the buffer and start its background disk worker.

        Args:
            path (str or os.PathLike):
                Temporary raw-line spool path. Its parent directory must
                exist, and neither this file nor path + ".lengths" may exist.
                Use a real disk directory rather than tmpfs. Normal close
                removes both files. These are temporary queue storage, not
                a durable archive or a restartable queue.

            ram_limit (int, default 10_000):
                Maximum number of lines ready for retrieval in RAM. Further
                lines go to an unbounded pending-write deque and are spilled
                to disk. This limits ready lines, not total memory or bytes.
                Very large lines or a slow writer can still consume more RAM.

            refill_at (int, default 5_000):
                Start background refill when ready lines drop strictly below
                this count. With defaults, 5,000 ready lines do not trigger
                refill, but 4,999 do. Once triggered, refill continues toward
                ram_limit while older lines remain on disk. Must be positive
                and no greater than ram_limit. get_line() may temporarily
                return None while the asynchronous refill is in progress.

            batch_size (int, default 1_000):
                Maximum lines per background write or refill batch. Smaller
                batches are handled immediately; the worker does not wait
                to accumulate this many lines. The writer removes a batch
                from the pending deque, holds it during the write, flushes
                it to the file, then clears all its line references. Larger
                batches can improve throughput but hold more lines at once.

        Raises:
            ValueError: A count is not a positive integer, or refill_at
                exceeds ram_limit. Booleans are not valid counts.
            RuntimeError: The worker cannot initialize its files. The
                underlying exception is available as the cause.

        Notes:
            There is no pending count limit or maximum line size. add_line()
            accepts bytes without waiting for the disk; invalid input and
            worker failures still raise exceptions. Pending memory can grow
            if input outpaces writing. Releasing written line references
            frees memory for reuse, not necessarily a visible RSS decrease.
            Caller-owned references continue to keep those lines alive.
            Construction and close() wait for the worker. Consume needed
            lines before close(), which discards outstanding work.
        """
        counts = (ram_limit, refill_at, batch_size)
        if any(not isinstance(value, int) or isinstance(value, bool)
               or value <= 0 for value in counts):
            raise ValueError("Counts must be positive integers")
        if refill_at > ram_limit:
            raise ValueError("refill_at must not exceed ram_limit")

        self._path = Path(path)
        self._index_path = Path(str(self._path) + ".lengths")
        self._ram_limit = ram_limit
        self._refill_at = refill_at
        self._batch_size = batch_size
        self._ready = deque()
        self._pending = deque()
        self._condition = Condition()
        self._started = Event()
        self._finished = Event()
        self._failed = Event()
        self._error = None
        self._closed = False
        self._input_finished = False
        self._disk_pending = 0
        self._write_in_flight = 0
        self._spilled_total = 0
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()
        self._started.wait()
        self._check()

    def _check(self):
        if self._failed.is_set():
            raise RuntimeError("Background spool worker failed") from self._error

    def add_line(self, line):
        """Accept original bytes immediately and return True.

        Disk spill and refill are automatic. There is no queue.Full condition.
        Invalid input, closed input, and worker failures raise exceptions.
        """
        self.put_nowait(line)
        return True

    def get_line(self):
        """Return the oldest ready bytes, or None if nothing is ready now.

        None can be temporary while disk lines are being loaded; it does not
        mean the entire queue is empty or the input stream is finished.
        """
        try:
            return self.get_nowait()
        except Empty:
            return None

    def put_nowait(self, line):
        """Accept original bytes without waiting for disk or capacity.

        The first ram_limit lines can enter RAM immediately even if the worker
        has not been scheduled. Later arrivals cannot overtake disk backlog.
        """
        if not isinstance(line, bytes):
            raise TypeError("Pass bytes; read the input file in binary mode")
        with self._condition:
            self._check()
            if self._closed or self._input_finished:
                raise RuntimeError("Input is closed")
            backlog = self._pending or self._disk_pending or self._write_in_flight
            if len(self._ready) < self._ram_limit and not backlog:
                self._ready.append(line)
            else:
                self._pending.append(line)
            self._condition.notify()

    def get_nowait(self):
        """Return the oldest line as bytes, or raise Empty without disk I/O."""
        with self._condition:
            self._check()
            if self._closed:
                raise RuntimeError("Queue is closed")
            if not self._ready:
                raise Empty
            line = self._ready.popleft()
            self._condition.notify()
            return line

    def finish_input(self):
        """Call after submitting the last line; do not submit further lines."""
        with self._condition:
            self._check()
            if self._closed:
                raise RuntimeError("Queue is closed")
            self._input_finished = True
            self._condition.notify()

    @property
    def finished(self):
        """True after input is finished and every line has been retrieved.

        Retrieval does not acknowledge successful application processing.
        """
        self._check()
        return self._finished.is_set()

    @property
    def stats(self):
        """A snapshot for monitoring, not a promise about later operations."""
        with self._condition:
            return {"ready": len(self._ready),
                    "pending_write": len(self._pending),
                    "write_in_flight": self._write_in_flight,
                    "disk_pending": self._disk_pending,
                    "spilled_total": self._spilled_total}

    def _read_batch(self, spool, index, read_offset, read_index, count):
        """Read original bytes; helper locals do not linger in the worker."""
        index.seek(read_index)
        metadata = index.read(count * self._LENGTH.size)
        if len(metadata) != count * self._LENGTH.size:
            raise OSError("Incomplete spool length index")
        spool.seek(read_offset)
        loaded = []
        for (length,) in self._LENGTH.iter_unpack(metadata):
            line = spool.read(length)
            if len(line) != length:
                raise OSError("Incomplete spool line")
            loaded.append(line)
        return loaded, spool.tell(), index.tell()

    def _write_batch(self, spool, index, write_offset, write_index, batch):
        """Write raw lines and length metadata, flushing both file buffers."""
        spool.seek(write_offset)
        spool.writelines(batch)
        spool.flush()
        index.seek(write_index)
        index.write(b"".join(self._LENGTH.pack(len(line)) for line in batch))
        index.flush()
        return spool.tell(), index.tell()

    def _run(self):
        created = []
        read_offset = write_offset = read_index = write_index = 0
        refilling = False
        try:
            with self._path.open("x+b", buffering=256 * 1024) as spool:
                created.append(self._path)
                with self._index_path.open("x+b", buffering=64 * 1024) as index:
                    created.append(self._index_path)
                    self._started.set()

                    while True:
                        batch = []
                        with self._condition:
                            if self._closed:
                                return
                            if (self._input_finished and not self._ready
                                    and not self._pending and not self._disk_pending
                                    and not self._write_in_flight):
                                self._finished.set()
                                return

                            if len(self._ready) < self._refill_at:
                                refilling = True
                            if len(self._ready) >= self._ram_limit:
                                refilling = False

                            read_count = 0
                            if refilling and self._disk_pending:
                                read_count = min(
                                    self._batch_size, self._disk_pending,
                                    self._ram_limit - len(self._ready))
                            elif self._pending:
                                batch = [self._pending.popleft() for _ in range(
                                    min(self._batch_size, len(self._pending)))]
                                # If older pending lines have not reached disk
                                # yet, move them directly into newly freed RAM.
                                if self._disk_pending == 0:
                                    direct = min(len(batch),
                                                 self._ram_limit - len(self._ready))
                                    self._ready.extend(batch[:direct])
                                    del batch[:direct]
                                self._write_in_flight = len(batch)
                            else:
                                self._condition.wait()
                                continue

                        # File operations are outside the shared lock.
                        if read_count:
                            loaded, read_offset, read_index = self._read_batch(
                                spool, index, read_offset, read_index, read_count)
                            with self._condition:
                                self._ready.extend(loaded)
                                self._disk_pending -= read_count
                                empty_disk = self._disk_pending == 0
                            loaded.clear()
                            if empty_disk:
                                # Disk space is reclaimed when backlog empties.
                                spool.seek(0)
                                spool.truncate()
                                index.seek(0)
                                index.truncate()
                                read_offset = write_offset = read_index = write_index = 0
                        elif batch:
                            count = len(batch)
                            write_offset, write_index = self._write_batch(
                                spool, index, write_offset, write_index, batch)
                            # Drop payload references immediately after flush.
                            # The worker's idle frame retains only an empty list.
                            batch.clear()
                            with self._condition:
                                self._disk_pending += count
                                self._spilled_total += count
                                self._write_in_flight = 0
        except Exception as exc:
            self._error = exc
            self._failed.set()
        finally:
            # Keep files after a worker failure for inspection. They are not
            # automatically replayable because some work may still be in RAM.
            if not self._failed.is_set():
                try:
                    for path in reversed(created):
                        path.unlink()
                except OSError as exc:
                    self._error = exc
                    self._failed.set()
            self._started.set()

    def close(self):
        """Stop the worker and discard outstanding work. Waits for file I/O."""
        with self._condition:
            self._closed = True
            self._condition.notify()
        self._thread.join()
        with self._condition:
            self._ready.clear()
            self._pending.clear()
        self._check()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


if __name__ == "__main__":
    import argparse
    import tempfile
    import time

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Log file; read as original bytes")
    parser.add_argument("--spool-directory", required=True,
                        help="An existing directory on a real disk")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(dir=args.spool_directory) as directory:
        with DiskBackedQueue(Path(directory) / "overflow.log") as work:
            producer_errors = []

            def read_logs():
                try:
                    with open(args.input, "rb") as source:
                        for line in source:
                            work.add_line(line)
                    work.finish_input()
                except Exception as exc:
                    producer_errors.append(exc)
                    try:
                        work.finish_input()
                    except RuntimeError:
                        pass

            reader = Thread(target=read_logs, daemon=True)
            reader.start()
            count = 0
            try:
                while not work.finished:
                    line = work.get_line()
                    if line is None:
                        # Replace this with useful unrelated application work.
                        time.sleep(0.001)
                        continue
                    # Your processing function receives the original bytes.
                    count += 1
                reader.join()
                if producer_errors:
                    raise producer_errors[0]
                print(f"Processed {count} lines; stats: {work.stats}")
            finally:
                # Close first so a still-active reader stops submitting.
                work.close()
                reader.join()
