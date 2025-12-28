        console.log('=== SCRIPT STARTING ===');
        
        let pollInterval = null;
        let emptyFolders = [];
        let selectedFolderPath = '';
        let loadedFolders = new Set(); // Track which folders have been loaded
        
        // Folder Tree Functions
        function selectFolder(element, path) {
            console.log('selectFolder called with path:', path);
            
            // Remove selected class from all items
            document.querySelectorAll('.tree-item.selected').forEach(el => {
                el.classList.remove('selected');
            });
            
            // Add selected class to clicked item
            element.classList.add('selected');
            
            // Update hidden input and display
            selectedFolderPath = path;
            document.getElementById('folderSelect').value = path;
            document.getElementById('selectedPath').textContent = path || '/ (Entire Dropbox)';
            
            console.log('selectedFolderPath is now:', selectedFolderPath);
        }
        
        // Event delegation for tree clicks (runs immediately since script is at end of body)
        (function() {
            const treeContainer = document.getElementById('folderTreeContainer');
            if (treeContainer) {
                treeContainer.addEventListener('click', function(event) {
                    const target = event.target;
                    
                    // Check if expand arrow was clicked
                    if (target.classList.contains('tree-expand')) {
                        event.stopPropagation();
                        const treeItem = target.closest('.tree-item');
                        if (treeItem) {
                            const path = treeItem.dataset.path;
                            console.log('Expand clicked, path:', path);
                            toggleFolderExpand(treeItem, path);
                        }
                        return;
                    }
                    
                    // Check if a tree item was clicked (but not the expand icon)
                    const treeItem = target.closest('.tree-item');
                    if (treeItem) {
                        const path = treeItem.dataset.path;
                        console.log('Tree item clicked, path:', path);
                        selectFolder(treeItem, path);
                    }
                });
            }
        })();
        
        async function toggleFolderExpand(element, path) {
            const wrapper = element.closest('.tree-item-wrapper') || element.parentElement;
            const childrenContainer = wrapper.querySelector('.tree-children');
            const expandIcon = element.querySelector('.tree-expand');
            
            if (!childrenContainer) return;
            
            // If already expanded, collapse
            if (!childrenContainer.classList.contains('collapsed')) {
                childrenContainer.classList.add('collapsed');
                if (expandIcon) expandIcon.classList.remove('expanded');
                return;
            }
            
            // If not loaded yet, load subfolders
            if (!loadedFolders.has(path)) {
                if (expandIcon) {
                    expandIcon.classList.add('loading');
                    expandIcon.textContent = '⟳';
                }
                
                try {
                    const response = await fetch('/api/subfolders?path=' + encodeURIComponent(path));
                    const data = await response.json();
                    
                    if (data.subfolders && data.subfolders.length > 0) {
                        childrenContainer.innerHTML = data.subfolders.map(folder => {
                            const escapedPath = folder.path.replace(/"/g, '&quot;');
                            return `
                            <div class="tree-item-wrapper">
                                <div class="tree-item" data-path="${escapedPath}">
                                    <span class="tree-expand">▶</span>
                                    <span class="tree-icon">📁</span>
                                    <span class="tree-label">${folder.name}</span>
                                </div>
                                <div class="tree-children collapsed"></div>
                            </div>
                        `}).join('');
                    } else {
                        childrenContainer.innerHTML = '<div class="tree-empty">No subfolders</div>';
                    }
                    
                    loadedFolders.add(path);
                } catch (e) {
                    console.error('Failed to load subfolders:', e);
                    childrenContainer.innerHTML = '<div class="tree-empty">Error loading folders</div>';
                }
                
                if (expandIcon) {
                    expandIcon.classList.remove('loading');
                    expandIcon.textContent = '▶';
                }
            }
            
            // Expand
            childrenContainer.classList.remove('collapsed');
            expandIcon.classList.add('expanded');
        }
        
        async function loadRootFolders() {
            console.log('loadRootFolders() called');
            const container = document.getElementById('rootFolders');
            if (!container) {
                console.error('rootFolders container not found!');
                return;
            }
            
            try {
                console.log('Fetching /api/subfolders?path=');
                const response = await fetch('/api/subfolders?path=');
                console.log('Response status:', response.status);
                const data = await response.json();
                console.log('Received', data.subfolders ? data.subfolders.length : 0, 'folders');
                
                if (data.subfolders && data.subfolders.length > 0) {
                    container.innerHTML = data.subfolders.map(folder => {
                        const escapedPath = folder.path.replace(/"/g, '&quot;');
                        return `
                        <div class="tree-item-wrapper">
                            <div class="tree-item" data-path="${escapedPath}">
                                <span class="tree-expand">▶</span>
                                <span class="tree-icon">📁</span>
                                <span class="tree-label">${folder.name}</span>
                            </div>
                            <div class="tree-children collapsed"></div>
                        </div>
                    `}).join('');
                    console.log('Folder tree HTML updated');
                } else {
                    container.innerHTML = '<div class="tree-empty">No folders found</div>';
                    console.log('No subfolders returned');
                }
            } catch (e) {
                console.error('Failed to load root folders:', e);
                container.innerHTML = '<div class="tree-empty">Error loading folders: ' + e.message + '</div>';
            }
        }
        
        // Get list of currently expanded folder paths
        function getExpandedPaths() {
            const expanded = [];
            document.querySelectorAll('.tree-children:not(.collapsed)').forEach(container => {
                const wrapper = container.closest('.tree-item-wrapper');
                if (wrapper) {
                    const treeItem = wrapper.querySelector('.tree-item');
                    if (treeItem && treeItem.dataset.path) {
                        expanded.push(treeItem.dataset.path);
                    }
                }
            });
            // Also include root if rootFolders is visible
            const rootFolders = document.getElementById('rootFolders');
            if (rootFolders && !rootFolders.classList.contains('collapsed')) {
                expanded.push('');  // Root path is empty string
            }
            return expanded;
        }
        
        // Re-expand folders to given paths
        async function expandToPaths(paths) {
            console.log('expandToPaths called with:', paths);
            for (const path of paths) {
                if (path === '') {
                    // Root is always expanded, skip
                    continue;
                }
                
                // Find the tree item with this path using attribute selector with escaped quotes
                const escapedPath = path.replace(/"/g, '\\"');
                const treeItem = document.querySelector('.tree-item[data-path="' + escapedPath + '"]');
                console.log('Looking for path:', path, '- Found:', !!treeItem);
                
                if (treeItem) {
                    const wrapper = treeItem.closest('.tree-item-wrapper');
                    const childrenContainer = wrapper ? wrapper.querySelector('.tree-children') : null;
                    
                    if (childrenContainer && childrenContainer.classList.contains('collapsed')) {
                        // Expand this folder
                        console.log('Expanding:', path);
                        await toggleFolderExpand(treeItem, path);
                    }
                } else {
                    console.log('Could not find tree item for path:', path);
                }
            }
        }
        
        // Refresh folder tree after deletions (preserving expanded state)
        async function refreshFolderTree() {
            console.log('========================================');
            console.log('REFRESH FOLDER TREE STARTING');
            console.log('========================================');
            
            // Save currently expanded paths and selected path
            const expandedPaths = getExpandedPaths();
            const previousSelection = selectedFolderPath;
            console.log('Preserving expanded paths:', expandedPaths);
            console.log('Preserving selection:', previousSelection);
            
            // Clear ALL caches
            loadedFolders.clear();
            console.log('Cleared loadedFolders cache');
            
            // Force reload root folders from Dropbox
            console.log('Calling loadRootFolders...');
            await loadRootFolders();
            console.log('loadRootFolders completed');
            
            // Re-expand previously expanded folders (in order from root to deep)
            // Sort by depth (number of slashes) to expand parents before children
            expandedPaths.sort((a, b) => (a.match(/\//g) || []).length - (b.match(/\//g) || []).length);
            console.log('About to re-expand paths:', expandedPaths);
            
            for (const path of expandedPaths) {
                if (path === '') continue;
                console.log('Re-expanding path:', path);
                const escapedPath = path.replace(/"/g, '\\"');
                const treeItem = document.querySelector('.tree-item[data-path="' + escapedPath + '"]');
                if (treeItem) {
                    console.log('Found tree item for:', path);
                    await toggleFolderExpand(treeItem, path);
                } else {
                    console.log('Tree item NOT found for (may have been deleted):', path);
                }
            }
            
            // Try to re-select the previously selected folder
            if (previousSelection) {
                const escapedSelection = previousSelection.replace(/"/g, '\\"');
                const prevItem = document.querySelector('.tree-item[data-path="' + escapedSelection + '"]');
                if (prevItem) {
                    selectFolder(prevItem, previousSelection);
                    console.log('Re-selected folder:', previousSelection);
                } else {
                    // Folder was deleted, reset to root
                    console.log('Previous selection no longer exists, resetting to root');
                    selectedFolderPath = '';
                    document.getElementById('folderSelect').value = '';
                    document.getElementById('selectedPath').textContent = '/ (Entire Dropbox)';
                    
                    document.querySelectorAll('.tree-item.selected').forEach(el => el.classList.remove('selected'));
                    const rootItem = document.querySelector('.tree-item.root-item');
                    if (rootItem) rootItem.classList.add('selected');
                }
            }
            console.log('========================================');
            console.log('REFRESH FOLDER TREE COMPLETE');
            console.log('========================================');
        }
        
        // Manual refresh button handler
        window.manualRefreshTree = async function() {
            console.log('Manual tree refresh triggered');
            await refreshFolderTree();
        };
        
        // Track if we've already refreshed after last deletion
        let lastDeleteRefreshed = false;
        
        async function fetchStatus() {
            console.log('fetchStatus() running...');
            try {
                const response = await fetch('/api/status');
                console.log('Got response:', response.status);
                if (!response.ok) {
                    console.error('Status response not OK:', response.status);
                    return;
                }
                const data = await response.json();
                console.log('Status data - connected:', data.connected);
                await updateUI(data);
                console.log('updateUI() completed');
            } catch (e) {
                console.error('Failed to fetch status:', e);
            }
        }
        
        function formatNumber(num) {
            return num.toLocaleString();
        }
        
        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function animateValue(elementId, newValue) {
            const el = document.getElementById(elementId);
            if (el.textContent !== newValue) {
                el.classList.add('updating');
                el.textContent = newValue;
                setTimeout(() => el.classList.remove('updating'), 150);
            }
        }
        
        async function updateUI(data) {
            // Connection status
            const statusEl = document.getElementById('connectionStatus');
            const accountEl = document.getElementById('accountInfo');
            const setupPrompt = document.getElementById('setupPrompt');
            
            const mode = data.config?.mode || 'dropbox';
            
            if (mode === 'local') {
                // Local mode - no Dropbox connection needed
                statusEl.className = 'status-badge status-connected';
                statusEl.innerHTML = '<span class="status-dot"></span> Local Ready';
                accountEl.textContent = `Path: ${data.config?.local_path || 'Not set'}`;
                setupPrompt.style.display = 'none';
            } else if (data.connected) {
                statusEl.className = 'status-badge status-connected';
                statusEl.innerHTML = '<span class="status-dot"></span> Connected';
                accountEl.textContent = `Logged in as ${data.account_name} (${data.account_email})`;
                setupPrompt.style.display = 'none';
            } else {
                statusEl.className = 'status-badge status-disconnected';
                statusEl.innerHTML = '<span class="status-dot"></span> Not Connected';
                accountEl.textContent = '';
                setupPrompt.style.display = 'block';
            }
            
            // Folder tree is loaded separately via loadRootFolders()
            // No need to populate dropdown anymore since we use tree view
            
            // Progress
            const progressCard = document.getElementById('progressCard');
            const scanBtn = document.getElementById('scanBtn');
            const deleteBtn = document.getElementById('deleteBtn');
            const progressSpinner = document.getElementById('progressSpinner');
            const emptyStatCard = document.getElementById('emptyStatCard');
            
            const percentDisplay = document.getElementById('percentDisplay');
            const timeStatCard = document.getElementById('timeStatCard');
            const rateStatCard = document.getElementById('rateStatCard');
            
            if (data.scanning) {
                progressCard.style.display = 'block';
                document.getElementById('progressTitle').textContent = 'Scanning your Dropbox...';
                document.getElementById('progressStatus').className = 'status-badge status-scanning';
                document.getElementById('progressStatus').innerHTML = '<span class="status-dot"></span> In Progress';
                document.getElementById('progressFill').className = 'progress-bar-fill indeterminate';
                
                // Show cancel button during scan
                document.getElementById('cancelScanBtn').style.display = 'flex';
                
                // Animate the numbers
                animateValue('folderCount', formatNumber(data.scan_progress.folders));
                animateValue('fileCount', formatNumber(data.scan_progress.files));
                animateValue('elapsedTime', formatTime(data.scan_progress.elapsed || 0));
                animateValue('itemRate', formatNumber(data.scan_progress.rate || 0));
                
                progressSpinner.style.display = 'block';
                document.getElementById('folderStatCard').classList.add('active');
                document.getElementById('fileStatCard').classList.add('active');
                timeStatCard.style.display = 'block';
                rateStatCard.style.display = 'block';
                timeStatCard.classList.add('active');
                rateStatCard.classList.add('active');
                emptyStatCard.style.display = 'none';
                percentDisplay.style.display = 'none';
                scanBtn.disabled = true;
                deleteBtn.disabled = true;
            } else if (data.deleting) {
                progressCard.style.display = 'block';
                document.getElementById('progressTitle').textContent = '⚡ Fast Deleting Empty Folders...';
                
                const pct = data.delete_progress.percent || 0;
                const deleted = data.delete_progress.deleted || 0;
                const skipped = data.delete_progress.skipped || 0;
                const errors = data.delete_progress.errors || 0;
                
                document.getElementById('progressStatus').innerHTML = `${pct}%`;
                document.getElementById('progressStatus').className = 'status-badge status-scanning';
                document.getElementById('progressFill').className = 'progress-bar-fill';
                document.getElementById('progressFill').style.width = pct + '%';
                
                // Show big percentage with detailed stats
                percentDisplay.style.display = 'block';
                animateValue('percentValue', `${pct}%`);
                let statusText = `Deleted: ${deleted}`;
                if (skipped > 0) statusText += ` | Skipped: ${skipped}`;
                if (errors > 0) statusText += ` | Errors: ${errors}`;
                document.getElementById('percentDisplay').querySelector('.percent-label').textContent = statusText;
                
                // Update streaming log for folder deletion
                if (data.delete_progress.log && data.delete_progress.log.length > 0) {
                    updateFolderDeletionLog(data.delete_progress.log);
                }
                
                // Hide scan stats during deletion
                document.getElementById('folderStatCard').style.display = 'none';
                document.getElementById('fileStatCard').style.display = 'none';
                timeStatCard.style.display = 'none';
                rateStatCard.style.display = 'none';
                emptyStatCard.style.display = 'none';
                
                progressSpinner.style.display = 'block';
                scanBtn.disabled = true;
                deleteBtn.disabled = true;
            } else {
                scanBtn.disabled = false;
                progressSpinner.style.display = 'none';
                document.getElementById('cancelScanBtn').style.display = 'none';  // Hide cancel button
                document.getElementById('folderStatCard').classList.remove('active');
                document.getElementById('fileStatCard').classList.remove('active');
                timeStatCard.classList.remove('active');
                rateStatCard.classList.remove('active');
                percentDisplay.style.display = 'none';
                
                // Show all stat cards again
                document.getElementById('folderStatCard').style.display = 'block';
                document.getElementById('fileStatCard').style.display = 'block';
                
                if (data.scan_progress.status === 'complete') {
                    progressCard.style.display = 'block';
                    document.getElementById('progressTitle').textContent = 'Scan Complete!';
                    document.getElementById('progressStatus').className = 'status-badge status-connected';
                    document.getElementById('progressStatus').innerHTML = '<span class="status-dot"></span> Done';
                    
                    // Solid green completed progress bar
                    document.getElementById('progressFill').className = 'progress-bar-fill complete';
                    document.getElementById('progressFill').style.width = '100%';
                    
                    // Show final stats
                    timeStatCard.style.display = 'block';
                    rateStatCard.style.display = 'block';
                    animateValue('elapsedTime', formatTime(data.scan_progress.elapsed || 0));
                    animateValue('itemRate', formatNumber(data.scan_progress.rate || 0));
                    
                    // Note: No need to refresh folder tree after scan - it only reads, doesn't modify
                    // Tree refresh only needed after deletion
                    
                    // Show empty count stat
                    emptyStatCard.style.display = 'block';
                    animateValue('emptyCount', formatNumber(data.empty_folders.length));
                } else if (data.scan_progress.status === 'cancelled') {
                    progressCard.style.display = 'block';
                    document.getElementById('progressTitle').textContent = 'Scan Cancelled';
                    document.getElementById('progressStatus').className = 'status-badge status-disconnected';
                    document.getElementById('progressStatus').innerHTML = '<span class="status-dot"></span> Cancelled';
                    document.getElementById('progressFill').className = 'progress-bar-fill';
                    document.getElementById('progressFill').style.width = '0%';
                    
                    // Show stats from partial scan
                    timeStatCard.style.display = 'block';
                    rateStatCard.style.display = 'block';
                    animateValue('elapsedTime', formatTime(data.scan_progress.elapsed || 0));
                    animateValue('itemRate', formatNumber(data.scan_progress.rate || 0));
                }
                
                // Check if deletion just completed
                if (data.delete_progress.status === 'complete' && !data.deleting) {
                    document.getElementById('progressFill').className = 'progress-bar-fill complete';
                    
                    // Refresh folder tree after deletion (only once)
                    if (!lastDeleteRefreshed) {
                        lastDeleteRefreshed = true;
                        console.log('*************************************************');
                        console.log('DELETION COMPLETE - TRIGGERING TREE REFRESH');
                        console.log('*************************************************');
                        
                        // Small delay to ensure backend has finished
                        await new Promise(resolve => setTimeout(resolve, 500));
                        
                        await refreshFolderTree();
                        console.log('*************************************************');
                        console.log('TREE REFRESH AFTER DELETION COMPLETE');
                        console.log('*************************************************');
                    }
                } else if (data.deleting) {
                    // Reset flag when new deletion starts
                    lastDeleteRefreshed = false;
                    console.log('Deletion started - refresh flag reset');
                }
            }
            
            // Update config UI
            updateConfigUI(data.config);

            // Update next run time
            const nextRunContainer = document.getElementById('nextRunContainer');
            const nextRunTime = document.getElementById('nextRunTime');
            if (data.next_scheduled_run !== null && data.next_scheduled_run !== undefined) {
                const hours = Math.floor(data.next_scheduled_run / 3600);
                const minutes = Math.floor((data.next_scheduled_run % 3600) / 60);
                nextRunTime.textContent = `in ${hours}h ${minutes}m`;
                nextRunContainer.style.display = 'inline';
            } else {
                nextRunContainer.style.display = 'none';
            }
            
            // Results
            if (data.empty_folders.length > 0 || data.scan_progress.status === 'complete') {
                const resultsCard = document.getElementById('resultsCard');
                resultsCard.style.display = 'block';
                
                emptyFolders = data.empty_folders;
                
                // Update badge counts
                document.getElementById('emptyFoldersBadge').textContent = formatNumber(emptyFolders.length);
                const filesCount = data.files_found_count || 0;
                document.getElementById('filesFoundBadge').textContent = formatNumber(filesCount);
                const conflictsCount = data.conflicts_count || 0;
                document.getElementById('conflictsBadge').textContent = formatNumber(conflictsCount);
                
                // Update statistics
                updateStats(data.stats);
                
                // Store data for visual insights
                if (data.scan_progress && data.scan_progress.folder_sizes) {
                    currentFolderSizes = data.scan_progress.folder_sizes;
                }
                if (data.stats) {
                    currentStats = data.stats;
                }
                
                // Only update results list if we're in folders view or it's a fresh load
                if (currentResultsView === 'folders') {
                    document.getElementById('resultsCount').textContent = `${emptyFolders.length} empty folder(s)`;
                    
                    const resultsList = document.getElementById('resultsList');
                    if (emptyFolders.length === 0) {
                        resultsList.innerHTML = `
                            <div class="success-state">
                                <div class="success-icon">✨</div>
                                <div class="success-title">All Clean!</div>
                                <p class="success-text">No empty folders found in this location.</p>
                            </div>`;
                        document.getElementById('warningBox').style.display = 'none';
                        deleteBtn.disabled = true;
                    } else {
                        resultsList.innerHTML = emptyFolders.map((folder, i) => 
                            `<div class="folder-item">
                                <span class="folder-item-num">${i + 1}.</span>
                                <span>${folder}</span>
                            </div>`
                        ).join('');
                        document.getElementById('warningBox').style.display = 'flex';
                        deleteBtn.disabled = false;
                    }
                }
            }
        }
        
        async function startScan() {
            const folder = selectedFolderPath; // Use tree selection
            console.log('startScan called, folder:', folder);
            
            // Reset refresh flag for next deletion cycle
            lastDeleteRefreshed = false;
            
            // Reset results view and files list for new scan
            filesFoundList = [];
            currentResultsView = 'folders';
            document.getElementById('viewEmptyFoldersBtn').classList.add('active');
            document.getElementById('viewFilesBtn').classList.remove('active', 'files-active');
            document.getElementById('emptyFoldersBadge').textContent = '0';
            document.getElementById('filesFoundBadge').textContent = '0';
            
            document.getElementById('resultsCard').style.display = 'none';
            document.getElementById('emptyStatCard').style.display = 'none';
            
            try {
                const response = await fetch('/api/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({folder: folder})
                });
                const result = await response.json();
                console.log('Scan API response:', result);
            } catch (e) {
                console.error('Failed to start scan:', e);
            }
        }
        
        async function cancelScan() {
            console.log('Cancelling scan...');
            try {
                const response = await fetch('/api/cancel', {method: 'POST'});
                const result = await response.json();
                console.log('Cancel response:', result);
                
                if (result.status === 'cancelled') {
                    showToast('Scan cancelled', 'info');
                    document.getElementById('progressTitle').textContent = 'Scan Cancelled';
                    document.getElementById('progressStatus').className = 'status-badge status-disconnected';
                    document.getElementById('progressStatus').innerHTML = '<span class="status-dot"></span> Cancelled';
                    document.getElementById('progressFill').className = 'progress-bar-fill';
                    document.getElementById('progressFill').style.width = '0%';
                    document.getElementById('cancelScanBtn').style.display = 'none';
                    document.getElementById('progressSpinner').style.display = 'none';
                    document.getElementById('scanBtn').disabled = false;
                }
            } catch (e) {
                console.error('Failed to cancel scan:', e);
                showToast('Failed to cancel scan', 'error');
            }
        }
        
        function confirmDelete() {
            document.getElementById('deleteCount').textContent = emptyFolders.length;
            document.getElementById('deleteModal').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('deleteModal').classList.remove('active');
        }
        
        function showHelp() {
            document.getElementById('helpModal').classList.add('active');
        }
        
        function closeHelp() {
            document.getElementById('helpModal').classList.remove('active');
        }
        
        async function executeDelete() {
            closeModal();
            
            // Reset the folder deletion log for fresh start
            resetFolderDeletionLog();
            
            try {
                await fetch('/api/delete', {method: 'POST'});
                showToast('⚡ Fast deletion started!', 'success');
            } catch (e) {
                console.error('Failed to delete:', e);
                showToast('Failed to start deletion', 'error');
            }
        }
        
        async function updateConfig() {
            const ignoreSystemFiles = document.getElementById('ignoreSystemFiles').checked;
            try {
                await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ignore_system_files: ignoreSystemFiles})
                });
            } catch (e) {
                console.error('Failed to update config:', e);
            }
        }
        
        function exportResults(format) {
            window.open(`/api/export?format=${format}`, '_blank');
        }
        
        // Track current results view and files data
        let currentResultsView = 'folders';
        let filesFoundList = [];
        let currentFolderSizes = {};
        let currentStats = {};
        let conflictsList = [];
        
        // Switch between empty folders and files view
        async function switchResultsView(view) {
            currentResultsView = view;
            const foldersBtn = document.getElementById('viewEmptyFoldersBtn');
            const filesBtn = document.getElementById('viewFilesBtn');
            const insightsBtn = document.getElementById('viewInsightsBtn');
            const resultsList = document.getElementById('resultsList');
            const warningBox = document.getElementById('warningBox');
            const deleteBtn = document.getElementById('deleteBtn');
            const resultsCount = document.getElementById('resultsCount');
            
            // Remove active class from all buttons
            foldersBtn.classList.remove('active');
            filesBtn.classList.remove('active', 'files-active');
            const conflictsBtn = document.getElementById('viewConflictsBtn');
            conflictsBtn.classList.remove('active', 'conflicts-active');
            insightsBtn.classList.remove('active', 'insights-active');
            
            if (view === 'files') {
                filesBtn.classList.add('active', 'files-active');
                
                // Hide delete-related elements
                warningBox.style.display = 'none';
                deleteBtn.disabled = true;
                
                // Fetch files if not already loaded
                if (filesFoundList.length === 0) {
                    try {
                        const response = await fetch('/api/files');
                        const data = await response.json();
                        filesFoundList = data.files || [];
                        document.getElementById('filesFoundBadge').textContent = formatNumber(filesFoundList.length);
                    } catch (e) {
                        console.error('Failed to fetch files:', e);
                    }
                }
                
                // Display files
                resultsCount.textContent = `${formatNumber(filesFoundList.length)} file(s) found`;
                resultsCount.style.background = 'linear-gradient(135deg, rgba(0, 188, 212, 0.2), rgba(0, 150, 200, 0.2))';
                resultsCount.style.color = 'var(--accent-cyan)';
                resultsCount.style.borderColor = 'rgba(0, 188, 212, 0.3)';
                
                if (filesFoundList.length === 0) {
                    resultsList.innerHTML = `
                        <div class="success-state">
                            <div class="success-icon">📁</div>
                            <div class="success-title">No Files Found</div>
                            <p class="success-text">No files were found in the scanned location (only empty folders or system files).</p>
                        </div>`;
                } else {
                    resultsList.innerHTML = filesFoundList.map((file, i) => 
                        `<div class="file-item">
                            <span class="file-item-num">${i + 1}.</span>
                            <span>${file}</span>
                        </div>`
                    ).join('');
                }
            } else if (view === 'conflicts') {
                conflictsBtn.classList.add('active', 'conflicts-active');
                
                // Fetch conflicts
                try {
                    const response = await fetch('/api/conflicts');
                    const data = await response.json();
                    conflictsList = data.conflicts || [];
                } catch (e) {
                    console.error('Failed to fetch conflicts:', e);
                }
                
                resultsCount.textContent = `${formatNumber(conflictsList.length)} conflict(s) found`;
                resultsCount.style.background = 'linear-gradient(135deg, rgba(234, 179, 8, 0.2), rgba(202, 138, 4, 0.2))';
                resultsCount.style.color = 'var(--accent-yellow)';
                resultsCount.style.borderColor = 'rgba(234, 179, 8, 0.3)';
                
                if (conflictsList.length === 0) {
                    resultsList.innerHTML = `
                        <div class="success-state">
                            <div class="success-icon">✅</div>
                            <div class="success-title">No Conflicts</div>
                            <p class="success-text">No conflicted copies found.</p>
                        </div>`;
                    warningBox.style.display = 'none';
                    deleteBtn.disabled = true;
                } else {
                    // Show delete all button in warning box
                    warningBox.style.display = 'flex';
                    deleteBtn.disabled = false;
                    deleteBtn.onclick = deleteConflicts; // Override onclick
                    deleteBtn.innerHTML = '⚡ Delete All Conflicts';
                    
                    resultsList.innerHTML = conflictsList.map((item, i) => 
                        `<div class="file-item" style="border-left: 2px solid var(--accent-yellow);">
                            <span class="file-item-num">${i + 1}.</span>
                            <div style="flex: 1; display: flex; flex-direction: column;">
                                <span title="${item.path}">${item.name}</span>
                                <span style="font-size: 0.8em; color: var(--text-muted);">
                                    ${formatFileSize(item.size)} | Modified: ${new Date(item.server_modified).toLocaleString()}
                                </span>
                            </div>
                        </div>`
                    ).join('');
                }

            } else if (view === 'insights') {
                insightsBtn.classList.add('active', 'insights-active');
                
                // Hide delete-related elements
                warningBox.style.display = 'none';
                deleteBtn.disabled = true;

                // Update Header
                resultsCount.textContent = 'Folder Size Analysis';
                resultsCount.style.background = 'linear-gradient(135deg, rgba(251, 146, 60, 0.2), rgba(249, 115, 22, 0.2))';
                resultsCount.style.color = 'var(--accent-orange)';
                resultsCount.style.borderColor = 'rgba(251, 146, 60, 0.3)';

                renderVisualInsights();
            } else {
                // Switch to folders view
                foldersBtn.classList.add('active');
                
                // Restore folder view styling
                resultsCount.style.background = 'linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(236, 72, 153, 0.2))';
                resultsCount.style.color = 'var(--accent-purple)';
                resultsCount.style.borderColor = 'rgba(168, 85, 247, 0.3)';
                
                // Restore delete button behavior
                deleteBtn.onclick = startDelete;
                deleteBtn.innerHTML = '⚡ Delete Found Folders';
                
                // Display empty folders
                resultsCount.textContent = `${emptyFolders.length} empty folder(s)`;
                
                if (emptyFolders.length === 0) {
                    resultsList.innerHTML = `
                        <div class="success-state">
                            <div class="success-icon">✨</div>
                            <div class="success-title">All Clean!</div>
                            <p class="success-text">No empty folders found in the scanned location. Your folder structure is clean!</p>
                        </div>`;
                    warningBox.style.display = 'none';
                    deleteBtn.disabled = true;
                } else {
                    resultsList.innerHTML = emptyFolders.map((folder, i) => 
                        `<div class="folder-item">
                            <span class="folder-item-num">${i + 1}.</span>
                            <span>${folder}</span>
                        </div>`
                    ).join('');
                    warningBox.style.display = 'flex';
                    deleteBtn.disabled = false;
                }
            }
        }
        
        async function deleteConflicts() {
            if (!confirm('Are you sure you want to delete all conflicted copies? This cannot be undone (items move to trash/recycle bin).')) {
                return;
            }
            
            try {
                const response = await fetch('/api/conflicts/delete', {method: 'POST'});
                const result = await response.json();
                
                if (result.status === 'started') {
                    showToast('Deleting conflicts...', 'info');
                } else if (result.status === 'already_deleting') {
                    showToast('Deletion already in progress', 'warning');
                } else {
                    showToast('Failed to start deletion', 'error');
                }
            } catch (e) {
                console.error('Failed to start conflict deletion:', e);
                showToast('Network error', 'error');
            }
        }

        function renderVisualInsights() {
            const resultsList = document.getElementById('resultsList');
            
            // Transform folder sizes to array
            const folderArray = Object.entries(currentFolderSizes)
                .map(([path, size]) => ({ path, size }))
                .sort((a, b) => b.size - a.size); // Sort by size desc
            
            if (folderArray.length === 0) {
                 resultsList.innerHTML = `
                    <div class="success-state">
                        <div class="success-icon">🔭</div>
                        <div class="success-title">No Insights Yet</div>
                        <p class="success-text">Scan a folder to visualize disk usage.</p>
                    </div>`;
                return;
            }
            
            // Take top 12 for treemap
            const topFolders = folderArray.slice(0, 12);
            const totalDisplayedSize = topFolders.reduce((acc, item) => acc + item.size, 0);
            
            // Hygiene Scorecard Data
            const score = currentStats.hygiene_score || 100;
            const wastedBytes = currentStats.wasted_bytes || 0;
            const emptyCount = emptyFolders ? emptyFolders.length : 0;
            const conflictsCount = currentStats.conflicts_count || 0;
            
            // Score Color
            let scoreColor = '#22c55e'; // Green
            if (score < 50) scoreColor = '#ef4444'; // Red
            else if (score < 80) scoreColor = '#f59e0b'; // Amber

            let html = `
                <!-- Hygiene Scorecard -->
                <div class="insight-card hygiene-scorecard">
                    <div class="insight-header">
                        <span class="insight-title">🩺 Hygiene Scorecard</span>
                    </div>
                    <div class="score-container">
                        
                        <!-- Score Circle -->
                        <div class="score-circle-wrapper">
                            <svg viewBox="0 0 36 36" class="score-svg">
                                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#444" stroke-width="3" />
                                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" class="score-path" stroke="${scoreColor}" stroke-width="3" stroke-dasharray="${score}, 100" />
                            </svg>
                            <div class="score-value" style="color: ${scoreColor};">${score}</div>
                        </div>
                        
                        <!-- Metrics -->
                        <div class="metrics-grid">
                            <div class="metric-item">
                                <div class="metric-label">Wasted Space</div>
                                <div class="metric-value" style="color: var(--accent-red);">${formatFileSize(wastedBytes)}</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">Conflicts</div>
                                <div class="metric-value" style="color: var(--accent-yellow);">${conflictsCount}</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">Cleanliness</div>
                                <div class="metric-value" style="color: ${scoreColor};">${score >= 80 ? 'Excellent' : (score >= 50 ? 'Fair' : 'Poor')}</div>
                            </div>
                             <div class="metric-item">
                                <div class="metric-label">Scan Depth</div>
                                <div class="metric-value" style="color: var(--accent-cyan);">${currentFolderSizes ? Object.keys(currentFolderSizes).length : 0} <span style="font-size:0.7em">folders</span></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="insight-card">
                    <div class="insight-header">
                        <span class="insight-title">📦 Largest Folders (Treemap)</span>
                    </div>
                    <div class="treemap-container">
            `;
            
            // Colors for treemap items
            const colors = ['var(--accent-cyan)', 'var(--accent-purple)', 'var(--accent-pink)', 'var(--accent-orange)', 'var(--accent-green)', 'var(--accent-red)'];
            
            html += topFolders.map((folder, i) => {
                const percent = totalDisplayedSize > 0 ? (folder.size / totalDisplayedSize) * 100 : 0;
                // Use flex-grow based on size, but clamp minimum to be visible
                const flexGrow = Math.max(1, Math.round(percent));
                // Also set basic width to help wrap
                const widthPercent = Math.max(10, percent); 
                
                const color = colors[i % colors.length];
                
                return `
                    <div class="treemap-item" style="flex-grow: ${flexGrow}; background: ${color}; min-width: ${widthPercent/2}%;" 
                         title="${folder.path} (${formatFileSize(folder.size)})">
                        <div class="treemap-label">${folder.path.split('/').pop() || '/'}</div>
                        <div class="treemap-value">${formatFileSize(folder.size)}</div>
                    </div>
                `;
            }).join('');
            
            html += `
                    </div>
                </div>
                
                <div class="insight-card">
                    <div class="insight-header">
                        <span class="insight-title">📊 Top Folders by Size</span>
                    </div>
                    <div class="results-list" style="max-height: 300px; overflow-y: auto;">
            `;
            
            // List view (Top 50)
            const listFolders = folderArray.slice(0, 50);
            
            html += listFolders.map((folder, i) => `
                <div class="folder-item">
                    <span class="folder-item-num">${i + 1}.</span>
                    <span style="flex: 1; overflow: hidden; text-overflow: ellipsis;" title="${folder.path}">${folder.path}</span>
                    <span style="color: var(--accent-orange); font-family: 'JetBrains Mono'; font-size: 0.9em;">
                        ${formatFileSize(folder.size)}
                    </span>
                </div>
            `).join('');
            
            html += `
                    </div>
                </div>
            `;
            
            resultsList.innerHTML = html;
        }
        
        function updateStats(stats) {
            const panel = document.getElementById('statsPanel');
            if (stats && stats.total_scanned > 0) {
                panel.style.display = 'block';
                document.getElementById('statScanned').textContent = formatNumber(stats.total_scanned);
                document.getElementById('statIgnored').textContent = formatNumber(stats.system_files_ignored || 0);
                
                const depths = Object.keys(stats.depth_distribution || {});
                const maxDepth = depths.length > 0 ? Math.max(...depths.map(Number)) : 0;
                document.getElementById('statDeepest').textContent = maxDepth;
            }
        }
        
        function updateConfigUI(config) {
            if (config) {
                document.getElementById('ignoreSystemFiles').checked = config.ignore_system_files !== false;
                
                // Update mode toggle buttons
                const mode = config.mode || 'dropbox';
                const dropboxBtn = document.getElementById('modeDropboxBtn');
                const localBtn = document.getElementById('modeLocalBtn');
                const dropboxInfo = document.getElementById('dropboxInfo');
                const localPathSection = document.getElementById('localPathSection');
                const inlineLocalPath = document.getElementById('inlineLocalPath');
                const rootLabel = document.getElementById('rootLabel');
                const selectedPath = document.getElementById('selectedPath');
                
                if (mode === 'local') {
                    // Activate local mode
                    dropboxBtn.classList.remove('active');
                    localBtn.classList.add('active', 'local-active');
                    dropboxInfo.style.display = 'none';
                    localPathSection.classList.add('visible');
                    if (config.local_path) {
                        inlineLocalPath.value = config.local_path;
                        rootLabel.textContent = '/ (Local Root)';
                        if (!selectedFolderPath) {
                            selectedPath.textContent = '/ (Local Root)';
                        }
                    }
                } else {
                    // Activate dropbox mode
                    localBtn.classList.remove('active', 'local-active');
                    dropboxBtn.classList.add('active');
                    dropboxInfo.style.display = 'block';
                    localPathSection.classList.remove('visible');
                    rootLabel.textContent = '/ (Entire Dropbox)';
                    if (!selectedFolderPath) {
                        selectedPath.textContent = '/ (Entire Dropbox)';
                    }
                }
            }
        }
        
        // Main page mode switcher function
        async function switchMode(mode) {
            console.log('Switching mode to:', mode);
            
            const dropboxBtn = document.getElementById('modeDropboxBtn');
            const localBtn = document.getElementById('modeLocalBtn');
            const compareBtn = document.getElementById('modeCompareBtn');
            const dropboxInfo = document.getElementById('dropboxInfo');
            const localPathSection = document.getElementById('localPathSection');
            const rootLabel = document.getElementById('rootLabel');
            const selectedPath = document.getElementById('selectedPath');
            const compareSection = document.getElementById('compareSection');
            const folderSelectCard = document.getElementById('folderTree')?.closest('.card');
            const progressCard = document.getElementById('progressCard');
            const resultsCard = document.getElementById('resultsCard');
            
            // Remove all active states
            dropboxBtn.classList.remove('active');
            localBtn.classList.remove('active', 'local-active');
            compareBtn.classList.remove('active', 'compare-active');
            
            // Update UI immediately for responsiveness
            if (mode === 'compare') {
                compareBtn.classList.add('active', 'compare-active');
                dropboxInfo.style.display = 'none';
                localPathSection.classList.remove('visible');
                compareSection.style.display = 'block';
                // Hide the folder selection, progress, and results cards for normal mode
                if (folderSelectCard) folderSelectCard.style.display = 'none';
                if (progressCard) progressCard.style.display = 'none';
                if (resultsCard) resultsCard.style.display = 'none';
                
                // Initialize compare folder trees
                setupCompareTreeHandlers();
                loadCompareFolders('left', '');
                loadCompareFolders('right', '');
                
                showToast('Switched to Compare Mode', 'success');
                return; // Don't need to save to config or reload folders
            } else {
                compareSection.style.display = 'none';
                // Show the folder selection card
                if (folderSelectCard) folderSelectCard.style.display = 'block';
                
                if (mode === 'local') {
                    localBtn.classList.add('active', 'local-active');
                    dropboxInfo.style.display = 'none';
                    localPathSection.classList.add('visible');
                    rootLabel.textContent = '/ (Local Root)';
                    selectedPath.textContent = '/ (Local Root)';
                } else {
                    dropboxBtn.classList.add('active');
                    dropboxInfo.style.display = 'block';
                    localPathSection.classList.remove('visible');
                    rootLabel.textContent = '/ (Entire Dropbox)';
                    selectedPath.textContent = '/ (Entire Dropbox)';
                }
            }
            
            // Reset selected folder to root when switching modes
            selectedFolderPath = '';
            document.getElementById('folderSelect').value = '';
            
            // Save the mode change
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ mode: mode })
                });
                
                if (response.ok) {
                    showToast(mode === 'local' ? 'Switched to Local Mode' : 'Switched to Dropbox Mode', 'success');
                    
                    // Clear and reload folder tree for new mode
                    loadedFolders.clear();
                    await loadRootFolders();
                    
                    // Re-select root
                    const rootItem = document.querySelector('.tree-item.root-item');
                    if (rootItem) {
                        document.querySelectorAll('.tree-item.selected').forEach(el => el.classList.remove('selected'));
                        rootItem.classList.add('selected');
                    }
                    
                    // Update connection status
                    fetchStatus();
                } else {
                    showToast('Failed to switch mode', 'error');
                }
            } catch (e) {
                console.error('Failed to switch mode:', e);
                showToast('Failed to switch mode', 'error');
            }
        }
        
        // =====================================================================
        // FOLDER COMPARISON FUNCTIONS
        // =====================================================================
        
        let compareLeftMode = 'dropbox';
        let compareRightMode = 'dropbox';
        let compareResults = null;
        let currentCompareView = 'delete';
        let comparePollInterval = null;
        let compareRunMode = 'preview';  // 'preview' or 'live'
        let compareLoadedFolders = { left: new Set(), right: new Set() };
        
        // Load folders for compare trees
        async function loadCompareFolders(side, parentPath = '') {
            const containerId = side === 'left' ? 'leftRootFolders' : 'rightRootFolders';
            const container = document.getElementById(containerId);
            
            if (!container) {
                console.log(`Container ${containerId} not found`);
                return;
            }
            
            // Check if already loaded
            const cacheKey = `${side}:${parentPath}`;
            if (compareLoadedFolders[side].has(cacheKey)) {
                console.log(`Folders for ${side}:${parentPath} already loaded`);
                return;
            }
            
            container.innerHTML = '<div class="tree-loading">Loading folders...</div>';
            
            try {
                console.log(`Loading compare folders for ${side}, path: ${parentPath}`);
                const response = await fetch(`/api/subfolders?path=${encodeURIComponent(parentPath)}`);
                const data = await response.json();
                
                // API returns "subfolders" not "folders"
                const folders = data.subfolders || data.folders || [];
                console.log(`Got ${folders.length} folders for ${side}`);
                
                if (folders.length > 0) {
                    container.innerHTML = folders.map(folder => {
                        const escapedPath = folder.path.replace(/"/g, '&quot;');
                        return `
                            <div class="tree-node">
                                <div class="tree-item" data-path="${escapedPath}" data-side="${side}">
                                    <span class="tree-expand">▶</span>
                                    <span class="tree-icon">📁</span>
                                    <span class="tree-label">${folder.name}</span>
                                </div>
                                <div class="tree-children collapsed"></div>
                            </div>
                        `;
                    }).join('');
                } else {
                    container.innerHTML = '<div class="tree-loading">No subfolders</div>';
                }
                
                compareLoadedFolders[side].add(cacheKey);
            } catch (e) {
                console.error('Failed to load compare folders:', e);
                container.innerHTML = '<div class="tree-loading">Error loading folders</div>';
            }
        }
        
        // Handle compare tree clicks
        function setupCompareTreeHandlers() {
            ['left', 'right'].forEach(side => {
                const containerId = side === 'left' ? 'leftFolderTreeContainer' : 'rightFolderTreeContainer';
                const container = document.getElementById(containerId);
                if (!container) return;
                
                container.addEventListener('click', async function(event) {
                    const target = event.target;
                    const treeItem = target.closest('.tree-item');
                    if (!treeItem) return;
                    
                    const path = treeItem.dataset.path;
                    const itemSide = treeItem.dataset.side;
                    
                    // Handle expand/collapse
                    if (target.classList.contains('tree-expand')) {
                        const node = treeItem.closest('.tree-node') || treeItem.parentElement;
                        const children = node.querySelector('.tree-children');
                        
                        if (children) {
                            children.classList.toggle('collapsed');
                            target.classList.toggle('expanded');
                            
                            // Load subfolders if expanding and not yet loaded
                            if (!children.classList.contains('collapsed') && 
                                children.innerHTML.includes('Loading') || children.innerHTML === '') {
                                children.innerHTML = '<div class="tree-loading">Loading...</div>';
                                await loadCompareSubfolders(itemSide, path, children);
                            }
                        }
                        return;
                    }
                    
                    // Handle selection
                    const allItems = container.querySelectorAll('.tree-item');
                    allItems.forEach(item => item.classList.remove('selected'));
                    treeItem.classList.add('selected');
                    
                    // Update the path input and display
                    const pathInput = document.getElementById(side === 'left' ? 'leftFolderPath' : 'rightFolderPath');
                    const pathDisplay = document.getElementById(side === 'left' ? 'leftSelectedPath' : 'rightSelectedPath');
                    
                    pathInput.value = path;
                    pathDisplay.textContent = path || '/ (Root)';
                    
                    // Reset comparison state when a new folder is selected
                    resetCompareStateForNewSelection();
                    
                    // Update action summary
                    updateActionSummary();
                });
            });
        }
        
        // Reset state when user selects a new folder (ready for new scan)
        function resetCompareStateForNewSelection() {
            // Hide results and progress cards
            document.getElementById('compareResultsCard').style.display = 'none';
            document.getElementById('compareProgressCard').style.display = 'none';
            
            // Re-enable the scan button
            document.getElementById('compareStartBtn').disabled = false;
            document.getElementById('compareCancelBtn').style.display = 'none';
            
            // Reset progress bar
            const progressFill = document.getElementById('compareProgressFill');
            if (progressFill) {
                progressFill.className = 'progress-bar-fill indeterminate';
                progressFill.style.width = '';
            }
            
            // Clear previous results
            compareResults = null;
            
            // Reset to preview mode
            setCompareRunMode('preview');
        }
        
        async function loadCompareSubfolders(side, parentPath, childrenContainer) {
            try {
                const response = await fetch(`/api/subfolders?path=${encodeURIComponent(parentPath)}`);
                const data = await response.json();
                
                // API returns "subfolders" not "folders"
                const folders = data.subfolders || data.folders || [];
                if (folders.length > 0) {
                    childrenContainer.innerHTML = folders.map(folder => {
                        const escapedPath = folder.path.replace(/"/g, '&quot;');
                        return `
                            <div class="tree-node">
                                <div class="tree-item" data-path="${escapedPath}" data-side="${side}">
                                    <span class="tree-expand">▶</span>
                                    <span class="tree-icon">📁</span>
                                    <span class="tree-label">${folder.name}</span>
                                </div>
                                <div class="tree-children collapsed"></div>
                            </div>
                        `;
                    }).join('');
                } else {
                    childrenContainer.innerHTML = '<div class="tree-loading">No subfolders</div>';
                }
            } catch (e) {
                console.error('Failed to load subfolders:', e);
                childrenContainer.innerHTML = '<div class="tree-loading">Error</div>';
            }
        }
        
        function setCompareRunMode(mode) {
            compareRunMode = mode;
            const previewBtn = document.getElementById('modePreviewBtn');
            const liveBtn = document.getElementById('modeLiveBtn');
            const modeDesc = document.getElementById('modeDescription');
            const previewActions = document.getElementById('previewModeActions');
            const liveActions = document.getElementById('liveModeActions');
            const startBtn = document.getElementById('compareStartBtn');
            const arrowLabel = document.getElementById('arrowActionLabel');
            const arrowBtn = document.getElementById('swapFoldersBtn');
            
            // Reset both buttons first
            previewBtn.classList.remove('active-preview');
            liveBtn.classList.remove('active-live');
            
            if (mode === 'preview') {
                previewBtn.classList.add('active-preview');
                modeDesc.textContent = 'Safe mode - shows what would happen without making changes';
                modeDesc.style.color = 'var(--accent-green)';
                modeDesc.classList.remove('danger-text-flash');
                if (previewActions) previewActions.style.display = 'flex';
                if (liveActions) liveActions.style.display = 'none';
                startBtn.innerHTML = '🔍 Scan & Compare Folders';
                startBtn.classList.remove('btn-danger');
                startBtn.classList.add('btn-primary');
                // Update arrow button and label for preview mode (green)
                if (arrowBtn) arrowBtn.classList.remove('live-mode');
                if (arrowLabel) {
                    arrowLabel.textContent = 'Compare LEFT → RIGHT';
                    arrowLabel.style.color = 'var(--accent-green)';
                }
            } else {
                liveBtn.classList.add('active-live');
                modeDesc.innerHTML = '<strong>⚠️ DANGER:</strong> Files will be permanently deleted!';
                modeDesc.style.color = '';  // Let CSS animation control color
                modeDesc.classList.add('danger-text-flash');
                if (previewActions) previewActions.style.display = 'none';
                if (liveActions) liveActions.style.display = 'flex';
                startBtn.innerHTML = '⚡ Scan & Delete Files';
                startBtn.classList.remove('btn-primary');
                startBtn.classList.add('btn-danger');
                // Update arrow button and label for live mode (red)
                if (arrowBtn) arrowBtn.classList.add('live-mode');
                if (arrowLabel) {
                    arrowLabel.textContent = '🗑️ Delete from LEFT';
                    arrowLabel.style.color = 'var(--accent-red)';
                }
            }
        }
        
        function setCompareMode(side, mode) {
            if (side === 'left') {
                compareLeftMode = mode;
                document.getElementById('leftModeDropbox').classList.toggle('active', mode === 'dropbox');
                document.getElementById('leftModeLocal').classList.toggle('active', mode === 'local');
                document.getElementById('leftDropboxPath').style.display = mode === 'dropbox' ? 'block' : 'none';
                document.getElementById('leftLocalPath').style.display = mode === 'local' ? 'block' : 'none';
            } else {
                compareRightMode = mode;
                document.getElementById('rightModeDropbox').classList.toggle('active', mode === 'dropbox');
                document.getElementById('rightModeLocal').classList.toggle('active', mode === 'local');
                document.getElementById('rightDropboxPath').style.display = mode === 'dropbox' ? 'block' : 'none';
                document.getElementById('rightLocalPath').style.display = mode === 'local' ? 'block' : 'none';
            }
            // Update the action summary when mode changes
            updateActionSummary();
        }
        
        function updateActionSummary() {
            // Get current paths based on modes
            const leftPath = compareLeftMode === 'dropbox' 
                ? document.getElementById('leftFolderPath').value.trim()
                : document.getElementById('leftLocalFolderPath').value.trim();
            const rightPath = compareRightMode === 'dropbox'
                ? document.getElementById('rightFolderPath').value.trim()
                : document.getElementById('rightLocalFolderPath').value.trim();
            
            // Update summary banner
            const deleteEl = document.getElementById('summaryDeletePath');
            const preserveEl = document.getElementById('summaryPreservePath');
            
            const leftDisplay = leftPath ? (leftPath || '/ (Root)') : '(select LEFT folder)';
            const rightDisplay = rightPath ? (rightPath || '/ (Root)') : '(select RIGHT folder)';
            
            deleteEl.textContent = leftDisplay;
            deleteEl.title = leftPath || '';  // Tooltip for full path
            preserveEl.textContent = rightDisplay;
            preserveEl.title = rightPath || '';  // Tooltip for full path
        }
        
        // Add event listeners for local path inputs (tree selection updates summary via code)
        const leftLocalInput = document.getElementById('leftLocalFolderPath');
        if (leftLocalInput) leftLocalInput.addEventListener('input', updateActionSummary);
        
        const rightLocalInput = document.getElementById('rightLocalFolderPath');
        if (rightLocalInput) rightLocalInput.addEventListener('input', updateActionSummary);
        
        function swapFolders() {
            // Animate the swap button
            const swapBtn = document.getElementById('swapFoldersBtn');
            swapBtn.style.transform = 'rotate(180deg)';
            setTimeout(() => { swapBtn.style.transform = ''; }, 300);
            
            // Get current values
            const leftDropboxPath = document.getElementById('leftFolderPath').value;
            const leftLocalPath = document.getElementById('leftLocalFolderPath').value;
            const rightDropboxPath = document.getElementById('rightFolderPath').value;
            const rightLocalPath = document.getElementById('rightLocalFolderPath').value;
            
            // Get display values
            const leftDisplay = document.getElementById('leftSelectedPath')?.textContent || '';
            const rightDisplay = document.getElementById('rightSelectedPath')?.textContent || '';
            
            // Swap the modes
            const tempMode = compareLeftMode;
            compareLeftMode = compareRightMode;
            compareRightMode = tempMode;
            
            // Update mode buttons for LEFT
            document.getElementById('leftModeDropbox').classList.toggle('active', compareLeftMode === 'dropbox');
            document.getElementById('leftModeLocal').classList.toggle('active', compareLeftMode === 'local');
            document.getElementById('leftDropboxPath').style.display = compareLeftMode === 'dropbox' ? 'block' : 'none';
            document.getElementById('leftLocalPath').style.display = compareLeftMode === 'local' ? 'block' : 'none';
            
            // Update mode buttons for RIGHT
            document.getElementById('rightModeDropbox').classList.toggle('active', compareRightMode === 'dropbox');
            document.getElementById('rightModeLocal').classList.toggle('active', compareRightMode === 'local');
            document.getElementById('rightDropboxPath').style.display = compareRightMode === 'dropbox' ? 'block' : 'none';
            document.getElementById('rightLocalPath').style.display = compareRightMode === 'local' ? 'block' : 'none';
            
            // Swap the path values (hidden inputs)
            document.getElementById('leftFolderPath').value = rightDropboxPath;
            document.getElementById('leftLocalFolderPath').value = rightLocalPath;
            document.getElementById('rightFolderPath').value = leftDropboxPath;
            document.getElementById('rightLocalFolderPath').value = leftLocalPath;
            
            // Swap the display values
            if (document.getElementById('leftSelectedPath')) {
                document.getElementById('leftSelectedPath').textContent = rightDisplay;
            }
            if (document.getElementById('rightSelectedPath')) {
                document.getElementById('rightSelectedPath').textContent = leftDisplay;
            }
            
            // Update the action summary
            updateActionSummary();
            
            showToast('Folders swapped! LEFT ↔ RIGHT', 'success');
        }
        
        async function startComparison() {
            // Get paths based on modes
            const leftPath = compareLeftMode === 'dropbox' 
                ? document.getElementById('leftFolderPath').value.trim()
                : document.getElementById('leftLocalFolderPath').value.trim();
            const rightPath = compareRightMode === 'dropbox'
                ? document.getElementById('rightFolderPath').value.trim()
                : document.getElementById('rightLocalFolderPath').value.trim();
            
            if (!leftPath) {
                showToast('Please enter a LEFT folder path', 'error');
                return;
            }
            if (!rightPath) {
                showToast('Please enter a RIGHT folder path', 'error');
                return;
            }
            
            // Show progress card
            document.getElementById('compareProgressCard').style.display = 'block';
            document.getElementById('compareResultsCard').style.display = 'none';
            document.getElementById('compareStartBtn').disabled = true;
            document.getElementById('compareCancelBtn').style.display = 'inline-flex';
            
            try {
                const response = await fetch('/api/compare/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        left_path: leftPath,
                        right_path: rightPath,
                        left_mode: compareLeftMode,
                        right_mode: compareRightMode
                    })
                });
                
                if (response.ok) {
                    showToast('Comparison started', 'success');
                    // Start polling for progress
                    if (comparePollInterval) clearInterval(comparePollInterval);
                    comparePollInterval = setInterval(pollCompareStatus, 500);
                } else {
                    showToast('Failed to start comparison', 'error');
                    document.getElementById('compareStartBtn').disabled = false;
                    document.getElementById('compareCancelBtn').style.display = 'none';
                }
            } catch (e) {
                console.error('Failed to start comparison:', e);
                showToast('Failed to start comparison', 'error');
                document.getElementById('compareStartBtn').disabled = false;
                document.getElementById('compareCancelBtn').style.display = 'none';
            }
        }
        
        // Update execution stats display with detailed progress
        function updateExecutionStatsDisplay(stats) {
            console.log('Updating stats display:', stats);
            
            let container = document.getElementById('executionStatsContainer');
            
            // Create container if it doesn't exist
            if (!container) {
                console.log('Creating stats container...');
                const progressCard = document.getElementById('compareProgressCard');
                if (!progressCard) {
                    console.error('Progress card not found!');
                    return;
                }
                
                // Find or create a place for the container
                let progressSection = progressCard.querySelector('.progress-section');
                if (!progressSection) {
                    progressSection = progressCard;
                }
                
                container = document.createElement('div');
                container.id = 'executionStatsContainer';
                container.className = 'glass-panel';
                container.style.cssText = `
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 12px;
                    margin: 20px 0;
                    padding: 20px;
                    background: var(--bg-card);
                    border-radius: var(--radius-md);
                    border: 1px solid var(--border-glass);
                    backdrop-filter: var(--glass-blur);
                    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
                `;
                
                // Insert after progress bar
                const progressContainer = document.querySelector('.progress-bar-container');
                if (progressContainer) {
                    progressContainer.parentNode.insertBefore(container, progressContainer.nextSibling);
                } else {
                    progressSection.appendChild(container);
                }
            }
            
            container.style.display = 'grid';
            
            const showBytes = stats.bytes_total > 0;
            const bytePercent = showBytes ? Math.round((stats.bytes_current / stats.bytes_total) * 100) : 0;
            const byteRateStr = showBytes ? formatFileSize(stats.bytes_rate) + '/s' : stats.rate + '/s';
            
            container.innerHTML = `
                <div class="stat-box" style="text-align: center; padding: 12px; background: rgba(248,113,113,0.1); border-radius: 8px; border: 1px solid rgba(248,113,113,0.2);">
                    <div style="font-size: 1.8em; font-weight: bold; color: var(--accent-red); transition: all 0.3s;">🗑️ ${stats.deleted}</div>
                    <div style="font-size: 0.7em; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-top: 4px;">Deleted</div>
                </div>
                <div class="stat-box" style="text-align: center; padding: 12px; background: rgba(52,211,153,0.1); border-radius: 8px; border: 1px solid rgba(52,211,153,0.2);">
                    <div style="font-size: 1.8em; font-weight: bold; color: var(--accent-green);">📋 ${stats.copied}</div>
                    <div style="font-size: 0.7em; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-top: 4px;">Copied</div>
                </div>
                <div class="stat-box" style="text-align: center; padding: 12px; background: rgba(251,146,60,0.1); border-radius: 8px; border: 1px solid rgba(251,146,60,0.2); position: relative;">
                    ${showBytes ? `
                        <div style="font-size: 1.2em; font-weight: bold; color: var(--accent-orange);">${formatFileSize(stats.bytes_current)}</div>
                        <div style="font-size: 0.7em; color: var(--text-muted); opacity: 0.7;">of ${formatFileSize(stats.bytes_total)}</div>
                        <div style="font-size: 0.7em; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-top: 4px;">Transferred</div>
                    ` : `
                        <div style="font-size: 1.8em; font-weight: bold; color: var(--accent-orange);">⏳ ${stats.remaining}</div>
                        <div style="font-size: 0.7em; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-top: 4px;">Left</div>
                    `}
                </div>
                <div class="stat-box" style="text-align: center; padding: 12px; background: rgba(34,211,238,0.1); border-radius: 8px; border: 1px solid rgba(34,211,238,0.2);">
                    <div style="font-size: 1.5em; font-weight: bold; color: var(--accent-cyan); animation: pulseGlow 2s infinite;">⚡ ${byteRateStr}</div>
                    <div style="font-size: 0.7em; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-top: 4px;">${stats.etaStr}</div>
                </div>
            `;
        }
        
        function hideExecutionStatsDisplay() {
            const container = document.getElementById('executionStatsContainer');
            if (container) {
                container.style.display = 'none';
            }
        }

        async function startExperimentalSync() {
            if (!confirm("Start Experimental Sync Mode? This will synchronize Local Folder -> Dropbox using the new engine.")) return;
            
            try {
                const btn = document.getElementById('syncBtn');
                btn.disabled = true;
                btn.innerHTML = '♻️ Syncing...';
                
                const response = await fetch('/api/sync/start', {
                    method: 'POST',
                    body: JSON.stringify({}),
                    headers: {'Content-Type': 'application/json'}
                });
                const data = await response.json();
                
                if (data.status === 'started') {
                    showToast('Sync Engine Started (Check Logs)', 'success');
                } else {
                    showToast('Failed: ' + data.message, 'error');
                    btn.disabled = false;
                    btn.innerHTML = '♻️ Sync (Experimental)';
                }
            } catch (e) {
                console.error(e);
                showToast('API Error', 'error');
            }
        }
        
        // Track last log length to only append new entries
        let lastLogLength = 0;
        
        function updateExecutionLog(logEntries) {
            console.log('Updating execution log, entries:', logEntries ? logEntries.length : 0);
            
            if (!logEntries || logEntries.length === 0) {
                console.log('No log entries to display');
                return;
            }
            
            let logContainer = document.getElementById('executionLogContainer');
            let logContent = document.getElementById('executionLogContent');
            
            // Create container dynamically if it doesn't exist
            if (!logContainer) {
                console.log('Creating execution log container dynamically');
                const progressCard = document.getElementById('compareProgressCard');
                if (!progressCard) return;
                
                logContainer = document.createElement('div');
                logContainer.id = 'executionLogContainer';
                logContainer.style.cssText = 'margin-top: 16px; display: block;';
                logContainer.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="color: var(--accent-cyan);">📋</span>
                        <span style="font-size: 0.9em; font-weight: bold; color: var(--text-primary);">Live Execution Log</span>
                    </div>
                    <div id="executionLogContent" style="
                        background: rgba(0, 0, 0, 0.5);
                        border: 1px solid var(--accent-red);
                        border-radius: 8px;
                        padding: 12px;
                        max-height: 200px;
                        overflow-y: auto;
                        font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
                        font-size: 0.85em;
                        line-height: 1.6;
                    "></div>
                `;
                
                // Find progress section and append
                const progressSection = progressCard.querySelector('.progress-section') || progressCard;
                progressSection.appendChild(logContainer);
                logContent = document.getElementById('executionLogContent');
            }
            
            if (!logContent) {
                console.error('Could not find or create log content element');
                return;
            }
            
            // Show the log container
            logContainer.style.display = 'block';
            
            // Only append new entries
            if (logEntries.length > lastLogLength) {
                const newEntries = logEntries.slice(lastLogLength);
                console.log('Adding', newEntries.length, 'new log entries');
                
                for (const entry of newEntries) {
                    const div = document.createElement('div');
                    div.className = 'log-entry';
                    div.style.padding = '2px 0';
                    div.textContent = entry;
                    
                    // Color-code based on content
                    if (entry.includes('✅') || entry.includes('🎉')) {
                        div.style.color = '#22c55e';  // Green
                    } else if (entry.includes('⚠️') || entry.includes('❌') || entry.includes('FAIL')) {
                        div.style.color = '#ef4444';  // Red
                    } else if (entry.includes('🚀') || entry.includes('⚡') || entry.includes('🛡️')) {
                        div.style.color = '#00d4ff';  // Cyan
                    } else if (entry.includes('📦') || entry.includes('⏳')) {
                        div.style.color = '#f97316';  // Orange
                    } else if (entry.includes('📋') || entry.includes('🗑️')) {
                        div.style.color = '#a78bfa';  // Purple
                    }
                    
                    logContent.appendChild(div);
                }
                lastLogLength = logEntries.length;
                
                // Auto-scroll to bottom
                logContent.scrollTop = logContent.scrollHeight;
            }
        }
        
        function resetExecutionLog() {
            const logContent = document.getElementById('executionLogContent');
            if (logContent) {
                logContent.innerHTML = '';
            }
            lastLogLength = 0;
        }
        
        // Track folder deletion log separately
        let lastFolderLogLength = 0;
        
        function updateFolderDeletionLog(logEntries) {
            let logContainer = document.getElementById('folderDeletionLogContainer');
            let logContent = document.getElementById('folderDeletionLogContent');
            
            // Create container if it doesn't exist
            if (!logContainer) {
                const progressCard = document.getElementById('progressCard');
                if (!progressCard) return;
                
                logContainer = document.createElement('div');
                logContainer.id = 'folderDeletionLogContainer';
                logContainer.style.cssText = 'margin-top: 16px; display: block;';
                logContainer.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="color: var(--accent-cyan);">📋</span>
                        <span style="font-size: 0.9em; font-weight: bold; color: var(--text-primary);">Live Deletion Log</span>
                    </div>
                    <div id="folderDeletionLogContent" style="
                        background: rgba(0, 0, 0, 0.4);
                        border: 1px solid var(--border-color);
                        border-radius: 8px;
                        padding: 12px;
                        max-height: 200px;
                        overflow-y: auto;
                        font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
                        font-size: 0.8em;
                        line-height: 1.6;
                    "></div>
                `;
                progressCard.querySelector('.progress-section').appendChild(logContainer);
                logContent = document.getElementById('folderDeletionLogContent');
            }
            
            if (!logContent) return;
            
            // Show the container
            logContainer.style.display = 'block';
            
            // Only append new entries
            if (logEntries.length > lastFolderLogLength) {
                const newEntries = logEntries.slice(lastFolderLogLength);
                for (const entry of newEntries) {
                    const div = document.createElement('div');
                    div.className = 'log-entry';
                    div.textContent = entry;
                    
                    // Color-code based on content
                    if (entry.includes('✅') || entry.includes('🎉')) {
                        div.style.color = 'var(--accent-green)';
                    } else if (entry.includes('⚠️') || entry.includes('❌') || entry.includes('FAIL-SAFE')) {
                        div.style.color = 'var(--accent-red)';
                    } else if (entry.includes('🚀') || entry.includes('⚡') || entry.includes('🛡️')) {
                        div.style.color = 'var(--accent-cyan)';
                    } else if (entry.includes('📦') || entry.includes('⏳')) {
                        div.style.color = 'var(--accent-orange)';
                    }
                    
                    logContent.appendChild(div);
                }
                lastFolderLogLength = logEntries.length;
                
                // Auto-scroll to bottom
                logContent.scrollTop = logContent.scrollHeight;
            }
        }
        
        function resetFolderDeletionLog() {
            const logContent = document.getElementById('folderDeletionLogContent');
            if (logContent) {
                logContent.innerHTML = '';
            }
            lastFolderLogLength = 0;
        }
        
        async function pollCompareStatus() {
            try {
                const response = await fetch('/api/compare/status', {method: 'POST'});
                const data = await response.json();
                
                const progress = data.progress;
                const executing = data.executing;
                const execProgress = data.execute_progress;
                
                // Update progress UI
                document.getElementById('compareLeftCount').textContent = formatNumber(progress.left_files);
                document.getElementById('compareRightCount').textContent = formatNumber(progress.right_files);
                
                const elapsed = progress.elapsed || 0;
                const mins = Math.floor(elapsed / 60);
                const secs = Math.floor(elapsed % 60);
                document.getElementById('compareElapsed').textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
                
                // Update title based on status
                const titles = {
                    'scanning_left': 'Scanning LEFT folder...',
                    'scanning_right': 'Scanning RIGHT folder...',
                    'comparing': `Comparing files... (${formatNumber(progress.compared)}/${formatNumber(progress.total)})`,
                    'done': 'Comparison Complete!',
                    'error': 'Error occurred',
                    'cancelled': 'Comparison Cancelled'
                };
                document.getElementById('compareProgressTitle').textContent = titles[progress.status] || 'Processing...';
                
                if (progress.current_file) {
                    document.getElementById('compareCurrentFile').textContent = progress.current_file;
                }
                
                // Update progress bar
                const progressFill = document.getElementById('compareProgressFill');
                if (progress.status === 'comparing' && progress.total > 0) {
                    progressFill.classList.remove('indeterminate');
                    progressFill.style.width = `${(progress.compared / progress.total) * 100}%`;
                } else if (progress.status === 'done') {
                    progressFill.classList.remove('indeterminate');
                    progressFill.style.width = '100%';
                }
                
                // Handle completion
                if (progress.status === 'done' || progress.status === 'error' || progress.status === 'cancelled') {
                    clearInterval(comparePollInterval);
                    comparePollInterval = null;
                    
                    document.getElementById('compareProgressSpinner').style.display = 'none';
                    document.getElementById('compareStartBtn').disabled = false;
                    document.getElementById('compareCancelBtn').style.display = 'none';
                    
                    const statusBadge = document.getElementById('compareProgressStatus');
                    if (progress.status === 'done') {
                        statusBadge.className = 'status-badge status-connected';
                        statusBadge.innerHTML = '<span class="status-dot"></span> Done';
                        // Load and display results
                        await loadCompareResults();
                    } else if (progress.status === 'error') {
                        statusBadge.className = 'status-badge status-disconnected';
                        statusBadge.innerHTML = '<span class="status-dot"></span> Error';
                        showToast('Comparison failed', 'error');
                    } else {
                        statusBadge.className = 'status-badge status-disconnected';
                        statusBadge.innerHTML = '<span class="status-dot"></span> Cancelled';
                    }
                }
                
                // Handle execution progress - this is the key part
                console.log('Execution status:', execProgress.status, 'executing:', executing);
                
                if (executing || execProgress.status === 'executing') {
                    console.log('=== UPDATING EXECUTION PROGRESS ===');
                    console.log('execProgress:', JSON.stringify(execProgress));
                    
                    const deleted = execProgress.deleted || 0;
                    const copied = execProgress.copied || 0;
                    const skipped = execProgress.skipped || 0;
                    const total = execProgress.total || 0;
                    const current = execProgress.current || 0;
                    const remaining = Math.max(0, total - current);
                    const percent = total > 0 ? Math.round((current / total) * 100) : 0;
                    
                    // Calculate rate
                    const startTime = execProgress.start_time || Date.now() / 1000;
                    const elapsed = (Date.now() / 1000) - startTime;
                    const rate = elapsed > 0 ? (current / elapsed).toFixed(1) : 0;
                    const eta = rate > 0 ? Math.round(remaining / rate) : 0;
                    const etaStr = eta > 60 ? `${Math.floor(eta/60)}m ${eta%60}s` : `${eta}s`;
                    
                    // Update title with detailed progress
                    const actionType = execProgress.copied > 0 && execProgress.deleted === 0 ? 'Copying' : 
                                     execProgress.deleted > 0 && execProgress.copied === 0 ? 'Deleting' : 'Processing';
                    document.getElementById('compareProgressTitle').innerHTML = 
                        `⚡ <strong>${actionType} Files...</strong> ${percent}%`;
                    
                    // Show detailed current file
                    const currentFile = execProgress.current_file || '';
                    document.getElementById('compareCurrentFile').innerHTML = currentFile ? 
                        `<span style="color: var(--accent-cyan);">📄</span> ${currentFile}` : '';
                    
                    // Update progress bar
                    if (total > 0) {
                        const progressFill = document.getElementById('compareProgressFill');
                        progressFill.classList.remove('indeterminate');
                        progressFill.style.width = `${percent}%`;
                    }
                    
                    // Update execution stats display
                    updateExecutionStatsDisplay({
                        deleted, copied, skipped, total, current, remaining, rate, etaStr, percent,
                        bytes_total: execProgress.bytes_total || 0,
                        bytes_current: execProgress.bytes_current || 0,
                        bytes_rate: execProgress.bytes_rate || 0
                    });
                    
                    // Update streaming log
                    updateExecutionLog(execProgress.log || []);
                }
                
                if (execProgress.status === 'done') {
                    clearInterval(comparePollInterval);
                    comparePollInterval = null;
                    
                    document.getElementById('compareProgressSpinner').style.display = 'none';
                    document.getElementById('compareExecuteBtn').disabled = false;
                    
                    // Final log update
                    updateExecutionLog(execProgress.log || []);
                    
                    // Show appropriate message based on results
                    if (execProgress.message) {
                        showToast(execProgress.message, 'info');
                    } else if (execProgress.deleted === 0 && execProgress.copied === 0) {
                        showToast('No files were deleted or copied - nothing matched the criteria', 'info');
                    } else {
                        showToast(`✅ Completed: ${execProgress.deleted} deleted, ${execProgress.copied} copied`, 'success');
                    }
                    
                    if (execProgress.errors && execProgress.errors.length > 0) {
                        showToast(`${execProgress.errors.length} errors occurred`, 'error');
                    }
                }
                
                if (execProgress.status === 'cancelled') {
                    clearInterval(comparePollInterval);
                    comparePollInterval = null;
                    document.getElementById('compareProgressSpinner').style.display = 'none';
                    showToast('Execution cancelled', 'info');
                    updateExecutionLog(execProgress.log || []);
                }
                
            } catch (e) {
                console.error('Failed to poll compare status:', e);
            }
        }
        
        async function loadCompareResults() {
            try {
                const response = await fetch('/api/compare/results', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ max_items: 500 })
                });
                compareResults = await response.json();
                
                // Update summary
                const summary = compareResults.summary || {};
                document.getElementById('summaryDeleteCount').textContent = formatNumber(summary.to_delete_count || 0);
                document.getElementById('summaryDeleteSize').textContent = formatSize(summary.to_delete_size || 0);
                document.getElementById('summaryCopyCount').textContent = formatNumber(summary.to_copy_count || 0);
                document.getElementById('summaryCopySize').textContent = formatSize(summary.to_copy_size || 0);
                document.getElementById('summaryLeftOnlyCount').textContent = formatNumber(summary.left_only_count || 0);
                document.getElementById('summaryRightOnlyCount').textContent = formatNumber(summary.right_only_count || 0);
                
                // Update badges
                document.getElementById('deleteBadge').textContent = formatNumber(summary.to_delete_count || 0);
                document.getElementById('copyBadge').textContent = formatNumber(summary.to_copy_count || 0);
                document.getElementById('leftOnlyBadge').textContent = formatNumber(summary.left_only_count || 0);
                
                // Show results card
                document.getElementById('compareResultsCard').style.display = 'block';
                
                // Enable/disable execute button based on results
                const hasActions = (summary.to_delete_count || 0) > 0 || (summary.to_copy_count || 0) > 0;
                const executeBtn = document.getElementById('compareExecuteBtn');
                executeBtn.disabled = !hasActions;
                
                // Show message if no actions available
                if (!hasActions) {
                    executeBtn.textContent = '✅ No Actions Required';
                    executeBtn.title = 'No files found that need to be deleted or copied';
                    showToast('No duplicates found - nothing to delete!', 'info');
                } else {
                    executeBtn.textContent = '🗑️ Execute Deletions Now';
                    executeBtn.title = `Delete ${summary.to_delete_count || 0} files, copy ${summary.to_copy_count || 0} files`;
                }
                
                // Render initial view
                switchCompareView('delete');
                
            } catch (e) {
                console.error('Failed to load compare results:', e);
                showToast('Failed to load results', 'error');
            }
        }
        
        function switchCompareView(view) {
            currentCompareView = view;
            
            // Update tab buttons
            document.getElementById('viewDeleteBtn').classList.toggle('active', view === 'delete');
            document.getElementById('viewCopyBtn').classList.toggle('active', view === 'copy');
            document.getElementById('viewLeftOnlyBtn').classList.toggle('active', view === 'leftonly');
            
            // Render the list
            renderCompareResults(view);
        }
        
        function renderCompareResults(view) {
            const container = document.getElementById('compareResultsList');
            if (!compareResults) {
                container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No results to display</p>';
                return;
            }
            
            let items = [];
            let itemType = '';
            
            if (view === 'delete') {
                items = compareResults.to_delete || [];
                itemType = 'delete';
            } else if (view === 'copy') {
                items = compareResults.to_copy || [];
                itemType = 'copy';
            } else if (view === 'leftonly') {
                items = compareResults.left_only || [];
                itemType = 'leftonly';
            }
            
            if (items.length === 0) {
                container.innerHTML = `<p style="text-align: center; color: var(--text-secondary);">No ${view === 'delete' ? 'files to delete' : view === 'copy' ? 'files to copy' : 'files only in LEFT'}</p>`;
                return;
            }
            
            let html = '';
            items.forEach((item, index) => {
                const file = itemType === 'leftonly' ? item.file : item.left;
                const icon = itemType === 'delete' ? '🗑️' : itemType === 'copy' ? '📤' : '📁';
                
                html += `
                    <div class="compare-result-item ${itemType}">
                        <div class="compare-result-icon">${icon}</div>
                        <div class="compare-result-details">
                            <div class="compare-result-path">${escapeHtml(file.rel_path)}</div>
                            <div class="compare-result-meta">
                                <span>📊 ${formatSize(file.size)}</span>
                                ${file.modified ? `<span>📅 ${new Date(file.modified).toLocaleDateString()}</span>` : ''}
                                <span class="compare-result-reason">${escapeHtml(item.reason)}</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
            return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function cancelComparison() {
            try {
                await fetch('/api/compare/cancel', {method: 'POST'});
                showToast('Cancelling comparison...', 'info');
            } catch (e) {
                console.error('Failed to cancel:', e);
            }
        }
        
        async function resetComparison() {
            try {
                await fetch('/api/compare/reset', {method: 'POST'});
                document.getElementById('compareProgressCard').style.display = 'none';
                document.getElementById('compareResultsCard').style.display = 'none';
                document.getElementById('compareStartBtn').disabled = false;
                document.getElementById('compareProgressFill').className = 'progress-bar-fill indeterminate';
                document.getElementById('compareProgressFill').style.width = '';
                document.getElementById('compareProgressSpinner').style.display = 'block';
                // Reset to preview mode
                setCompareRunMode('preview');
                compareResults = null;
                showToast('Ready for new comparison', 'success');
            } catch (e) {
                console.error('Failed to reset:', e);
            }
        }
        
        function confirmCompareExecute() {
            if (compareRunMode !== 'live') {
                showToast('Please switch to Live Mode first', 'error');
                return;
            }
            
            const summary = compareResults?.summary || {};
            const deleteCount = summary.to_delete_count || 0;
            const copyCount = summary.to_copy_count || 0;
            const deleteSize = formatSize(summary.to_delete_size || 0);
            const copySize = formatSize(summary.to_copy_size || 0);
            
            // Get the actual folder paths
            const leftPath = compareLeftMode === 'dropbox' 
                ? document.getElementById('leftFolderPath').value.trim()
                : document.getElementById('leftLocalFolderPath').value.trim();
            
            const message = `🚨 FINAL WARNING - PERMANENT DELETION 🚨\n\n` +
                `You are about to DELETE files from:\n` +
                `📁 ${leftPath}\n\n` +
                `Actions:\n` +
                `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
                `🗑️ DELETE: ${deleteCount} file(s) (${deleteSize})\n` +
                `📤 COPY:   ${copyCount} file(s) (${copySize})\n` +
                `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
                `⚠️ DELETIONS CANNOT BE UNDONE!\n` +
                `(Dropbox trash keeps files for 30 days)\n\n` +
                `Type "DELETE" to confirm:`;
            
            const userInput = prompt(message);
            if (userInput === 'DELETE') {
                executeCompareActions();
            } else if (userInput !== null) {
                showToast('Deletion cancelled - you must type DELETE exactly', 'info');
            }
        }
        
        async function executeCompareActions() {
            console.log('=== STARTING EXECUTION ===');
            
            // Disable button and show progress
            document.getElementById('compareExecuteBtn').disabled = true;
            
            // Make progress card very visible
            const progressCard = document.getElementById('compareProgressCard');
            progressCard.style.display = 'block';
            progressCard.style.border = '2px solid var(--accent-red)';
            progressCard.style.boxShadow = '0 0 20px rgba(239, 68, 68, 0.3)';
            progressCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Update title and spinner
            document.getElementById('compareProgressSpinner').style.display = 'block';
            document.getElementById('compareProgressTitle').innerHTML = '⚡ <strong style="color: var(--accent-red);">EXECUTING DELETIONS...</strong>';
            document.getElementById('compareCurrentFile').textContent = 'Initializing...';
            
            // Update status badge
            const statusBadge = document.getElementById('compareProgressStatus');
            statusBadge.className = 'status-badge status-scanning';
            statusBadge.innerHTML = '<span class="status-dot"></span> Executing';
            
            // Reset progress bar
            const progressFill = document.getElementById('compareProgressFill');
            progressFill.classList.remove('indeterminate');
            progressFill.style.width = '0%';
            progressFill.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
            
            // Reset and show execution log
            resetExecutionLog();
            const logContainer = document.getElementById('executionLogContainer');
            if (logContainer) {
                logContainer.style.display = 'block';
            }
            
            // Hide stats container initially (will be created by updateExecutionStatsDisplay)
            hideExecutionStatsDisplay();
            
            try {
                console.log('Calling /api/compare/execute...');
                const response = await fetch('/api/compare/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})  // Execute all
                });
                
                console.log('Response status:', response.status);
                
                if (response.ok) {
                    showToast('⚡ Fast execution started!', 'success');
                    
                    // Start fast polling for progress
                    if (comparePollInterval) clearInterval(comparePollInterval);
                    comparePollInterval = setInterval(pollCompareStatus, 200);  // Very fast updates
                    
                    // Also do an immediate poll
                    setTimeout(pollCompareStatus, 100);
                } else {
                    showToast('Failed to start execution', 'error');
                    document.getElementById('compareExecuteBtn').disabled = false;
                    progressCard.style.border = '';
                    progressCard.style.boxShadow = '';
                }
            } catch (e) {
                console.error('Failed to execute:', e);
                showToast('Failed to execute: ' + e.message, 'error');
                document.getElementById('compareExecuteBtn').disabled = false;
                progressCard.style.border = '';
                progressCard.style.boxShadow = '';
            }
        }
        
        function exportCompareResults(format) {
            if (!compareResults) {
                showToast('No results to export', 'error');
                return;
            }
            
            const dataStr = JSON.stringify(compareResults, null, 2);
            const blob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `folder_comparison_${new Date().toISOString().slice(0,10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
        }
        
        // =====================================================================
        // END FOLDER COMPARISON FUNCTIONS
        // =====================================================================
        
        // Apply local path
        async function applyLocalPath() {
            const localPath = document.getElementById('inlineLocalPath').value.trim();
            
            if (!localPath) {
                showToast('Please enter a path', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ mode: 'local', local_path: localPath })
                });
                
                if (response.ok) {
                    showToast('Path applied: ' + localPath, 'success');
                    
                    // Clear and reload folder tree
                    loadedFolders.clear();
                    await loadRootFolders();
                    
                    // Update status
                    fetchStatus();
                } else {
                    showToast('Failed to apply path', 'error');
                }
            } catch (e) {
                console.error('Failed to apply path:', e);
                showToast('Failed to apply path', 'error');
            }
        }
        
        let currentConfig = {};
        
        function showSettings() {
            // Populate settings from current config
            fetch('/api/config')
                .then(r => r.json())
                .then(config => {
                    currentConfig = config;
                    document.getElementById('settingsIgnoreSystem').checked = config.ignore_system_files !== false;
                    loadSystemFilesFromConfig(config.system_files || defaultSystemFiles);
                    document.getElementById('excludePatternsList').value = (config.exclude_patterns || []).join('\n');
                    document.getElementById('settingsPort').value = config.port || 8765;
                    document.getElementById('settingsExportFormat').value = config.export_format || 'json';
                    
                    // Schedule settings
                    const schedule = config.schedule || {};
                    document.getElementById('settingsScheduleEnabled').checked = schedule.enabled || false;
                    document.getElementById('settingsScheduleInterval').value = schedule.interval_hours || 24;
                    toggleScheduleOptions();
                    
                    document.getElementById('settingsModal').classList.add('active');
                })
                .catch(e => {
                    console.error('Failed to load config:', e);
                    alert('Failed to load settings');
                });
        }
        
        function closeSettings() {
            document.getElementById('settingsModal').classList.remove('active');
        }
        
        function toggleScheduleOptions() {
            const enabled = document.getElementById('settingsScheduleEnabled').checked;
            document.getElementById('scheduleOptions').style.display = enabled ? 'block' : 'none';
        }
        
        // Toggle between Dropbox, Local, and Google mode UI
function toggleModeUI() {
    const mode = document.querySelector('input[name="operatingMode"]:checked').value;
    const localPathSettings = document.getElementById('localPathSettings');
    const dropboxSettings = document.getElementById('dropboxSettingsSection');
    const googleSettings = document.getElementById('googleSettingsSection');
    
    // Reset all
    localPathSettings.style.display = 'none';
    dropboxSettings.style.display = 'none';
    if(googleSettings) googleSettings.style.display = 'none';
    
    if (mode === 'local') {
        localPathSettings.style.display = 'block';
    } else if (mode === 'dropbox') {
        dropboxSettings.style.display = 'block';
    } else if (mode === 'google') {
        if(googleSettings) googleSettings.style.display = 'block';
    }
    
    // Update active style
    document.querySelectorAll('.mode-option').forEach(opt => {
        opt.style.borderColor = 'var(--border-color)';
        opt.style.background = 'transparent';
    });
    const activeOption = document.querySelector('input[name="operatingMode"]:checked').parentElement;
    activeOption.style.borderColor = 'var(--accent-cyan)';
    activeOption.style.background = 'rgba(0, 200, 255, 0.1)';
}

async function connectGoogle() {
    try {
        const btn = document.querySelector('#googleSettingsSection button');
        const originalText = btn.textContent;
        btn.textContent = 'Connecting...';
        btn.disabled = true;
        
        const response = await fetch('/api/google/connect', { 
            method: 'POST',
            body: JSON.stringify({}),
            headers: {'Content-Type': 'application/json'} 
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            showToast('Connected to Google Drive', 'success');
            document.getElementById('settingsGoogleStatus').querySelector('.status-indicator').className = 'status-indicator connected';
            document.getElementById('settingsGoogleAccount').textContent = 'Connected';
        } else {
            showToast('Failed: ' + (data.message || 'Unknown error'), 'error');
        }
        
        btn.textContent = originalText;
        btn.disabled = false;
    } catch (e) {
        console.error('Google connect error:', e);
        showToast('Connection failed', 'error');
    }
}
        
        async function saveSettings() {
            // Get mode
            const mode = document.querySelector('input[name="operatingMode"]:checked').value;
            const localPath = document.getElementById('settingsLocalPath').value;
            
            const newConfig = {
                mode: mode,
                local_path: localPath,
                ignore_system_files: document.getElementById('settingsIgnoreSystem').checked,
                system_files: getEnabledSystemFiles(),
                exclude_patterns: document.getElementById('excludePatternsList').value
                    .split('\n')
                    .map(l => l.trim())
                    .filter(l => l.length > 0),
                port: parseInt(document.getElementById('settingsPort').value) || 8765,
                export_format: document.getElementById('settingsExportFormat').value,
                schedule: {
                    enabled: document.getElementById('settingsScheduleEnabled').checked,
                    interval_hours: parseInt(document.getElementById('settingsScheduleInterval').value) || 24,
                    last_run: (currentConfig.schedule ? currentConfig.schedule.last_run : 0)
                }
            };
            
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(newConfig)
                });
                
                if (response.ok) {
                    closeSettings();
                    // Update main toggle
                    document.getElementById('ignoreSystemFiles').checked = newConfig.ignore_system_files;
                    // Update mode indicator in UI
                    updateModeIndicator(mode, localPath);
                    // Refresh folder tree for new mode
                    loadedFolders.clear();
                    await loadRootFolders();
                    showToast('Settings saved successfully! Mode: ' + (mode === 'local' ? 'Local Filesystem' : 'Dropbox API'), 'success');
                } else {
                    showToast('Failed to save settings', 'error');
                }
            } catch (e) {
                console.error('Failed to save settings:', e);
                showToast('Failed to save settings', 'error');
            }
        }
        
        // Default system files list
        const defaultSystemFiles = [
            '.DS_Store', 'Thumbs.db', 'desktop.ini', '.dropbox', 
            '.dropbox.attr', 'Icon', 'Icon\\r', '.localized',
            '*.alias', '*.lnk', '*.symlink'
        ];
        
        // Current system files (enabled ones)
        let currentSystemFiles = new Set();
        // All known patterns (for checkbox display)
        let allSystemFilePatterns = new Set(defaultSystemFiles);
        
        function renderSystemFileCheckboxes() {
            const container = document.getElementById('systemFilesCheckboxes');
            const patterns = Array.from(allSystemFilePatterns).sort((a, b) => {
                // Sort: exact names first, then wildcards
                const aWild = a.includes('*');
                const bWild = b.includes('*');
                if (aWild !== bWild) return aWild ? 1 : -1;
                return a.localeCompare(b);
            });
            
            container.innerHTML = patterns.map(pattern => {
                const id = 'sysfile_' + pattern.replace(/[^a-zA-Z0-9]/g, '_');
                const isWildcard = pattern.includes('*') || pattern.includes('?');
                const checked = currentSystemFiles.has(pattern) ? 'checked' : '';
                return `
                    <div class="checkbox-item ${isWildcard ? 'is-wildcard' : ''}">
                        <input type="checkbox" id="${id}" value="${pattern}" ${checked} onchange="toggleSystemFile('${pattern}', this.checked)">
                        <label for="${id}" title="${pattern}">${pattern}</label>
                    </div>
                `;
            }).join('');
        }
        
        function toggleSystemFile(pattern, enabled) {
            if (enabled) {
                currentSystemFiles.add(pattern);
            } else {
                currentSystemFiles.delete(pattern);
            }
        }
        
        function addCustomSystemFile() {
            const input = document.getElementById('customSystemFile');
            const pattern = input.value.trim();
            if (pattern && !allSystemFilePatterns.has(pattern)) {
                allSystemFilePatterns.add(pattern);
                currentSystemFiles.add(pattern);
                renderSystemFileCheckboxes();
                input.value = '';
            } else if (allSystemFilePatterns.has(pattern)) {
                // Pattern exists, just enable it
                currentSystemFiles.add(pattern);
                renderSystemFileCheckboxes();
                input.value = '';
            }
        }
        
        function loadSystemFilesFromConfig(systemFiles) {
            // Add any new patterns from config to our known patterns
            systemFiles.forEach(f => allSystemFilePatterns.add(f));
            // Set current enabled files
            currentSystemFiles = new Set(systemFiles);
            renderSystemFileCheckboxes();
        }
        
        function getEnabledSystemFiles() {
            return Array.from(currentSystemFiles);
        }
        
        function resetSettings() {
            if (confirm('Reset all settings to defaults?')) {
                document.getElementById('settingsIgnoreSystem').checked = true;
                allSystemFilePatterns = new Set(defaultSystemFiles);
                currentSystemFiles = new Set(defaultSystemFiles);
                renderSystemFileCheckboxes();
                document.getElementById('excludePatternsList').value = '.git\\nnode_modules\\n__pycache__\\n.venv\\n.env';
                document.getElementById('settingsPort').value = '8765';
                document.getElementById('settingsExportFormat').value = 'json';
            }
        }
        
        function showToast(message, type) {
            // Create toast element
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            document.body.appendChild(toast);
            
            // Animate in
            setTimeout(() => toast.classList.add('show'), 10);
            
            // Remove after delay
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
        
        function togglePassword(inputId) {
            const input = document.getElementById(inputId);
            input.type = input.type === 'password' ? 'text' : 'password';
        }
        
        async function loadCredentials() {
            try {
                // Load credentials
                const credResponse = await fetch('/api/credentials');
                const credData = await credResponse.json();
                document.getElementById('settingsAppKey').value = credData.app_key || '';
                document.getElementById('settingsAppSecret').value = credData.app_secret || '';
                document.getElementById('settingsRefreshToken').value = credData.refresh_token || '';
                
                // Update connection status in settings
                const statusEl = document.getElementById('settingsConnectionStatus');
                const indicator = statusEl.querySelector('.status-indicator');
                const info = document.getElementById('settingsAccountInfo');
                
                if (credData.connected) {
                    indicator.className = 'status-indicator connected';
                    info.textContent = `Connected as ${credData.account_name}`;
                } else {
                    indicator.className = 'status-indicator disconnected';
                    info.textContent = 'Not connected';
                }
                
                // Also load config
                const configResponse = await fetch('/api/config');
                const config = await configResponse.json();
                document.getElementById('settingsIgnoreSystem').checked = config.ignore_system_files !== false;
                loadSystemFilesFromConfig(config.system_files || defaultSystemFiles);
                document.getElementById('excludePatternsList').value = (config.exclude_patterns || []).join('\\n');
                document.getElementById('settingsPort').value = config.port || 8765;
                document.getElementById('settingsExportFormat').value = config.export_format || 'json';
                
            } catch (e) {
                console.error('Failed to load credentials/config:', e);
            }
        }
        
        function startAuth() {
            const appKey = document.getElementById('settingsAppKey').value.trim();
            const appSecret = document.getElementById('settingsAppSecret').value.trim();
            
            if (!appKey || !appSecret) {
                showToast('Please enter App Key and App Secret first', 'error');
                return;
            }
            
            document.getElementById('authModal').classList.add('active');
        }
        
        function closeAuth() {
            document.getElementById('authModal').classList.remove('active');
            document.getElementById('authCode').value = '';
        }
        
        function openAuthUrl() {
            const appKey = document.getElementById('settingsAppKey').value.trim();
            const authUrl = `https://www.dropbox.com/oauth2/authorize?client_id=${appKey}&response_type=code&token_access_type=offline`;
            window.open(authUrl, '_blank');
        }
        
        async function exchangeCode() {
            const appKey = document.getElementById('settingsAppKey').value.trim();
            const appSecret = document.getElementById('settingsAppSecret').value.trim();
            const code = document.getElementById('authCode').value.trim();
            
            if (!code) {
                showToast('Please enter the authorization code', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/auth/exchange', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({app_key: appKey, app_secret: appSecret, code: code})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('settingsRefreshToken').value = data.refresh_token;
                    closeAuth();
                    showToast('Authorization successful! Click Save Settings to apply.', 'success');
                } else {
                    showToast(`Authorization failed: ${data.error}`, 'error');
                }
            } catch (e) {
                console.error('Exchange failed:', e);
                showToast('Authorization failed. Check console for details.', 'error');
            }
        }
        
        async function testConnection() {
            const appKey = document.getElementById('settingsAppKey').value.trim();
            const appSecret = document.getElementById('settingsAppSecret').value.trim();
            const refreshToken = document.getElementById('settingsRefreshToken').value.trim();
            
            if (!appKey || !appSecret || !refreshToken) {
                showToast('Please enter all credentials first', 'error');
                return;
            }
            
            showToast('Testing connection...', 'info');
            
            try {
                const response = await fetch('/api/auth/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({app_key: appKey, app_secret: appSecret, refresh_token: refreshToken})
                });
                
                const data = await response.json();
                
                const indicator = document.querySelector('#settingsConnectionStatus .status-indicator');
                const info = document.getElementById('settingsAccountInfo');
                
                if (data.success) {
                    indicator.className = 'status-indicator connected';
                    info.textContent = `Connected as ${data.account_name}`;
                    showToast(`Connected as ${data.account_name}!`, 'success');
                } else {
                    indicator.className = 'status-indicator disconnected';
                    info.textContent = 'Connection failed';
                    showToast(`Connection failed: ${data.error}`, 'error');
                }
            } catch (e) {
                console.error('Test failed:', e);
                showToast('Connection test failed', 'error');
            }
        }
        
        // Override showSettings to also load credentials
        const originalShowSettings = showSettings;
        showSettings = async function() {
            try {
                await loadCredentials();
                // Show settings modal directly instead of calling original
                document.getElementById('settingsModal').classList.add('active');
            } catch (e) {
                console.error('Error opening settings:', e);
                // Still show the modal even if credentials fail to load
                document.getElementById('settingsModal').classList.add('active');
            }
        };
        
        // Override saveSettings to also save credentials
        const originalSaveSettings = saveSettings;
        saveSettings = async function() {
            // Save credentials
            const credentials = {
                app_key: document.getElementById('settingsAppKey').value.trim(),
                app_secret: document.getElementById('settingsAppSecret').value.trim(),
                refresh_token: document.getElementById('settingsRefreshToken').value.trim()
            };
            
            try {
                await fetch('/api/credentials', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(credentials)
                });
            } catch (e) {
                console.error('Failed to save credentials:', e);
            }
            
            // Call original save
            await originalSaveSettings();
        };
        
        // Setup Wizard Functions
        let currentWizardStep = 1;
        
        function showSetupWizard() {
            currentWizardStep = 1;
            updateWizardStep(1);
            document.getElementById('setupWizard').classList.add('active');
        }
        
        function closeWizard() {
            document.getElementById('setupWizard').classList.remove('active');
            // Refresh the page to update connection status
            location.reload();
        }
        
        function updateWizardStep(step) {
            // Hide all content
            for (let i = 1; i <= 4; i++) {
                const content = document.getElementById(`wizStep${i}`);
                const indicator = document.getElementById(`wizStep${i}Indicator`);
                if (content) content.style.display = 'none';
                if (indicator) {
                    indicator.classList.remove('active', 'completed');
                    if (i < step) indicator.classList.add('completed');
                    if (i === step) indicator.classList.add('active');
                }
            }
            document.getElementById('wizStepSuccess').style.display = 'none';
            
            // Show current step
            const currentContent = document.getElementById(`wizStep${step}`);
            if (currentContent) currentContent.style.display = 'block';
            
            currentWizardStep = step;
        }
        
        function wizardNext(step) {
            updateWizardStep(step);
        }
        
        function wizardBack(step) {
            updateWizardStep(step);
        }
        
        function wizardValidateAndNext() {
            const appKey = document.getElementById('wizardAppKey').value.trim();
            const appSecret = document.getElementById('wizardAppSecret').value.trim();
            
            if (!appKey) {
                showToast('Please enter your App Key', 'error');
                document.getElementById('wizardAppKey').focus();
                return;
            }
            
            if (!appSecret) {
                showToast('Please enter your App Secret', 'error');
                document.getElementById('wizardAppSecret').focus();
                return;
            }
            
            if (appKey.length < 10) {
                showToast('App Key seems too short. Please check and try again.', 'error');
                return;
            }
            
            if (appSecret.length < 10) {
                showToast('App Secret seems too short. Please check and try again.', 'error');
                return;
            }
            
            wizardNext(4);
        }
        
        function wizardOpenAuth() {
            const appKey = document.getElementById('wizardAppKey').value.trim();
            if (!appKey) {
                showToast('Please go back and enter your App Key first', 'error');
                return;
            }
            const authUrl = `https://www.dropbox.com/oauth2/authorize?client_id=${appKey}&response_type=code&token_access_type=offline`;
            window.open(authUrl, '_blank');
        }
        
        async function wizardComplete() {
            const appKey = document.getElementById('wizardAppKey').value.trim();
            const appSecret = document.getElementById('wizardAppSecret').value.trim();
            const code = document.getElementById('wizardAuthCode').value.trim();
            
            if (!code) {
                showToast('Please enter the authorization code from Dropbox', 'error');
                document.getElementById('wizardAuthCode').focus();
                return;
            }
            
            showToast('Completing setup...', 'info');
            
            try {
                // Exchange code for token
                const exchangeResponse = await fetch('/api/auth/exchange', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({app_key: appKey, app_secret: appSecret, code: code})
                });
                
                const exchangeData = await exchangeResponse.json();
                
                if (!exchangeData.success) {
                    showToast(`Authorization failed: ${exchangeData.error}`, 'error');
                    return;
                }
                
                // Save credentials
                await fetch('/api/credentials', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        app_key: appKey,
                        app_secret: appSecret,
                        refresh_token: exchangeData.refresh_token
                    })
                });
                
                // Test connection to get account name
                const testResponse = await fetch('/api/auth/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        app_key: appKey,
                        app_secret: appSecret,
                        refresh_token: exchangeData.refresh_token
                    })
                });
                
                const testData = await testResponse.json();
                
                if (testData.success) {
                    // Show success
                    document.getElementById('wizardSuccessAccount').textContent = `Connected as: ${testData.account_name}`;
                    
                    // Mark all steps completed
                    for (let i = 1; i <= 4; i++) {
                        document.getElementById(`wizStep${i}Indicator`).classList.add('completed');
                        document.getElementById(`wizStep${i}Indicator`).classList.remove('active');
                    }
                    
                    // Hide all steps and show success
                    for (let i = 1; i <= 4; i++) {
                        document.getElementById(`wizStep${i}`).style.display = 'none';
                    }
                    document.getElementById('wizStepSuccess').style.display = 'block';
                    
                    showToast('Setup complete!', 'success');
                } else {
                    showToast(`Connection test failed: ${testData.error}`, 'error');
                }
            } catch (e) {
                console.error('Wizard error:', e);
                showToast('Setup failed. Please check your credentials and try again.', 'error');
            }
        }
        
        // Check if setup is needed on page load
        async function checkSetupNeeded() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                // Only show setup wizard if in Dropbox mode and not connected
                const mode = data.config?.mode || 'dropbox';
                if (mode === 'dropbox' && !data.connected) {
                    // Show setup wizard after a short delay
                    setTimeout(() => {
                        showSetupWizard();
                    }, 1000);
                }
            } catch (e) {
                console.error('Failed to check status:', e);
            }
        }
        
        // Disclaimer functions
        function showDisclaimer() {
            document.getElementById('disclaimerModal').classList.add('active');
        }
        
        function acceptDisclaimer() {
            localStorage.setItem('disclaimerAccepted', 'true');
            localStorage.setItem('disclaimerDate', new Date().toISOString());
            document.getElementById('disclaimerModal').classList.remove('active');
        }
        
        function checkDisclaimerAccepted() {
            const accepted = localStorage.getItem('disclaimerAccepted');
            if (!accepted) {
                // Show disclaimer on first visit
                setTimeout(() => {
                    showDisclaimer();
                }, 500);
            }
        }
        
        // Update mode indicator in main UI (now handled by toggle buttons)
        function updateModeIndicator(mode, localPath) {
            // Mode is now shown via toggle buttons, no separate badge needed
            // This function is kept for backwards compatibility with saveSettings
            console.log('Mode indicator updated:', mode, localPath);
        }
        
        // Direct function to open settings modal - defined before event listeners
        window.openSettingsModal = async function() {
            console.log('Opening settings modal...');
            try {
                // Load credentials
                const credResponse = await fetch('/api/credentials');
                const credData = await credResponse.json();
                console.log('Credentials loaded:', credData.connected);
                
                document.getElementById('settingsAppKey').value = credData.app_key || '';
                document.getElementById('settingsAppSecret').value = credData.app_secret || '';
                document.getElementById('settingsRefreshToken').value = credData.refresh_token || '';
                
                // Update connection status in settings
                const statusEl = document.getElementById('settingsConnectionStatus');
                if (statusEl) {
                    const indicator = statusEl.querySelector('.status-indicator');
                    const info = document.getElementById('settingsAccountInfo');
                    
                    if (credData.connected) {
                        indicator.className = 'status-indicator connected';
                        info.textContent = 'Connected as ' + credData.account_name;
                    } else {
                        indicator.className = 'status-indicator disconnected';
                        info.textContent = 'Not connected';
                    }
                }
                
                // Load config
                const configResponse = await fetch('/api/config');
                const config = await configResponse.json();
                console.log('Config loaded:', config);
                
                // Set mode radio buttons
                const mode = config.mode || 'dropbox';
                if (mode === 'dropbox') {
                    document.getElementById('modeDropbox').checked = true;
                } else if (mode === 'google') {
                    document.getElementById('modeGoogle').checked = true;
                } else {
                    document.getElementById('modeLocal').checked = true;
                }
                document.getElementById('settingsLocalPath').value = config.local_path || '';
                toggleModeUI(); // Update UI based on mode
                
                document.getElementById('settingsIgnoreSystem').checked = config.ignore_system_files !== false;
                loadSystemFilesFromConfig(config.system_files || defaultSystemFiles);
                document.getElementById('excludePatternsList').value = (config.exclude_patterns || []).join('\\n');
                document.getElementById('settingsPort').value = config.port || 8765;
                document.getElementById('settingsExportFormat').value = config.export_format || 'json';
                
            } catch (e) {
                console.error('Error loading settings data:', e);
            }
            
            // Show the modal
            console.log('Showing settings modal');
            document.getElementById('settingsModal').classList.add('active');
        };
        
        // Add event listeners for navigation buttons
        document.getElementById('settingsNavBtn').addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Settings nav button clicked');
            window.openSettingsModal();
        });
        
        document.getElementById('helpNavBtn').addEventListener('click', function(e) {
            e.preventDefault();
            showHelp();
        });
        
        document.getElementById('disclaimerNavBtn').addEventListener('click', function(e) {
            e.preventDefault();
            showDisclaimer();
        });
        
        // Also add listener for inline settings button
        document.getElementById('inlineSettingsBtn').addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Inline settings button clicked');
            window.openSettingsModal();
        });
        
        // Start polling
        console.log('=== STARTING INITIALIZATION ===');
        try {
            fetchStatus();
            console.log('fetchStatus() called successfully');
        } catch(e) {
            console.error('Error calling fetchStatus:', e);
        }
        
        // Adaptive polling - faster during active operations
        let lastOperationState = { scanning: false, deleting: false };
        function adaptivePolling() {
            const isActive = lastOperationState.scanning || lastOperationState.deleting;
            const interval = isActive ? 200 : 500;  // 200ms during operations, 500ms idle
            
            clearInterval(pollInterval);
            pollInterval = setInterval(async () => {
                await fetchStatus();
                // Check if we need to adjust polling rate
                const nowActive = appState.scanning || appState.deleting;
                if (nowActive !== (lastOperationState.scanning || lastOperationState.deleting)) {
                    lastOperationState = { scanning: appState.scanning, deleting: appState.deleting };
                    adaptivePolling();  // Adjust rate
                }
            }, interval);
        }
        
        pollInterval = setInterval(fetchStatus, 500);
        console.log('Poll interval set (adaptive)');
        
        // Load folder tree
        console.log('Initializing - calling loadRootFolders...');
        loadRootFolders().then(() => {
            console.log('Root folders loaded successfully');
        }).catch(e => {
            console.error('Failed to load root folders on init:', e);
        });
        
        // Check if setup is needed
        checkSetupNeeded();
        
        // Check if disclaimer needs to be shown
        checkDisclaimerAccepted();
