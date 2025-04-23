document.addEventListener('DOMContentLoaded', function() {
    // Handle the file upload form validation
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(event) {
            const fileInput = document.getElementById('menu_pdf');
            const hotelNameInput = document.getElementById('hotel_name');
            
            if (!fileInput.files.length) {
                event.preventDefault();
                showAlert('Please select a PDF file.');
                return;
            }
            
            const file = fileInput.files[0];
            
            // Check if the file is a PDF
            if (!file.type.includes('pdf')) {
                event.preventDefault();
                showAlert('Please upload a PDF file only.');
                return;
            }
            
            // Check file size (max 16MB)
            const maxSize = 16 * 1024 * 1024; // 16MB in bytes
            if (file.size > maxSize) {
                event.preventDefault();
                showAlert('File size exceeds 16MB. Please upload a smaller file.');
                return;
            }
            
            // Validate hotel name
            if (!hotelNameInput.value.trim()) {
                event.preventDefault();
                showAlert('Please enter a hotel name.');
                return;
            }
            
            // Show loading indicator
            addLoadingIndicator();
        });
    }
    
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length) {
        setTimeout(() => {
            flashMessages.forEach(message => {
                message.style.opacity = '0';
                setTimeout(() => {
                    message.style.display = 'none';
                }, 500);
            });
        }, 5000);
    }
    
    // Function to show custom alerts
    function showAlert(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'flash-message';
        alertDiv.textContent = message;
        
        const messagesContainer = document.querySelector('.flash-messages');
        if (messagesContainer) {
            messagesContainer.appendChild(alertDiv);
        } else {
            const newContainer = document.createElement('div');
            newContainer.className = 'flash-messages';
            newContainer.appendChild(alertDiv);
            
            const main = document.querySelector('main');
            main.insertBefore(newContainer, main.firstChild);
        }
        
        // Auto-hide the alert after 5 seconds
        setTimeout(() => {
            alertDiv.style.opacity = '0';
            setTimeout(() => {
                alertDiv.remove();
            }, 500);
        }, 5000);
    }
    
    // Function to add loading indicator
    function addLoadingIndicator() {
        const submitButton = document.querySelector('.btn-primary');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = 'Processing... <span class="spinner"></span>';
            submitButton.classList.add('loading');
        }
    }
});