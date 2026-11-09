"""One explicit fake streaming call through Core HTTP/SQLite; never a real model."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts import u108_work_events_host as host
from tests.test_core_work_events import WorkEventsTests, RealClient
from ai_union.work_transport import ModeldWorkTransport


class PageCancellationFixture(WorkEventsTests):
    def setUp(self):
        super().setUp()
        # Browser fault scenarios need bounded time; product deadlines are untouched.
        self.app.work.transport_factory = lambda au, connection: ModeldWorkTransport(
            RealClient(str(self.config)), au, connection, poll_seconds=.1, timeout_seconds=60)


host.WorkEventsTests = PageCancellationFixture
if __name__ == "__main__":
    host.main()
