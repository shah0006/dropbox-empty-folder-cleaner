**Status**: Phase 3 (Visual Insights) IN PROGRESS.
**Objective**: Build out visual analytics and advanced reporting.

---

## 1. Phase 1: Robust Copy Engine (Polish)
- [x] Basic `copy` logic (Multi-mode).
- [x] Chunked uploads (>50MB).
- [x] **Feature 1.4: Collision Handling**: Autorename/Safe rename.
- [x] **Feature 1.5: Data Rate Stats**: Real-time bit-rate calculation.

## 2. Phase 2: Deep Intelligence
- [x] **Feature 3.1: Content Hashing**: Dropbox-compatible hashing.
- [x] **Feature 3.2: Hash-Based Comparison**: Cross-path deduplication.
- [x] **Feature 3.3: Conflict Copy Detection**: Identified `(conflicted copy)` files.

## 3. Phase 3: Visual Insights (NEW)
- [x] **Feature 4.1: Size-Based Treemaps**: Visual representation of disk usage.
- [x] **Feature 4.2: Conflict Resolution UI**: Bulk actions for conflicted copies.
- [x] **Feature 4.3: Exportable Cleanup Reports**: PDF/CSV audit logs.
- [x] **Feature 4.4: Hygiene Scorecard**: Health metrics and cleanliness score.

## 4. Phase 4: Automation & "Set-and-Forget"
- [x] **Feature 5.1: Background Watchdog**: Scheduled silent scans.
- [x] **Feature 5.2: Multi-Cloud Connectors**: Google Drive / OneDrive support.

## 3. Phase 1.2: Safety Stage
- [x] **Local Trash**: Implemented.
- [x] **Dropbox Trash**: Native integration.

---

## 🛡️ Safety Checklist (Pre-Deployment)
1. **Dry-Run Validation**: Ensure no bytes are moved during a dry run.
2. **Permission Check**: Verify write access before starting a 1,000+ file operation.
3. **Space Verification**: (For local) Ensure enough disk space for copy operations.

---

## 🛡️ Safety Checklist (Pre-Deployment)
1. **Dry-Run Validation**: Ensure no bytes are moved during a dry run.
2. **Permission Check**: Verify write access before starting a 1,000+ file operation.
3. **Space Verification**: (For local) Ensure enough disk space for copy operations.
