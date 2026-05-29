"""MediaPush entry point."""
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from PyQt5.QtWidgets import QApplication  # noqa: E402

from db.store import Store  # noqa: E402
from account.manager import AccountManager  # noqa: E402
from publisher.queue import PublishQueue  # noqa: E402
from publisher.inbox_watcher import InboxWatcher  # noqa: E402
from publisher.douyin import DouyinPublisher  # noqa: E402
from publisher.xiaohongshu import XiaohongshuPublisher  # noqa: E402
from publisher.kuaishou import KuaishouPublisher  # noqa: E402
from publisher.douyin_message import DouyinMessageReader  # noqa: E402
from publisher.message_scheduler import MessageScheduler  # noqa: E402
from publisher.message_store import MessageStore  # noqa: E402
from mediapush_ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    db_path = os.environ["MEDIAPUSH_DB_PATH"]
    profiles_path = os.environ["MEDIAPUSH_PROFILES_PATH"]

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(profiles_path).mkdir(parents=True, exist_ok=True)

    inbox_path = os.environ.get("MEDIAPUSH_INBOX_PATH", str(Path(db_path).parent.parent / "inbox"))
    processed_path = os.environ.get(
        "MEDIAPUSH_INBOX_PROCESSED_PATH",
        str(Path(inbox_path) / "processed"),
    )
    poll_sec = float(os.environ.get("MEDIAPUSH_INBOX_POLL_SECONDS", "5"))
    Path(inbox_path).mkdir(parents=True, exist_ok=True)
    Path(processed_path).mkdir(parents=True, exist_ok=True)

    store = Store(db_path)
    if os.environ.get("MEDIAPUSH_AUTO_PURGE_HISTORY", "1") != "0":
        store.purge_submitted_history_before(date.today().isoformat())
    publishers = {
        "douyin": DouyinPublisher(),
        "xiaohongshu": XiaohongshuPublisher(),
        "kuaishou": KuaishouPublisher(),
    }
    account_mgr = AccountManager(store, profiles_path, publishers=publishers)
    queue = PublishQueue(store, publishers=publishers)
    queue.start()
    watcher = InboxWatcher(store, queue, inbox_path, processed_path, poll_sec=poll_sec)
    watcher.start()
    msg_store = MessageStore(Path(db_path).parent / "message_seen.json")
    message_readers = {"douyin": DouyinMessageReader()}
    message_scheduler = MessageScheduler(store, msg_store, message_readers)
    message_scheduler.start()

    app = QApplication(sys.argv)
    win = MainWindow(
        account_mgr=account_mgr,
        queue=queue,
        store=store,
        msg_store=msg_store,
        scheduler=message_scheduler,
        message_readers=message_readers,
    )
    win.show()
    try:
        return app.exec()
    finally:
        message_scheduler.stop()
        message_scheduler.wait(3000)
        watcher.stop()
        watcher.wait(2000)
        queue.stop()
        queue.wait(2000)
        store.close()


if __name__ == "__main__":
    sys.exit(main())
