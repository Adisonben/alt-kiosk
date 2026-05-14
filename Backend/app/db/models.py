"""
Local database models — plain dataclasses mirroring the SQLite schema.

These are NOT ORMs. They are simple data containers used to pass
structured data between the DB layer and service layer.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Fingerprint:
    id: str                     # UUID from cloud
    employee_id: str            # FK → Employee.id
    finger_index: Optional[int] # 0-9, nullable
    fingerprint_code: str       # Base64 encoded template
    updated_at: str             # ISO8601 from cloud
    synced_at: str              # ISO8601 local sync time


@dataclass
class Employee:
    id: str                               # UUID from cloud
    emp_id: str                           # Display ID e.g. "ORG-0001"
    full_name: str
    org_id: str
    updated_at: str                       # ISO8601 from cloud
    synced_at: str                        # ISO8601 local sync time
    fingerprints: list[Fingerprint] = field(default_factory=list)


@dataclass
class SyncMetadata:
    key: str    # e.g. "employees_last_sync"
    value: str  # ISO8601 timestamp or version string
    updated_at: str


@dataclass
class ScanLog:
    id: Optional[int]       # Auto-increment PK, None before insert
    employee_id: str        # FK → Employee.id (cloud UUID)
    scan_type: str          # "fingerprint" | "alcohol"
    result: str             # "match" | "no_match" | "pass" | "fail"
    value: Optional[float]  # Alcohol reading (mg%), None for fingerprint
    scanned_at: str         # ISO8601
    uploaded: bool          # False = pending upload
    upload_error: Optional[str]  # Last error message if upload failed
