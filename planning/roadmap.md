# 🗺️ Product Roadmap: Intelligent Hygiene Suite v2.0

This document outlines the strategic evolution of the Dropbox Empty Folder Cleaner into a comprehensive **Intelligent Hygiene Suite**.

## 🎯 Vision
To transform a simple cleanup script into an "Intelligent Custodian" for cloud and local filesystems, prioritizing **Safety, Intelligence, and Visual Insight**.

---

## 🏛️ Phase 1: Robust Foundation & Safety (Current)
*Focus: Ensuring no data loss and robust multi-mode operations.*

1.  **[IN PROGRESS] Cross-Platform Copy Engine**: Implement bit-for-bit file copying between Dropbox and Local modes.
2.  **Safety Stage (Trash)**: Implement a `.cleaner_trash` mechanism for "soft" deletions.
3.  **Atomic Operations**: Batch processing with rollback capability.
4.  **Premium UI Polish**: Full implementation of Glassmorphism and Mobile responsiveness (95% complete).

## 🧠 Phase 2: Deep Intelligence
*Focus: Understanding data content and identifying waste.*

1.  **MD5/SHA-256 Deduplication**: Identify identical files regardless of name.
2.  **Conflict Copy Detection**: Specifically targeting Dropbox `(conflicted copy)` patterns.
3.  **Heuristic "Junk" Filters**: Automatic identification of installer stubs, temp files, and partial downloads.
4.  **Similarity Analysis**: Flagging near-duplicate documents for manual review.

## 📊 Phase 3: Visual Insights & Observability
*Focus: Making abstract file structures tangible.*

1.  **[COMPLETE] Interactive Disk Map (TreeMap)**: Scalable visual representation of folder size.
2.  **[COMPLETE] Conflict Resolution UI**: Bulk actions for conflicted copies.
3.  **[COMPLETE] Hygiene Scorecard**: Metrics on folder health (nesting depth, empty ratios).
4.  **Timeline Monitoring**: Growth/Shrinkage trends of critical directories.

## 🤖 Phase 4: Automation & "Set-and-Forget"
*Focus: Moving from reactive tools to proactive agents.*

1.  **Background Watchdog**: Scheduled "Silent Scans" that report findings.
2.  **Headless Mode**: Docker support for NAS/Server deployments.
3.  **Multi-Cloud Connectors**: Expanding to Google Drive and OneDrive.

---

## 🛠️ Code Hygiene & Maintenance
*   **Audit Frequency**: Perform "Cleanup Sprints" after every major feature.
*   **Documentation**: Maintain up-to-date `.KIs` and implementation plans.
*   **Safety Verification**: 'Just-in-Time' checks before any destructive action.
