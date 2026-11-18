"""Public provider download, deterministic parsing, explicit vintage provenance."""
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

SOURCE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_Daily_CSV.zip"


def fetch_archive(destination, expected_sha256=None, allow_revised=False):
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        response = requests.get(SOURCE_URL, timeout=90)
        response.raise_for_status()
        if len(response.content) > 100_000_000:
            raise ValueError("Unexpectedly large provider archive")
        path.write_bytes(response.content)
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    changed = expected_sha256 is not None and digest != expected_sha256
    if changed and not allow_revised:
        raise ValueError("Provider archive hash differs from the published vintage. "
                         "Use --allow-revised-data to explicitly run a revised vintage.")
    return payload, {"source_url": SOURCE_URL, "archive_sha256": digest,
                     "archive_bytes": len(payload),
                     "retrieved_or_checked_utc": datetime.now(timezone.utc).isoformat(),
                     "revised_vintage": bool(changed)}


def parse_french_daily(payload):
    """Read ONLY the first value-weighted daily return panel, never equal weights.

    French files concatenate several tables. Parsing stops at the first non-date
    row following the selected panel, so the second panel cannot enter silently.
    Returns are converted from percentage points to decimal simple returns.
    """
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError("Expected exactly one CSV in the provider archive")
        member = archive.read(names[0]).decode("utf-8-sig")
    lines = member.splitlines()
    marker = next((i for i, line in enumerate(lines)
                   if "Average Value Weighted Returns" in line), None)
    if marker is None:
        raise ValueError("Value-weighted return panel marker was not found")
    first = next((i for i in range(marker + 1, len(lines))
                  if re.match(r"^\s*\d{8}\s*,", lines[i])), None)
    if first is None:
        raise ValueError("Daily dates were not found in the value-weighted panel")
    header = lines[first - 1]
    selected = []
    for line in lines[first:]:
        if not re.match(r"^\s*\d{8}\s*,", line):
            break
        selected.append(line)
    frame = pd.read_csv(io.StringIO("\n".join([header] + selected)), index_col=0)
    frame.index = pd.to_datetime(frame.index.astype(str).str.strip(), format="%Y%m%d")
    frame.index.name = "date"
    frame.columns = frame.columns.str.strip()
    frame = frame.astype(float).replace([-99.99, -999.0], np.nan) / 100
    validate_returns(frame)
    return frame, {"csv_member": names[0], "csv_member_sha256": hashlib.sha256(member.encode()).hexdigest(),
                   "first_date": str(frame.index.min().date()), "last_date": str(frame.index.max().date()),
                   "rows": len(frame), "industries": list(frame.columns),
                   "missing_cells": int(frame.isna().sum().sum())}


def validate_returns(returns):
    if not isinstance(returns.index, pd.DatetimeIndex) or not returns.index.is_monotonic_increasing:
        raise ValueError("Returns require a sorted DatetimeIndex")
    if not returns.index.is_unique or not returns.columns.is_unique:
        raise ValueError("Duplicate dates or industries")
    values = returns.to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    if np.any(np.isinf(values)) or np.any(finite < -1):
        raise ValueError("Invalid simple return outside the lower bound or infinite")
    if len(returns) == 0 or returns.shape[1] < 2:
        raise ValueError("Insufficient return panel")


def load_dataset(root, allow_revised=False):
    root = Path(root)
    old = root / "data/source_manifest.json"
    expected = json.loads(old.read_text()).get("archive_sha256") if old.exists() else None
    payload, manifest = fetch_archive(root / "data/raw/49_Industry_Portfolios_Daily_CSV.zip",
                                       expected, allow_revised)
    returns, parsed = parse_french_daily(payload)
    manifest.update(parsed)
    return returns, manifest

