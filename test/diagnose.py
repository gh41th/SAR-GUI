"""
tests/thread_test.py
Tests Qt threading using the QThread subclass pattern.
This is more reliable on Windows than the worker+moveToThread pattern.

The key difference:
  OLD: QObject worker → moveToThread(QThread)   ← fragile on Windows
  NEW: subclass QThread, override run()          ← simple and reliable

Run with:
    python tests/thread_test.py
"""

import sys
import time
import traceback

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QPushButton, QLabel,
    QProgressBar, QTextEdit
)
from PyQt5.QtCore import QThread, pyqtSignal


# ══════════════════════════════════════════════════════════════════════
# WORKERS — now subclasses of QThread directly
# Override run() with your slow code. Emit signals to talk to the GUI.
# ══════════════════════════════════════════════════════════════════════

class ThreadA(QThread):
    """Test 1 — simplest possible: sleep 2s, emit a string."""
    result = pyqtSignal(str)

    def run(self):
        print("[ThreadA] run() started", flush=True)
        time.sleep(2)
        print("[ThreadA] emitting result", flush=True)
        self.result.emit("ThreadA done after 2 seconds!")


class ThreadB(QThread):
    """Test 2 — emits progress 0→100 over 3 seconds."""
    result   = pyqtSignal(str)
    progress = pyqtSignal(int)

    def run(self):
        print("[ThreadB] run() started", flush=True)
        for i in range(101):
            time.sleep(0.03)
            self.progress.emit(i)
        self.result.emit("ThreadB done — progress works!")


class ThreadC(QThread):
    """Test 3 — crashes intentionally, error sent via signal."""
    result = pyqtSignal(str)
    error  = pyqtSignal(str)

    def run(self):
        print("[ThreadC] run() started, about to crash...", flush=True)
        try:
            raise ValueError("Deliberate test crash!")
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


class ThreadD(QThread):
    """Test 4 — returns a numpy array. Simulates the SAR loader."""
    result   = pyqtSignal(object)   # object = any Python type, inc. ndarray
    progress = pyqtSignal(int)
    error    = pyqtSignal(str)

    def run(self):
        print("[ThreadD] run() started", flush=True)
        try:
            import numpy as np
            self.progress.emit(10)
            time.sleep(1)
            self.progress.emit(50)
            fake = np.random.randint(0, 255, (512, 512), dtype=np.uint8)
            time.sleep(1)
            self.progress.emit(100)
            print(f"[ThreadD] emitting array shape={fake.shape}", flush=True)
            self.result.emit(fake)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ══════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════

class TestWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt Thread Tester")
        self.setMinimumSize(600, 550)
        self._threads = []
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setSpacing(10)
        self.setCentralWidget(root)

        # Click counter — proves GUI stays responsive while threads run
        self.click_counter = 0
        self.click_btn = QPushButton("Click me while tests run (counts clicks)")
        self.click_btn.clicked.connect(self._on_click)
        layout.addWidget(self.click_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        for label, slot in [
            ("Test 1 — Basic thread (2s sleep)", self._test1),
            ("Test 2 — Progress bar (3s count)",  self._test2),
            ("Test 3 — Error handling",            self._test3),
            ("Test 4 — Returns numpy array",       self._test4),
        ]:
            layout.addWidget(QLabel(f"<b>{label}</b>"))
            btn = QPushButton(f"▶ Run {label.split('—')[0].strip()}")
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    def _log(self, msg, color="black"):
        self.log.append(f'<span style="color:{color}">{msg}</span>')
        print(msg, flush=True)

    def _on_click(self):
        self.click_counter += 1
        self.click_btn.setText(f"Click me while tests run (clicks: {self.click_counter})")

    # ── Tests ──────────────────────────────────────────────────────

    def _test1(self):
        self._log("Test 1 started — GUI should stay alive for 2s...")
        t = ThreadA()
        t.result.connect(lambda msg: self._log(f"✅ {msg}", "green"))
        t.start()
        self._threads.append(t)

    def _test2(self):
        self._log("Test 2 started — watch progress bar...")
        self.progress.setValue(0)
        t = ThreadB()
        t.progress.connect(self.progress.setValue)
        t.result.connect(lambda msg: self._log(f"✅ {msg}", "green"))
        t.start()
        self._threads.append(t)

    def _test3(self):
        self._log("Test 3 started — expecting an error...")
        t = ThreadC()
        t.result.connect(lambda msg: self._log(f"✅ {msg}", "green"))
        t.error.connect(lambda msg: self._log(f"✅ Caught error: {msg}", "orange"))
        t.start()
        self._threads.append(t)

    def _test4(self):
        self._log("Test 4 started — simulating SAR loader...")
        self.progress.setValue(0)
        t = ThreadD()
        t.progress.connect(self.progress.setValue)
        t.result.connect(self._on_test4_done)
        t.error.connect(lambda msg: self._log(f"❌ {msg}", "red"))
        t.start()
        self._threads.append(t)

    def _on_test4_done(self, array):
        self._log(
            f"✅ Test 4: got array shape={array.shape} "
            f"dtype={array.dtype} mean={array.mean():.1f}",
            "green"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = TestWindow()
    win.show()
    sys.exit(app.exec_())
"""
tests/thread_test.py
A standalone GUI that tests Qt threading step by step.
No SAR data needed — just run it and click the buttons in order.

Run with:
    python tests/thread_test.py
"""

import sys
import time
import traceback

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QPushButton, QLabel,
    QProgressBar, QTextEdit
)
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtGui import QColor


# ══════════════════════════════════════════════════════════════════════
# WORKERS
# Each one tests a different aspect of threading.
# ══════════════════════════════════════════════════════════════════════

class WorkerA(QObject):
    """
    TEST 1 — Simplest possible worker.
    Just sleeps 2 seconds and emits a string result.
    If this works, basic threading is fine.
    """
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def run(self):
        print("[WorkerA] run() started", flush=True)
        time.sleep(2)
        print("[WorkerA] about to emit finished", flush=True)
        self.finished.emit("WorkerA done after 2 seconds!")
        print("[WorkerA] finished emitted", flush=True)


class WorkerB(QObject):
    """
    TEST 2 — Worker with progress updates.
    Counts from 0 to 100 over 3 seconds, emitting progress each step.
    If this works, progress bars will work.
    """
    finished = pyqtSignal(str)
    progress = pyqtSignal(int)
    error    = pyqtSignal(str)

    def run(self):
        print("[WorkerB] run() started", flush=True)
        for i in range(101):
            time.sleep(0.03)            # 3 seconds total
            self.progress.emit(i)
        self.finished.emit("WorkerB done — progress works!")
        print("[WorkerB] finished emitted", flush=True)


class WorkerC(QObject):
    """
    TEST 3 — Worker that intentionally crashes.
    Verifies that errors are caught and sent to the main thread safely.
    """
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def run(self):
        print("[WorkerC] run() started, about to crash...", flush=True)
        try:
            raise ValueError("This is a deliberate test crash!")
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


class WorkerD(QObject):
    """
    TEST 4 — Worker that returns a large numpy array.
    Simulates the SAR overview loader.
    If this works, our actual data pipeline will work.
    """
    finished = pyqtSignal(object)   # 'object' = any Python type, including ndarray
    progress = pyqtSignal(int)
    error    = pyqtSignal(str)

    def run(self):
        print("[WorkerD] run() started", flush=True)
        try:
            import numpy as np
            self.progress.emit(10)
            time.sleep(1)

            # Simulate building an overview image
            self.progress.emit(50)
            fake_image = np.random.randint(0, 255, (512, 512), dtype=np.uint8)
            time.sleep(1)

            self.progress.emit(100)
            self.finished.emit(fake_image)
            print(f"[WorkerD] emitted array shape={fake_image.shape}", flush=True)

        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ══════════════════════════════════════════════════════════════════════
# HELPER — reusable thread launcher (same as in our app)
# ══════════════════════════════════════════════════════════════════════

def launch_worker(worker, on_finished, on_error=None, on_progress=None):
    """
    Connect signals, move worker to thread, start.
    Returns the thread (caller must keep a reference).
    """
    thread = QThread()

    # ── Connect ALL signals before moveToThread ────────────────────
    worker.finished.connect(on_finished)
    worker.finished.connect(lambda _=None: thread.quit())

    if on_error and hasattr(worker, "error"):
        worker.error.connect(on_error)
        worker.error.connect(lambda _=None: thread.quit())

    if on_progress and hasattr(worker, "progress"):
        worker.progress.connect(on_progress)

    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    # ── Move and start ────────────────────────────────────────────
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    thread.start()

    print(f"[launcher] thread started for {worker.__class__.__name__}", flush=True)
    return thread


# ══════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════

class TestWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt Thread Tester")
        self.setMinimumSize(600, 550)
        self._threads = []   # keep references so GC doesn't kill them

        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setSpacing(10)
        self.setCentralWidget(root)

        def section(title):
            lbl = QLabel(f"<b>{title}</b>")
            layout.addWidget(lbl)

        # ── Status indicator (turns green when GUI stays responsive) ──
        self.ping_label = QLabel("⬤ GUI responsive")
        self.ping_label.setStyleSheet("color: green; font-size: 14px;")
        layout.addWidget(self.ping_label)

        # A counter that increments every time you click it.
        # If the GUI is frozen, this button won't respond while a test runs.
        self.click_counter = 0
        self.click_btn = QPushButton("Click me while tests run (counts clicks)")
        self.click_btn.clicked.connect(self._on_click)
        layout.addWidget(self.click_btn)

        # ── Progress bar (shared) ──────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        # ── Test buttons ───────────────────────────────────────────
        section("Test 1 — Basic thread (2s sleep, no progress)")
        btn1 = QPushButton("▶ Run Test 1")
        btn1.clicked.connect(self._test1)
        layout.addWidget(btn1)

        section("Test 2 — Thread with progress bar (3s count)")
        btn2 = QPushButton("▶ Run Test 2")
        btn2.clicked.connect(self._test2)
        layout.addWidget(btn2)

        section("Test 3 — Thread that crashes (error handling)")
        btn3 = QPushButton("▶ Run Test 3")
        btn3.clicked.connect(self._test3)
        layout.addWidget(btn3)

        section("Test 4 — Thread returns numpy array (simulates SAR loader)")
        btn4 = QPushButton("▶ Run Test 4")
        btn4.clicked.connect(self._test4)
        layout.addWidget(btn4)

        # ── Log output ─────────────────────────────────────────────
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(140)
        layout.addWidget(self.log)

    # ── Helpers ────────────────────────────────────────────────────

    def _log(self, msg, color="black"):
        self.log.append(f'<span style="color:{color}">{msg}</span>')
        print(msg, flush=True)

    def _on_click(self):
        self.click_counter += 1
        self.click_btn.setText(
            f"Click me while tests run (clicks: {self.click_counter})"
        )

    def _on_error(self, msg):
        self._log(f"❌ ERROR:\n{msg}", color="red")

    # ── Test 1 ─────────────────────────────────────────────────────

    def _test1(self):
        self._log("Test 1 started — GUI should stay responsive for 2s...")
        worker = WorkerA()
        t = launch_worker(
            worker,
            on_finished=lambda msg: self._log(f"✅ Test 1: {msg}", "green"),
            on_error=self._on_error,
        )
        self._threads.append(t)

    # ── Test 2 ─────────────────────────────────────────────────────

    def _test2(self):
        self._log("Test 2 started — watch the progress bar for 3s...")
        self.progress.setValue(0)
        worker = WorkerB()
        t = launch_worker(
            worker,
            on_finished=lambda msg: self._log(f"✅ Test 2: {msg}", "green"),
            on_error=self._on_error,
            on_progress=self.progress.setValue,
        )
        self._threads.append(t)

    # ── Test 3 ─────────────────────────────────────────────────────

    def _test3(self):
        self._log("Test 3 started — should show an error message...")
        worker = WorkerC()
        t = launch_worker(
            worker,
            on_finished=lambda msg: self._log(f"✅ Test 3: {msg}", "green"),
            on_error=lambda msg: self._log(f"✅ Test 3 caught error correctly:\n{msg}", "orange"),
        )
        self._threads.append(t)

    # ── Test 4 ─────────────────────────────────────────────────────

    def _test4(self):
        self._log("Test 4 started — simulates SAR loader returning numpy array...")
        self.progress.setValue(0)
        worker = WorkerD()
        t = launch_worker(
            worker,
            on_finished=self._on_test4_done,
            on_error=self._on_error,
            on_progress=self.progress.setValue,
        )
        self._threads.append(t)

    def _on_test4_done(self, array):
        import numpy as np
        self._log(
            f"✅ Test 4: received array shape={array.shape} "
            f"dtype={array.dtype} mean={array.mean():.1f}",
            "green"
        )


# ══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = TestWindow()
    win.show()
    sys.exit(app.exec_())