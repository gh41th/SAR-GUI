"""
data/io.py — HDF5 file reading for NISAR data.

NISAR HDF5 STRUCTURE (from real files):
  SLC:
    /science/LSAR/SLC/swaths/frequencyA/
      HH, HV, VH, VV          ← complex64 arrays

  GCOV:
    /science/LSAR/GCOV/grids/frequencyA/
      HHHH, HVHV, VVVV ...    ← float32 covariance elements
      xCoordinates            ← 1D array of x positions
      yCoordinates            ← 1D array of y positions
      xCoordinateSpacing      ← scalar
      yCoordinateSpacing      ← scalar
      projection              ← EPSG code (int)

OVERVIEW CACHING:
  First load of any dataset is slow (~3s) due to gzip decompression.
  We save a tiny .npy overview file next to the .h5 on first load.
  Subsequent loads are instant (~0.05s).
  Cache file: <original_name>.<dataset>.overview.npy
"""

import os
import h5py
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class GeoInfo:
    epsg: int
    x_coords: np.ndarray
    y_coords: np.ndarray
    dx: float
    dy: float

    @property
    def x_min(self): return float(self.x_coords.min())
    @property
    def x_max(self): return float(self.x_coords.max())
    @property
    def y_min(self): return float(self.y_coords.min())
    @property
    def y_max(self): return float(self.y_coords.max())

    @property
    def crs_string(self) -> str:
        return f"EPSG:{self.epsg}"

    def rasterio_profile(self, n_rows: int, n_cols: int, n_bands: int = 1) -> dict:
        from rasterio.transform import from_origin
        transform = from_origin(
            self.x_min - self.dx / 2,
            self.y_max - self.dy / 2,
            self.dx,
            -self.dy
        )
        return {
            "driver": "GTiff", "height": n_rows, "width": n_cols,
            "count": n_bands, "dtype": "float32", "crs": self.crs_string,
            "transform": transform, "compress": "deflate", "tiled": True,
            "blockxsize": 512, "blockysize": 512,
            "BIGTIFF": "YES", "nodata": float("nan"),
        }


@dataclass
class PolarizationInfo:
    name: str
    shape: tuple
    dtype: str
    h5_path: str


@dataclass
class NISARFileInfo:
    file_path: str
    product_type: str
    band: str
    frequency: str
    polarizations: list[PolarizationInfo] = field(default_factory=list)
    orbit_direction: str = "unknown"
    start_time: str = "unknown"
    radar_wavelength: Optional[float] = None
    geo: Optional[GeoInfo] = None

    @property
    def display_name(self) -> str:
        return os.path.basename(self.file_path)

    @property
    def is_geocoded(self) -> bool:
        return self.product_type in ("GCOV", "GSLC", "GUNW", "RIFG", "ROFF", "RUNW")


# ── Overview cache ─────────────────────────────────────────────────────────────

def _cache_path(file_path: str, dataset_name: str) -> str:
    """
    Returns the path for the cached overview .npy file.
    Stored alongside the .h5 file.
    Example: /data/scene.h5  →  /data/scene.HHHH.overview.npy
    """
    base = os.path.splitext(file_path)[0]
    return f"{base}.{dataset_name}.overview.npy"


def has_cached_overview(file_path: str, dataset_name: str) -> bool:
    return os.path.exists(_cache_path(file_path, dataset_name))


def load_cached_overview(file_path: str, dataset_name: str) -> Optional[np.ndarray]:
    path = _cache_path(file_path, dataset_name)
    if os.path.exists(path):
        return np.load(path)
    return None


def save_cached_overview(file_path: str, dataset_name: str, array: np.ndarray):
    path = _cache_path(file_path, dataset_name)
    np.save(path, array)


# ── Metadata reader ────────────────────────────────────────────────────────────

def read_nisar_metadata(file_path: str) -> NISARFileInfo:
    """
    Open a NISAR HDF5 file and read only its metadata.
    No pixel arrays are loaded.
    """
    # Datasets to skip — they live in the same group as images but aren't images
    NON_IMAGE = {
        "xCoordinates", "yCoordinates", "xCoordinateSpacing",
        "yCoordinateSpacing", "projection", "validSamplesSubSwath1",
        "listOfCovarianceTerms", "listOfPolarizations",
        "numberOfSubSwaths", "mask", "numberOfLooks",
        "rtcGammaToSigmaFactor",
    }

    with h5py.File(file_path, "r") as f:

        science = f.get("science")
        if science is None:
            raise ValueError("Not a valid NISAR file: missing /science group")

        band = next((b for b in ["LSAR", "SSAR"] if b in science), None)
        if band is None:
            raise ValueError("Could not find LSAR or SSAR group")

        band_group = science[band]
        product_type = next(
            (p for p in ["SLC", "GCOV", "GSLC", "GUNW", "RIFG", "ROFF", "RUNW"]
             if p in band_group), None
        )
        if product_type is None:
            raise ValueError(f"Unknown product type in /{band}")

        container = "swaths" if product_type == "SLC" else "grids"
        data_group = band_group[product_type].get(container)
        if data_group is None:
            raise ValueError(f"Missing /{container} in {product_type}")

        frequency = next(
            (f_ for f_ in ["frequencyA", "frequencyB"] if f_ in data_group), None
        )
        if frequency is None:
            raise ValueError("No frequencyA/B found")

        freq_group = data_group[frequency]

        # Collect image polarization datasets only
        pols = []
        for key in sorted(freq_group.keys()):
            if key in NON_IMAGE:
                continue
            item = freq_group[key]
            if isinstance(item, h5py.Dataset) and item.ndim == 2:
                pols.append(PolarizationInfo(
                    name=key, shape=item.shape,
                    dtype=str(item.dtype), h5_path=item.name
                ))

        # Geo info (geocoded products only)
        geo = None
        if product_type != "SLC":
            try:
                geo = GeoInfo(
                    epsg=int(freq_group["projection"][()]),
                    x_coords=freq_group["xCoordinates"][:],
                    y_coords=freq_group["yCoordinates"][:],
                    dx=float(freq_group["xCoordinateSpacing"][()]),
                    dy=float(freq_group["yCoordinateSpacing"][()]),
                )
            except KeyError as e:
                print(f"Warning: geo info missing: {e}")

        # Global metadata
        def _read(path, decode=True):
            try:
                v = f[path][()]
                return v.decode("utf-8") if decode else float(v)
            except Exception:
                return "unknown" if decode else None

        return NISARFileInfo(
            file_path=file_path,
            product_type=product_type,
            band=band,
            frequency=frequency.replace("frequency", ""),
            polarizations=pols,
            orbit_direction=_read(f"science/{band}/identification/orbitPassDirection"),
            start_time=_read(f"science/{band}/identification/zeroDopplerStartTime"),
            radar_wavelength=_read(
                f"science/{band}/{product_type}/metadata/"
                f"processingInformation/parameters/effectiveRadarWavelength",
                decode=False
            ),
            geo=geo,
        )


# ── Overview loader (the core function the worker calls) ──────────────────────

def load_overview(
    file_path: str,
    h5_path: str,
    dataset_name: str,
    target_size: int = 4096,
    progress_cb=None,
) -> np.ndarray:
    """
    Load a downsampled overview of a SAR dataset, using cache when available.

    On first call: reads full file with chunk-aligned strips (~3s), saves cache.
    On subsequent calls: loads .npy cache file (~0.05s).

    Args:
        file_path    : path to .h5 file
        h5_path      : dataset path inside HDF5
        dataset_name : short name for cache file (e.g. "HHHH")
        target_size  : overview pixel size in each dimension
        progress_cb  : optional callable(int 0-100) for progress updates

    Returns:
        2D float32 amplitude array, ready for amplitude_to_uint8()
    """
    def _progress(v):
        if progress_cb:
            progress_cb(v)

    # ── Try cache first ────────────────────────────────────────────────
    cached = load_cached_overview(file_path, dataset_name)
    if cached is not None:
        _progress(100)
        return cached

    # ── Cache miss — read from HDF5 ────────────────────────────────────
    _progress(5)

    with h5py.File(file_path, "r") as f:
        ds = f[h5_path]
        rows, cols = ds.shape[0], ds.shape[1]

        # Get chunk size — default to 512 if not chunked
        chunk_h = ds.chunks[0] if ds.chunks else 512

        col_step = max(1, cols // target_size)
        row_step = max(1, rows // target_size)

        strips = []
        n_strips = (rows + chunk_h - 1) // chunk_h   # ceil division

        for i, r in enumerate(range(0, rows, chunk_h)):
            r_end = min(r + chunk_h, rows)

            # Read full-width strip — perfectly contiguous, no striding in HDF5
            strip = ds[r:r_end, :]

            # Convert complex to amplitude if SLC
            if np.iscomplexobj(strip):
                strip = np.abs(strip)

            strip = strip.astype(np.float32)

            # Downsample in numpy — free operation, no HDF5 involved
            strip_down = strip[::row_step, ::col_step]
            strips.append(strip_down)

            _progress(5 + int(90 * (i + 1) / n_strips))

    overview = np.vstack(strips)
    _progress(97)

    # ── Save cache ─────────────────────────────────────────────────────
    save_cached_overview(file_path, dataset_name, overview)
    _progress(100)

    return overview


# ── Display scaling ────────────────────────────────────────────────────────────

def amplitude_to_uint8(amplitude: np.ndarray, percentile_clip: float = 2.0) -> np.ndarray:
    """Scale float32 amplitude to uint8 for display, handling NaNs."""
    clean = np.where(np.isfinite(amplitude), amplitude, np.nan)
    lo = np.nanpercentile(clean, percentile_clip)
    hi = np.nanpercentile(clean, 100 - percentile_clip)
    clipped = np.clip(clean, lo, hi)
    norm = (clipped - lo) / max(hi - lo, 1e-9)
    return (np.nan_to_num(norm, nan=0.0) * 255).astype(np.uint8)


# ── Tile loader (for full-res zoom-in, used later) ────────────────────────────

def load_region(
    file_path: str,
    h5_path: str,
    row_start: int, row_end: int,
    col_start: int, col_end: int,
    downsample: int = 1,
    progress_cb=None,
) -> np.ndarray:
    """
    Load a specific region of a dataset at a given downsample level.
    Used for zoom-in tile loading.

    Args:
        row/col start/end : pixel bounds in the FULL resolution image
        downsample        : 1=full res, 2=half res, 4=quarter res
        progress_cb       : optional callable(int 0-100)

    Returns:
        2D float32 amplitude array
    """
    def _p(v):
        if progress_cb: progress_cb(v)

    _p(10)
    with h5py.File(file_path, "r") as f:
        ds = f[h5_path]
        rows, cols = ds.shape[0], ds.shape[1]

        # Clamp bounds to valid range
        r0 = max(0, row_start)
        r1 = min(rows, row_end)
        c0 = max(0, col_start)
        c1 = min(cols, col_end)

        _p(20)

        # Read the region in chunk-aligned strips for speed
        chunk_h = ds.chunks[0] if ds.chunks else 512
        strips = []
        n_strips = max(1, (r1 - r0 + chunk_h - 1) // chunk_h)

        for i, r in enumerate(range(r0, r1, chunk_h)):
            re = min(r + chunk_h, r1)
            if re <= r:
                continue
            strip = ds[r:re, c0:c1]
            if strip.size == 0:
                continue
            if np.iscomplexobj(strip):
                strip = np.abs(strip)
            stripped = strip.astype(np.float32)[::downsample, ::downsample]
            if stripped.size > 0:
                strips.append(stripped)
            _p(20 + int(70 * (i + 1) / n_strips))

    if not strips:
        return np.zeros((1, 1), dtype=np.float32)

    result = np.vstack(strips)
    _p(100)
    return result