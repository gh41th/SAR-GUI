"""
data/worker.py — Background threads for file I/O and processing.

Uses the QThread subclass pattern — reliable on Windows with PyQt5.

Pattern:
    class MyThread(QThread):
        result = pyqtSignal(object)

        def run(self):               ← runs on background thread
            data = do_slow_work()
            self.result.emit(data)   ← safely delivered to main thread

Usage:
    t = FileLoaderThread(path)
    t.result.connect(self._on_loaded)
    t.error.connect(self._on_error)
    t.start()
    self._threads.append(t)   ← keep reference or GC kills it mid-run
"""

import traceback
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from data.io import read_nisar_metadata, load_overview, load_region, amplitude_to_uint8


class FileLoaderThread(QThread):
    """Reads NISAR file metadata in the background."""
    result = pyqtSignal(object)   # emits NISARFileInfo
    error  = pyqtSignal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        print(f"[FileLoaderThread] reading: {self.file_path}", flush=True)
        try:
            info = read_nisar_metadata(self.file_path)
            print(f"[FileLoaderThread] done — {info.product_type} "
                  f"{[p.name for p in info.polarizations]}", flush=True)
            self.result.emit(info)
        except Exception as e:
            print(f"[FileLoaderThread] ERROR: {e}", flush=True)
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")


class OverviewLoaderThread(QThread):
    """
    Loads a downsampled overview of the full scene.
    First call reads HDF5 (~5s) and caches a .npy file.
    Subsequent calls load from cache (~0.05s).
    """
    result   = pyqtSignal(np.ndarray)
    progress = pyqtSignal(int)
    error    = pyqtSignal(str)

    def __init__(self, file_path: str, h5_path: str, dataset_name: str):
        super().__init__()
        self.file_path    = file_path
        self.h5_path      = h5_path
        self.dataset_name = dataset_name

    def run(self):
        print(f"[OverviewLoaderThread] loading {self.dataset_name}", flush=True)
        try:
            overview = load_overview(
                file_path=self.file_path,
                h5_path=self.h5_path,
                dataset_name=self.dataset_name,
                target_size=4096,
                progress_cb=lambda v: self.progress.emit(v),
            )
            print(f"[OverviewLoaderThread] shape={overview.shape}", flush=True)
            display = amplitude_to_uint8(overview)
            self.result.emit(display)
        except Exception as e:
            print(f"[OverviewLoaderThread] ERROR: {e}", flush=True)
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")


class RegionLoaderThread(QThread):
    """
    Loads a specific spatial region at a given downsample level.
    Used when the user zooms in past a threshold.

    row/col bounds are in FULL resolution pixel coordinates.
    downsample: 1=full res, 4=quarter res, etc.
    """
    result   = pyqtSignal(np.ndarray, int, int, int, int)  # array, r0, r1, c0, c1
    progress = pyqtSignal(int)
    error    = pyqtSignal(str)

    def __init__(self, file_path: str, h5_path: str,
                 row_start: int, row_end: int,
                 col_start: int, col_end: int,
                 downsample: int = 1):
        super().__init__()
        self.file_path  = file_path
        self.h5_path    = h5_path
        self.row_start  = row_start
        self.row_end    = row_end
        self.col_start  = col_start
        self.col_end    = col_end
        self.downsample = downsample

    def run(self):
        print(f"[RegionLoaderThread] rows={self.row_start}:{self.row_end} "
              f"cols={self.col_start}:{self.col_end} ds={self.downsample}", flush=True)
        try:
            region = load_region(
                file_path=self.file_path,
                h5_path=self.h5_path,
                row_start=self.row_start,
                row_end=self.row_end,
                col_start=self.col_start,
                col_end=self.col_end,
                downsample=self.downsample,
                progress_cb=lambda v: self.progress.emit(v),
            )
            display = amplitude_to_uint8(region)
            print(f"[RegionLoaderThread] done shape={display.shape}", flush=True)
            self.result.emit(display,
                             self.row_start, self.row_end,
                             self.col_start, self.col_end)
        except Exception as e:
            print(f"[RegionLoaderThread] ERROR: {e}", flush=True)
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")
