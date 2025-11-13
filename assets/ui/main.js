document.addEventListener('DOMContentLoaded', () => {
    // Theme Switcher
    const themeButtons = document.querySelectorAll('.theme-btn');
    const currentTheme = localStorage.getItem('theme') || 'hacker';
    document.body.className = currentTheme + '-theme';

    themeButtons.forEach(button => {
        if (button.dataset.theme === currentTheme) {
            button.classList.add('active');
        }
        button.addEventListener('click', (e) => {
            const selectedTheme = e.currentTarget.dataset.theme;
            document.body.className = selectedTheme + '-theme';
            localStorage.setItem('theme', selectedTheme);

            // Update active state
            themeButtons.forEach(btn => btn.classList.remove('active'));
            e.currentTarget.classList.add('active');
        });
    });

    // File Search/Filter
    const searchBox = document.getElementById('search-box');
    const fileList = document.getElementById('file-list').getElementsByTagName('tbody')[0];
    const fileRows = fileList.getElementsByTagName('tr');

    searchBox.addEventListener('keyup', () => {
        const query = searchBox.value.toLowerCase();
        for (let i = 0; i < fileRows.length; i++) {
            const fileName = fileRows[i].getElementsByTagName('td')[0].textContent.toLowerCase();
            if (fileName.includes(query)) {
                fileRows[i].style.display = '';
            } else {
                fileRows[i].style.display = 'none';
            }
        }
    });

    // Copy URL to Clipboard
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', () => {
            const fileUrl = button.getAttribute('data-url');
            const fullUrl = new URL(fileUrl, window.location.href).href;
            navigator.clipboard.writeText(fullUrl).then(() => {
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                setTimeout(() => {
                    button.textContent = originalText;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy URL: ', err);
            });
        });
    });

    // File Preview Modal
    const modal = document.getElementById('preview-modal');
    const closeBtn = document.querySelector('.close-btn');
    const previewContent = document.getElementById('preview-content');
    const fileLinks = document.querySelectorAll('#file-list a');
    let currentFileUrl = ''; // Global variable to store the URL of the currently previewed file

    const previewable_extensions = {
        images: ['jpg', 'jpeg', 'png', 'gif', 'svg', 'bmp', 'webp'],
        text: ['txt', 'md', 'py', 'js', 'css', 'html', 'json', 'xml', 'sh', 'bat', 'log', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp', 'rtf', 'csv', 'mp3', 'wav', 'ogg', 'mp4', 'avi', 'mov', 'mkv', 'psd', 'crt', 'gz', 'zip', 'php', 'cpp', 'jar', 'key']
    };

    fileLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            if (link.getAttribute('href').endsWith('/')) {
                return; // It's a directory, let the browser navigate
            }
            e.preventDefault(); // It's a file, open in modal

            currentFileUrl = link.href; // Store the current file URL

            const url = new URL(link.href);
            const extension = url.pathname.split('.').pop().toLowerCase();

            const isImage = previewable_extensions.images.includes(extension);
            const isText = previewable_extensions.text.includes(extension);

            previewContent.innerHTML = ''; // Clear previous content
            const metadataContent = document.getElementById('metadata-content');
            metadataContent.innerHTML = '';
            modal.style.display = 'block';

            // Display preview if image or text
            if (isImage) {
                const img = document.createElement('img');
                img.src = link.href;
                previewContent.appendChild(img);
            } else if (isText) {
                fetch(link.href)
                    .then(response => response.text())
                    .then(text => {
                        const pre = document.createElement('pre');
                        pre.textContent = text;
                        previewContent.appendChild(pre);
                    })
                    .catch(err => {
                        console.error('Failed to fetch file content: ', err);
                        previewContent.textContent = 'Failed to load file content.';
                    });
            } else {
                // For other file types, show a message or just metadata
                previewContent.textContent = 'No visual preview available for this file type.';
            }

            // Always fetch and display metadata
            fetch(`/metadata?file=${url.pathname}`)
                .then(response => response.json())
                .then(data => {
                    const table = document.createElement('table');
                    const tbody = document.createElement('tbody');
                    for (const [key, value] of Object.entries(data)) {
                        const row = document.createElement('tr');
                        const keyCell = document.createElement('td');
                        keyCell.textContent = key;
                        const valueCell = document.createElement('td');
                        valueCell.textContent = value;
                        row.appendChild(keyCell);
                        row.appendChild(valueCell);
                        tbody.appendChild(row);
                    }
                    if (Object.keys(data).length > 0) {
                        const heading = document.createElement('h3');
                        heading.textContent = 'Metadata';
                        metadataContent.appendChild(heading);
                        table.appendChild(tbody);
                        metadataContent.appendChild(table);
                    } else {
                        metadataContent.textContent = 'No metadata found for this file.';
                    }
                })
                .catch(err => {
                    console.error('Failed to fetch metadata: ', err);
                    metadataContent.textContent = 'Failed to load metadata.';
                });
        });
    });

    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target == modal) {
            modal.style.display = 'none';
        }
    });

    // Download button functionality
    const downloadBtn = document.getElementById('download-btn');
    downloadBtn.addEventListener('click', () => {
        if (currentFileUrl) {
            const a = document.createElement('a');
            a.href = currentFileUrl;
            a.download = currentFileUrl.split('/').pop(); // Suggest filename from URL
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    });

    // Copy all button functionality
    const copyAllBtn = document.getElementById('copy-all-btn');
    copyAllBtn.addEventListener('click', () => {
        const preElement = previewContent.querySelector('pre');
        if (preElement) {
            navigator.clipboard.writeText(preElement.textContent).then(() => {
                const originalText = copyAllBtn.textContent;
                copyAllBtn.textContent = 'Copied!';
                setTimeout(() => {
                    copyAllBtn.textContent = originalText;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
            });
        }
    });

    // Log Viewer
    const logToggleBtn = document.getElementById('log-toggle-btn');
    const logViewer = document.getElementById('log-viewer');
    const logContent = document.getElementById('log-content');
    let logInterval = null;

    // Upload Viewer
    const uploadToggleBtn = document.getElementById('upload-toggle-btn');
    const uploadViewer = document.getElementById('upload-viewer');
    const dropZone = uploadViewer.querySelector('#drop-zone');
    const fileInput = uploadViewer.querySelector('#file-input');
    const uploadProgress = uploadViewer.querySelector('#upload-progress');


    const fetchLogs = () => {
        fetch('/logs')
            .then(response => response.text())
            .then(text => {
                logContent.textContent = text;
                logContent.scrollTop = logContent.scrollHeight;
            })
            .catch(err => {
                console.error('Failed to fetch logs:', err);
            });
    };

    logToggleBtn.addEventListener('click', () => {
        logViewer.classList.toggle('visible');
        if (logViewer.classList.contains('visible')) {
            fetchLogs();
            logInterval = setInterval(fetchLogs, 2000);
        } else {
            clearInterval(logInterval);
        }
    });

    // Pause/Resume log fetching on hover for scrolling
    if (logContent) {
        logContent.addEventListener('mouseenter', () => {
            if (logInterval) {
                clearInterval(logInterval);
                logInterval = null; // Clear the interval ID
            }
        });

        logContent.addEventListener('mouseleave', () => {
            if (!logInterval && logViewer.classList.contains('visible')) {
                logInterval = setInterval(fetchLogs, 2000);
            }
        });
    }

    // Log Viewer Resizing
    const logResizerHandle = document.getElementById('log-resizer-handle');
    let isResizing = false;
    let lastY = 0;
    let lastHeight = 0;

    if (logResizerHandle) {
        logResizerHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            lastY = e.clientY;
            lastHeight = logViewer.offsetHeight;
            document.addEventListener('mousemove', resizeLogViewer);
            document.addEventListener('mouseup', stopResizing);
        });
    }

    const resizeLogViewer = (e) => {
        if (!isResizing) return;
        const dy = e.clientY - lastY;
        const newHeight = Math.max(100, lastHeight - dy); // Minimum height of 100px
        logViewer.style.height = `${newHeight}px`;
        logContent.style.height = `calc(${newHeight}px - 50px)`; // Adjust log content height
    };

    const stopResizing = () => {
        isResizing = false;
        document.removeEventListener('mousemove', resizeLogViewer);
        document.removeEventListener('mouseup', stopResizing);
    };

    if (uploadToggleBtn) {
        uploadToggleBtn.addEventListener('click', () => {
            uploadViewer.classList.toggle('visible');
        });
    }

    // File Upload Logic
    if (dropZone) {
        const activeUploads = {};

        uploadProgress.addEventListener('click', (e) => {
            if (e.target.classList.contains('cancel-btn')) {
                const fileId = e.target.dataset.fileId;
                if (activeUploads[fileId]) {
                    activeUploads[fileId].abort();
                }
            }
        });

        dropZone.addEventListener('click', () => fileInput.click());

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            handleFiles(files);
        });

        fileInput.addEventListener('change', () => {
            const files = fileInput.files;
            handleFiles(files);
        });

        const handleFiles = (files) => {
            for (const file of files) {
                uploadFile(file);
            }
        };

        const uploadFile = (file) => {
            const formData = new FormData();
            formData.append('file', file);

            const sanitizedId = file.name.replace(/[^a-zA-Z0-9]/g, '');

            // Remove any existing progress container for this file to avoid duplicate IDs
            const existingContainer = document.getElementById(`progress-container-${sanitizedId}`);
            if (existingContainer) {
                existingContainer.remove();
            }

            const fileProgressContainer = document.createElement('div');
            fileProgressContainer.className = 'upload-item-container';
            fileProgressContainer.id = `progress-container-${sanitizedId}`;
            fileProgressContainer.innerHTML = `
                <div class="progress-description">
                    <span>${file.name}: <span id="progress-text-${sanitizedId}">0%</span></span>
                </div>
                <div class="progress-cancel">
                    <button class="cancel-btn" data-file-id="${sanitizedId}">Cancel</button>
                </div>
                <div class="progress-bar-background">
                    <div class="progress-bar-fill" id="progress-bar-${sanitizedId}"></div>
                </div>
            `;
            uploadProgress.appendChild(fileProgressContainer);

            const xhr = new XMLHttpRequest();
            activeUploads[sanitizedId] = xhr;

            xhr.open('POST', '/upload', true);

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    const progressBarFill = document.getElementById(`progress-bar-${sanitizedId}`);
                    const progressText = document.getElementById(`progress-text-${sanitizedId}`);
                    if (progressBarFill) {
                        progressBarFill.style.width = `${percentComplete.toFixed(0)}%`;
                    }
                    if (progressText) {
                        progressText.textContent = `${percentComplete.toFixed(0)}%`;
                    }
                }
            };

            xhr.onload = () => {
                const fileProgressContainer = document.getElementById(`progress-container-${sanitizedId}`);
                if (fileProgressContainer) {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        // Success
                        fileProgressContainer.innerHTML = `<p class="success-message">${xhr.responseText}</p>`;
                        setTimeout(() => {
                            location.reload();
                        }, 2000); // Reload after 2 seconds
                    } else {
                        // Error
                        let errorMessage = `Error uploading '${file.name}'. Status: ${xhr.status}`;
                        if (xhr.responseText) {
                            errorMessage += ` - ${xhr.responseText}`;
                        }
                        fileProgressContainer.innerHTML = `<p class="error-message">${errorMessage}</p>`;
                    }
                }
                delete activeUploads[sanitizedId];
            };

            xhr.onerror = () => {
                const fileProgressContainer = document.getElementById(`progress-container-${sanitizedId}`);
                if (fileProgressContainer) {
                    fileProgressContainer.innerHTML = `<p class="error-message">Network error uploading file '${file.name}'.</p>`;
                }
                delete activeUploads[sanitizedId];
            };

            xhr.onabort = () => {
                const fileProgressContainer = document.getElementById(`progress-container-${sanitizedId}`);
                if (fileProgressContainer) {
                    fileProgressContainer.innerHTML = `<p class="info-message">Upload of '${file.name}' was canceled.</p>`;
                }
                delete activeUploads[sanitizedId];
            };

            xhr.send(formData);
        };
    }
});

