// Global variables
let selectedFile = null;
let processedData = null;

// DOM elements
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const fileSize = document.getElementById('file-size');
const processBtn = document.getElementById('process-btn');
const loading = document.getElementById('loading');
const errorMessage = document.getElementById('error-message');
const successMessage = document.getElementById('success-message');
const resultsSection = document.getElementById('results-section');
const modal = document.getElementById('modal');

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
});

function setupEventListeners() {
    // Upload area click
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    
    // Process button
    processBtn.addEventListener('click', processFile);
    
    // Export buttons
    document.getElementById('export-csv').addEventListener('click', () => exportData('csv'));
    document.getElementById('export-json').addEventListener('click', () => exportData('json'));
    
    // Raw text toggle
    document.getElementById('show-raw').addEventListener('click', showRawText);
    document.getElementById('hide-raw').addEventListener('click', hideRawText);
    
    // Modal
    document.querySelector('.close').addEventListener('click', closeModal);
    document.getElementById('modal-cancel').addEventListener('click', closeModal);
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        document.addEventListener(eventName, preventDefaults, false);
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDragOver(e) {
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFile(file) {
    // Validate file type
    const validTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
        showError('Please upload a PDF or image file (PNG, JPG, JPEG)');
        return;
    }
    
    // Validate file size (16MB max)
    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('File size must be less than 16MB');
        return;
    }
    
    selectedFile = file;
    displayFileInfo(file);
    processBtn.style.display = 'block';
    hideMessages();
}

function displayFileInfo(file) {
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.classList.add('show');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

async function processFile() {
    if (!selectedFile) {
        showError('Please select a file first');
        return;
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    // Show loading state
    processBtn.disabled = true;
    loading.classList.add('show');
    hideMessages();
    resultsSection.classList.remove('show');
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            processedData = data;
            displayResults(data);
            showSuccess('File processed successfully!');
        } else {
            showError(data.error || 'Failed to process file');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('An error occurred while processing the file');
    } finally {
        processBtn.disabled = false;
        loading.classList.remove('show');
    }
}

function displayResults(data) {
    // Display account information
    const accountInfoGrid = document.getElementById('account-info-grid');
    accountInfoGrid.innerHTML = '';
    
    if (data.account_info && Object.keys(data.account_info).length > 0) {
        for (const [key, value] of Object.entries(data.account_info)) {
            const infoItem = createInfoItem(formatLabel(key), value);
            accountInfoGrid.appendChild(infoItem);
        }
    } else {
        accountInfoGrid.innerHTML = '<p style="color: #666;">No account information extracted</p>';
    }
    
    // Display transaction count
    document.getElementById('transaction-count').textContent = data.transaction_count || 0;
    
    // Display transactions
    const tbody = document.getElementById('transactions-tbody');
    tbody.innerHTML = '';
    
    if (data.transactions && data.transactions.length > 0) {
        data.transactions.forEach((transaction, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${transaction.date || '-'}</td>
                <td>${transaction.description || '-'}</td>
                <td>${transaction.amount || '-'}</td>
            `;
            tbody.appendChild(row);
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #666;">No transactions found</td></tr>';
    }
    
    // Store raw text preview
    if (data.raw_text_preview) {
        document.getElementById('raw-text-preview').textContent = data.raw_text_preview;
    }
    
    // Show results section
    resultsSection.classList.add('show');
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function createInfoItem(label, value) {
    const div = document.createElement('div');
    div.className = 'info-item';
    div.innerHTML = `
        <div class="info-label">${label}</div>
        <div class="info-value">${value || 'N/A'}</div>
    `;
    return div;
}

function formatLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

async function exportData(format) {
    if (!processedData) {
        showError('No data to export');
        return;
    }
    
    try {
        const response = await fetch(`/export/${format}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(processedData)
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bank_statement_${format}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showSuccess(`Data exported as ${format.toUpperCase()} successfully!`);
        } else {
            showError('Failed to export data');
        }
    } catch (error) {
        console.error('Export error:', error);
        showError('An error occurred while exporting data');
    }
}

function showRawText() {
    const rawTextCard = document.getElementById('raw-text-card');
    rawTextCard.style.display = 'block';
    rawTextCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function hideRawText() {
    document.getElementById('raw-text-card').style.display = 'none';
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
    successMessage.classList.remove('show');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorMessage.classList.remove('show');
    }, 5000);
}

function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.classList.add('show');
    errorMessage.classList.remove('show');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        successMessage.classList.remove('show');
    }, 5000);
}

function hideMessages() {
    errorMessage.classList.remove('show');
    successMessage.classList.remove('show');
}

function showModal(title, message, onConfirm) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').textContent = message;
    modal.style.display = 'block';
    
    // Set up confirm button
    const confirmBtn = document.getElementById('modal-confirm');
    confirmBtn.onclick = function() {
        if (onConfirm) onConfirm();
        closeModal();
    };
}

function closeModal() {
    modal.style.display = 'none';
}

// Window click event to close modal
window.onclick = function(event) {
    if (event.target === modal) {
        closeModal();
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Escape key to close modal
    if (e.key === 'Escape' && modal.style.display === 'block') {
        closeModal();
    }
    
    // Ctrl/Cmd + O to open file dialog
    if ((e.ctrlKey || e.metaKey) && e.key === 'o') {
        e.preventDefault();
        fileInput.click();
    }
    
    // Ctrl/Cmd + Enter to process file
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && selectedFile && !processBtn.disabled) {
        e.preventDefault();
        processFile();
    }
});

// Auto-cleanup old files periodically
setInterval(async function() {
    try {
        await fetch('/cleanup', { method: 'POST' });
    } catch (error) {
        console.log('Cleanup failed:', error);
    }
}, 3600000); // Run every hour

// Page visibility API to pause/resume operations
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden, could pause any ongoing operations
        console.log('Page hidden');
    } else {
        // Page is visible again
        console.log('Page visible');
    }
});

// Print functionality
function printResults() {
    if (!processedData || !processedData.transactions) {
        showError('No data to print');
        return;
    }
    
    window.print();
}

// Add print button functionality if needed
function addPrintButton() {
    const exportButtons = document.querySelector('.export-buttons');
    const printBtn = document.createElement('button');
    printBtn.className = 'export-btn';
    printBtn.textContent = 'Print Results';
    printBtn.onclick = printResults;
    exportButtons.appendChild(printBtn);
}

// Helper function to format currency
function formatCurrency(amount) {
    if (typeof amount === 'string') {
        amount = parseFloat(amount.replace(/,/g, ''));
    }
    if (isNaN(amount)) return '-';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

// Helper function to format date
function formatDate(dateString) {
    if (!dateString) return '-';
    
    // Try to parse various date formats
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
        // If parsing fails, return original string
        return dateString;
    }
    
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Advanced search/filter functionality
function addSearchFilter() {
    const searchContainer = document.createElement('div');
    searchContainer.className = 'search-container';
    searchContainer.innerHTML = `
        <input type="text" id="transaction-search" placeholder="Search transactions..." class="search-input">
        <button id="clear-search" class="clear-btn">Clear</button>
    `;
    
    const transactionsTable = document.getElementById('transactions-table');
    transactionsTable.parentNode.insertBefore(searchContainer, transactionsTable);
    
    const searchInput = document.getElementById('transaction-search');
    const clearBtn = document.getElementById('clear-search');
    
    searchInput.addEventListener('input', filterTransactions);
    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        filterTransactions();
    });
}

function filterTransactions() {
    const searchTerm = document.getElementById('transaction-search').value.toLowerCase();
    const rows = document.querySelectorAll('#transactions-tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
    
    // Update count
    const visibleRows = document.querySelectorAll('#transactions-tbody tr:not([style*="display: none"])');
    const countText = `${visibleRows.length} of ${rows.length} transactions`;
    
    // Update or create filtered count display
    let filteredCount = document.getElementById('filtered-count');
    if (!filteredCount) {
        filteredCount = document.createElement('span');
        filteredCount.id = 'filtered-count';
        filteredCount.style.marginLeft = '10px';
        filteredCount.style.color = '#666';
        document.getElementById('transaction-count').parentNode.appendChild(filteredCount);
    }
    
    if (searchTerm) {
        filteredCount.textContent = ` (Showing ${countText})`;
    } else {
        filteredCount.textContent = '';
    }
}

// Initialize additional features when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add print button
    addPrintButton();
    
    // Add search functionality after results are displayed
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.target.classList && mutation.target.classList.contains('show')) {
                if (!document.getElementById('transaction-search')) {
                    addSearchFilter();
                }
            }
        });
    });
    
    observer.observe(resultsSection, {
        attributes: true,
        attributeFilter: ['class']
    });
});

// Error handling for network issues
window.addEventListener('online', function() {
    console.log('Connection restored');
    hideMessages();
});

window.addEventListener('offline', function() {
    showError('No internet connection. Please check your network.');
});

// Performance monitoring
function measurePerformance() {
    if (window.performance && window.performance.timing) {
        const loadTime = window.performance.timing.loadEventEnd - window.performance.timing.navigationStart;
        console.log(`Page load time: ${loadTime}ms`);
    }
}

window.addEventListener('load', measurePerformance);

// Export functions for testing or external use
window.OCRApp = {
    processFile,
    exportData,
    showError,
    showSuccess,
    formatCurrency,
    formatDate
};