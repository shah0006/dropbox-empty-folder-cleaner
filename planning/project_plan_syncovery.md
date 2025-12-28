# Project Plan: Intelligent Replication Suite (Syncovery-Like Architecture)

## 1. Executive Summary
This project aims to engineer a high-fidelity synchronization and replication system based on the architectural principles of Syncovery. The system favors "white box" engineering, providing granular control, rigorous state management, and high-performance transport over disparate protocols.

## 2. Modular Architecture & Development Phases

### Module 1: Core Framework & Virtual File System (VFS)
**Objective**: Build the foundational abstraction layer to treat all storage providers (Local, Cloud, FTP) uniformly.

*   **1.1 VFS Interface (`IFileProvider`)**
    *   Define abstract base class with methods: `list_dir`, `get_metadata`, `upload_file`, `download_file`, `delete_file`, `move_file`.
    *   Implement capabilities flags (e.g., `supports_versioning`, `precision_level`).
*   **1.2 Profile Management System**
    *   Design Data Model for `Profile`: Source/Dest URIs, Mode (Mirror/Copy), Schedule, Filters.
    *   Implement Serialization (JSON/XML) for storing/loading profiles.
    *   Create `ProfileManager` to handle CRUD operations on profiles.
*   **1.3 Local Filesystem Adapter**
    *   Implement `LocalProvider` inheriting `IFileProvider`.
    *   Handle OS-specific path normalization (NFC/NFD).

### Module 2: The Synchronization Engine
**Objective**: Implement the logic core for decision-making (SmartTracking) and execution.

*   **2.1 Stateless Engine**
    *   Implement `StandardCopy` logic (Source > Dest).
    *   Implement `ExactMirror` logic (Dest == Source, delete extras).
*   **2.2 SmartTracking (Stateful Engine)**
    *   Design SQLite schema for file history (snapshots).
    *   Implement `StateDB` class for persistence.
    *   Implement Logic:
        *   New File Detection (A exists, B missing, Not in DB).
        *   Deletion Detection (A missing, B exists, In DB).
        *   Conflict Detection (A & B changed vs DB).
        *   Moved File Heuristics (Size/Time match + Hash).
*   **2.3 Comparison Logic**
    *   Implement fuzzy timestamp comparison (2-second window).
    *   Normalization of timestamps to UTC.

### Module 3: Transport Protocols & Cloud Integration
**Objective**: Expand connectivity beyond local storage.

*   **3.1 Cloud Adapters**
    *   **S3 Adapter**: Multipart upload support, pagination.
    *   **Dropbox Adapter**: (Refactor existing service into VFS pattern).
    *   **Google Drive Adapter**: (Refactor existing service).
*   **3.2 Network Adapters**
    *   **SFTP Adapter**: Optimized SSH transfer.
    *   **WebDAV Adapter**: `PROPFIND` optimization.
*   **3.3 Resilience**
    *   Implement Exponential Backoff for API throttling (429 handling).

### Module 4: Performance & Optimization
**Objective**: Maximize throughput and minimize bandwidth.

*   **4.1 Concurrency Manager**
    *   Implement `ThreadPool` for parallel file processing.
    *   Implement parallel chunk upgrades for large files.
*   **4.2 Block-Level Sync (Delta)**
    *   Implement rolling checksum algorithm (Adler-32/MD5) for differential transfer.
    *   Logic to patch files or create synthetic backups.
*   **4.3 Streaming Compression (`.sz` equivalent)**
    *   Implement Zstd streaming pipeline.
    *   No-temp-file architecture (RAM buffer -> Network).

### Module 5: Safety & Security
**Objective**: Zero data loss and secure transport.

*   **5.1 Safety Valve (Ransomware Protection)**
    *   Implement `DeleteThreshold` logic (e.g., abort if >10% deletions).
    *   Alerting mechanism.
*   **5.2 Archive & Versioning**
    *   Implement `SoftDelete`: Move deleted files to `_DeletedFiles` folder instead of unlink.
*   **5.3 Encryption**
    *   Client-side AES-256 stream encryption.
    *   Filename encryption layer.

### Module 6: Automation & Interface
**Objective**: Headless operation and user management.

*   **6.1 Service Daemon**
    *   Decouple engine from UI. Run as background service.
    *   Scheduler implementation (Cron/Interval).
*   **6.2 API & CLI**
    *   REST API for controlling the daemon (FastAPI).
    *   CLI tool for scripting/batch operations.
*   **6.3 Web Dashboard**
    *   Visual Profile Editor.
    *   Real-time progress monitoring (connecting to WebSocket/API).

## 3. Implementation Roadmap Strategy

1.  **Refactor Phase**: Convert current `dropbox_service.py` / `google_service.py` into Module 1 VFS pattern.
2.  **Logic Phase**: Build Module 2 (SmartTracking).
3.  **Expansion Phase**: Add Module 3 adapters.
4.  **Hardening Phase**: Implement Module 5 safety checks.
5.  **Performance Phase**: Add Module 4 concurrency/compression.
