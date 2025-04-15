document.addEventListener('DOMContentLoaded', function() {
    // Get form elements
    const reportForm = document.querySelector('form');
    const videoUrlInput = document.querySelector('input[name="video_url"]');
    const reportCategorySelect = document.querySelector('select[name="report_category"]');
    
    if (reportForm) {
        reportForm.addEventListener('submit', function(event) {
            // Reset any previous validation styles
            videoUrlInput.style.borderColor = '';
            reportCategorySelect.style.borderColor = '';
            
            let isValid = true;
            
            // Validate video URL
            if (!validateVideoUrl()) {
                isValid = false;
                videoUrlInput.style.borderColor = 'red';
            }
            
            // Validate report category
            if (!validateReportCategory()) {
                isValid = false;
                reportCategorySelect.style.borderColor = 'red';
            }
            
            if (!isValid) {
                event.preventDefault();
                alert('Please fix the highlighted fields before submitting.');
            }
        });
    }
    
    function validateVideoUrl() {
        const videoUrl = videoUrlInput.value.trim();
        
        if (!videoUrl) {
            return false;
        }
        
        // Check if URL contains youtube.com or youtu.be
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[a-zA-Z0-9_-]{11}(?:\S+)?$/;
        return youtubeRegex.test(videoUrl);
    }
    
    function validateReportCategory() {
        return reportCategorySelect.value !== '';
    }
});