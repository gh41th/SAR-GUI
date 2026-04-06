"""
tests/generate_test_data.py
Creates TWO minimal but structurally valid NISAR-like HDF5 files:
  - fake_nisar_slc.h5   (SLC, swaths, complex64)
  - fake_nisar_gcov.h5  (GCOV, grids, float32 + geo coords)

Both mirror the exact paths and dataset names from real NISAR files.

Run with:
    python tests/generate_test_data.py
"""

import h5py
import numpy as np
import os

OUT_DIR     = os.path.dirname(__file__)
SLC_PATH    = os.path.join(OUT_DIR, "fake_nisar_slc.h5")
GCOV_PATH   = os.path.join(OUT_DIR, "fake_nisar_gcov.h5")
ROWS, COLS  = 512, 512


# ── Fake SLC ───────────────────────────────────────────────────────────────────

def make_fake_slc_array() -> np.ndarray:
    rng = np.random.default_rng(42)
    amplitude = rng.rayleigh(scale=0.3, size=(ROWS, COLS)).astype(np.float32)
    for r, c in [(100, 100), (200, 350), (400, 150), (450, 450)]:
        amplitude[r-3:r+3, c-3:c+3] += 5.0
    amplitude[300:420, 200:380] *= 0.05   # dark water-like region
    phase = rng.uniform(0, 2 * np.pi, size=(ROWS, COLS)).astype(np.float32)
    return (amplitude * np.exp(1j * phase)).astype(np.complex64)


def create_fake_slc(path: str):
    print(f"\nCreating fake SLC: {path}")
    with h5py.File(path, "w") as f:
        ident = f.create_group("science/LSAR/identification")
        ident.create_dataset("zeroDopplerStartTime", data=np.bytes_("2024-01-15T10:30:00.000000000"))
        ident.create_dataset("orbitPassDirection",   data=np.bytes_("ascending"))

        freq = f.create_group("science/LSAR/SLC/swaths/frequencyA")
        slc  = make_fake_slc_array()
        for pol in ["HH", "HV", "VH", "VV"]:
            freq.create_dataset(pol, data=slc, chunks=(64, 64),
                                compression="gzip", compression_opts=1)

        params = f.create_group("science/LSAR/SLC/metadata/processingInformation/parameters")
        params.create_dataset("effectiveRadarWavelength", data=np.float64(0.238))

    print(f"  /science/LSAR/SLC/swaths/frequencyA/HH|HV|VH|VV  shape=({ROWS},{COLS}) complex64")


# ── Fake GCOV ──────────────────────────────────────────────────────────────────

def make_fake_gcov_array() -> np.ndarray:
    """Power image (float32, always >= 0, with NaN nodata border)."""
    rng = np.random.default_rng(7)
    data = rng.rayleigh(scale=0.1, size=(ROWS, COLS)).astype(np.float32) ** 2
    data[300:420, 200:380] *= 0.01   # dark region
    for r, c in [(80, 80), (250, 400), (420, 100)]:
        data[r-2:r+2, c-2:c+2] = 1.5
    # NaN border — common in real GCOV files
    data[:10, :] = np.nan
    data[-10:, :] = np.nan
    return data


def create_fake_gcov(path: str):
    print(f"\nCreating fake GCOV: {path}")

    # Fake UTM coordinates (zone 11N, EPSG:32611)
    x0, y0 = 500_000.0, 4_000_000.0
    dx, dy = 20.0, -20.0   # 20 m GCOV resolution, dy negative (north-up)
    x_coords = x0 + np.arange(COLS) * dx
    y_coords = y0 + np.arange(ROWS) * dy   # decreasing (top row = highest y)

    with h5py.File(path, "w") as f:
        ident = f.create_group("science/LSAR/identification")
        ident.create_dataset("zeroDopplerStartTime", data=np.bytes_("2024-01-15T10:30:00.000000000"))
        ident.create_dataset("orbitPassDirection",   data=np.bytes_("ascending"))

        freq = f.create_group("science/LSAR/GCOV/grids/frequencyA")

        # Covariance elements — same structure as your notebook
        gcov = make_fake_gcov_array()
        for pol in ["HHHH", "HVHV", "VVVV", "HHHV", "HHVV", "HVVV"]:
            freq.create_dataset(pol, data=gcov * (0.8 + 0.4 * np.random.rand()),
                                chunks=(64, 64), compression="gzip", compression_opts=1)

        # Geo datasets — exact same names as your real files
        freq.create_dataset("xCoordinates",     data=x_coords.astype(np.float64))
        freq.create_dataset("yCoordinates",     data=y_coords.astype(np.float64))
        freq.create_dataset("xCoordinateSpacing", data=np.float64(dx))
        freq.create_dataset("yCoordinateSpacing", data=np.float64(dy))
        freq.create_dataset("projection",        data=np.int32(32611))

        params = f.create_group("science/LSAR/GCOV/metadata/processingInformation/parameters")
        params.create_dataset("effectiveRadarWavelength", data=np.float64(0.238))

    print(f"  /science/LSAR/GCOV/grids/frequencyA/HHHH|HVHV|VVVV...  shape=({ROWS},{COLS}) float32")
    print(f"  xCoordinates, yCoordinates, projection (EPSG:32611)")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    create_fake_slc(SLC_PATH)
    create_fake_gcov(GCOV_PATH)
    print(f"\nDone. Test files are in: {OUT_DIR}")
    print("Open them in the app via File → Open")