// frontend/js/script.js
// (Ensure this file is correctly linked from your HTML file)

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Ready - Initializing Frontend Logic");

    // --- Configuration ---
    const BACKEND_URL = 'http://127.0.0.1:5000'; // IMPORTANT: Ensure this matches your running Flask backend URL/Port

    // --- Select UI Elements ---
    const audioFileInput = document.getElementById('audioFile');
    const summaryTypeSelect = document.getElementById('summaryType'); // Keep if needed later
    const generateButton = document.getElementById('generateReport');
    const reportOutputDiv = document.getElementById('report-output'); // Make sure <div id="report-output"> exists in your HTML
    const textPromptInput = document.getElementById('textPrompt'); // Get text prompt input
    const submitPromptButton = document.getElementById('submitPrompt'); // Get submit prompt button

    // --- Dynamically Create or Find Status Div ---
    let processingStatusDiv = document.getElementById('processing-status');
    if (!processingStatusDiv) {
        processingStatusDiv = document.createElement('div');
        processingStatusDiv.id = 'processing-status';
        processingStatusDiv.style.marginTop = '15px';
        processingStatusDiv.style.fontStyle = 'italic';
        processingStatusDiv.style.color = '#e1e1ff'; // Default status color
        processingStatusDiv.style.textAlign = 'center';
        processingStatusDiv.style.minHeight = '1.2em'; // Prevent layout shift
        // Try inserting after generate button's parent group, fallback to appending to card
        if (generateButton && generateButton.closest('.form-group') && generateButton.closest('.form-group').parentNode) {
             generateButton.closest('.form-group').parentNode.insertBefore(processingStatusDiv, generateButton.closest('.form-group').nextSibling);
        } else if (document.querySelector('.card')) {
            document.querySelector('.card').appendChild(processingStatusDiv);
             console.warn("Generate button or its parent group not found, appended status div to card.");
        } else {
            document.body.appendChild(processingStatusDiv); // Absolute fallback
             console.warn("Card container not found, appended status div to body.");
        }
    }
     // --- Ensure report output div exists ---
     if (!reportOutputDiv) {
          console.error("CRITICAL: Report output div (#report-output) not found in HTML!");
     }
     // --- Ensure other necessary elements exist ---
     if (!audioFileInput) console.error("CRITICAL: Audio file input (#audioFile) not found!");
     if (!generateButton) console.error("CRITICAL: Generate button (#generateReport) not found!");
     if (!textPromptInput) console.warn("Text prompt input (#textPrompt) not found.");
     if (!submitPromptButton) console.warn("Submit prompt button (#submitPrompt) not found.");


    // Variable to hold the polling interval ID
    let pollingIntervalId = null;
    const POLLING_INTERVAL_MS = 4000; // Check status every 4 seconds (adjust as needed)

    // --- Attach Event Listeners ---
    if (generateButton) {
        generateButton.addEventListener('click', handleGenerateReportClick);
    }
    if (submitPromptButton) {
          submitPromptButton.addEventListener('click', handleSubmitPromptClick);
          submitPromptButton.disabled = true; // Initially disabled
     }

    // --- Core Functions ---

    async function handleGenerateReportClick() {
        console.log("Generate Report button clicked.");
        // Safety checks
        if (!reportOutputDiv || !processingStatusDiv || !audioFileInput || !generateButton) {
             console.error("One or more essential UI elements are missing.");
             alert("Initialization error. Required elements not found on page.");
             return;
        }

        processingStatusDiv.textContent = 'Starting...';
        processingStatusDiv.style.color = '#e1e1ff';
        reportOutputDiv.innerHTML = '<p><i>Processing request...</i></p>'; // Clear previous & show indicator

        // 1. Get File Input
        const file = audioFileInput.files[0];
        if (!file) {
            displayError("Please select an audio file first.");
            return;
        }

        // 2. Get Other Options (Example)
        const whisperModelSize = 'small'; // Hardcode or get from UI

        // 3. Create FormData
        const formData = new FormData();
        formData.append('audioFile', file);
        formData.append('whisperModelSize', whisperModelSize);

        // 4. Clear previous polling
        if (pollingIntervalId) {
            clearInterval(pollingIntervalId);
            pollingIntervalId = null;
        }

        // 5. Send POST request to Backend
        processingStatusDiv.textContent = 'Uploading and processing audio... (This may take some time)';
        generateButton.disabled = true;
        if (submitPromptButton) submitPromptButton.disabled = true;

        try {
            console.log(`Sending POST request to ${BACKEND_URL}/process_audio`);
            const response = await fetch(`${BACKEND_URL}/process_audio`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                let errorMsg = `Upload failed! Status: ${response.status}`;
                try { const errResult = await response.json(); errorMsg = errResult.error || `Upload failed! Status: ${response.status}`; } catch (e) {
                    console.warn("Could not parse error response as JSON.");
                    const textError = await response.text(); if(textError) errorMsg += ` - ${textError}`;
                }
                throw new Error(errorMsg);
            }

            const result = await response.json();

            if (result.job_id) {
                console.log(`Processing started successfully. Job ID: ${result.job_id}`);
                if(submitPromptButton) submitPromptButton.dataset.jobId = result.job_id;
                processingStatusDiv.textContent = `Processing initiated (Job ID: ${result.job_id}). Waiting for results...`;
                startPollingStatus(result.job_id);
            } else {
                throw new Error("Backend response OK but missing Job ID.");
            }

        } catch (error) {
            console.error('Error during upload/processing initiation:', error);
            displayError(`Upload/Start Error: ${error.message || 'Network error or server unreachable'}`);
            generateButton.disabled = false; // Re-enable buttons on error
            if (submitPromptButton) submitPromptButton.disabled = false;
        }
    }

    function startPollingStatus(jobId) {
        console.log(`Starting status polling for Job ID: ${jobId}`);
        if (pollingIntervalId) { clearInterval(pollingIntervalId); }
        checkStatus(jobId); // Check immediately
        pollingIntervalId = setInterval(() => checkStatus(jobId), POLLING_INTERVAL_MS);
    }

    async function checkStatus(jobId) {
        console.log(`Checking status for Job ID: ${jobId}...`);
        if (!processingStatusDiv) return;

        try {
            const response = await fetch(`${BACKEND_URL}/get_status/${jobId}`);

            if (!response.ok) {
                if (response.status === 404) {
                    console.warn(`Job ID ${jobId} status not found. Continuing poll...`);
                    processingStatusDiv.textContent = `Waiting for job ${jobId} status...`;
                    return;
                }
                throw new Error(`HTTP error checking status! Status: ${response.status}`);
            }

            const result = await response.json();
            console.log("Status received:", result);
            processingStatusDiv.textContent = `Status: ${result.status || 'Unknown'}`;

            if (result.status === 'completed' || result.status === 'failed') {
                console.log(`Polling finished for Job ID: ${jobId}. Status: ${result.status}`);
                clearInterval(pollingIntervalId);
                pollingIntervalId = null;
                fetchFinalResult(jobId);
            } else if (result.status === 'processing') {
                console.log("Still processing..."); // Normal state
            } else if (result.status === 'not_found') {
                 console.warn(`Job ID ${jobId} status reported as 'not_found'. Continuing poll...`);
                 processingStatusDiv.textContent = `Waiting for job ${jobId} status...`;
            } else {
                 console.warn(`Unexpected status received: ${result.status}`);
            }

        } catch (error) {
            console.error('Error polling status:', error);
            clearInterval(pollingIntervalId);
            pollingIntervalId = null;
            displayError(`Error checking status: ${error.message}`);
            generateButton.disabled = false;
             if (submitPromptButton) submitPromptButton.disabled = false;
        }
    }

    async function fetchFinalResult(jobId) {
        console.log(`Fetching final result for Job ID: ${jobId}`);
        if (!processingStatusDiv || !reportOutputDiv) return;
        processingStatusDiv.textContent = 'Fetching final report...';
        processingStatusDiv.style.color = '#e1e1ff';

        try {
            const response = await fetch(`${BACKEND_URL}/get_result/${jobId}`);

            if (!response.ok) {
                let errorMsg = `HTTP error fetching result! Status: ${response.status}`;
                try { const errResult = await response.json(); errorMsg = errResult.error || errResult.detail || `Server error ${response.status}`; } catch (e) {}
                throw new Error(errorMsg);
            }

            const result = await response.json();
            console.log("Final result received:", result);

            if (result.status === 'completed' && result.data) {
                processingStatusDiv.textContent = 'Report generated successfully!';
                processingStatusDiv.style.color = '#00c7d9';
                displayReport(result.data); // Call function to render the report
            } else if (result.status === 'failed') {
                // Display error message from backend if available
                displayError(`Processing failed: ${result.data?.error || 'Unknown processing error'}`);
            } else {
                displayError(`Unexpected final status: ${result.status || 'Unknown'}`);
            }

        } catch (error) {
            console.error('Error fetching final result:', error);
            displayError(`Error fetching report: ${error.message}`);
        } finally {
            generateButton.disabled = false; // Re-enable buttons
            if (submitPromptButton) submitPromptButton.disabled = false;
        }
    }

    function displayReport(data) {
        console.log("Displaying report data");
        if (!reportOutputDiv) return;
        reportOutputDiv.innerHTML = ''; // Clear

        // --- Display Speaker Dialogue ---
        if (data.dialogue && data.dialogue.length > 0) {
            const dialogueHeader = document.createElement('h4');
            dialogueHeader.textContent = 'Conversation Dialogue:';
            reportOutputDiv.appendChild(dialogueHeader);

            const dialogueContainer = document.createElement('div');
            dialogueContainer.className = 'dialogue-output'; // Add class for styling if needed
            // Add styles via JS for simplicity
            dialogueContainer.style.maxHeight = '300px';
            dialogueContainer.style.overflowY = 'auto';
            dialogueContainer.style.border = '1px solid #444464';
            dialogueContainer.style.padding = '15px';
            dialogueContainer.style.backgroundColor = '#1f1f3a';
            dialogueContainer.style.borderRadius = '5px';
            dialogueContainer.style.marginBottom = '20px';
            dialogueContainer.style.color = '#e1e1ff';

            data.dialogue.forEach(turn => {
                const turnP = document.createElement('p');
                turnP.style.marginBottom = '10px';
                turnP.style.lineHeight = '1.5';
                const speakerSpan = document.createElement('strong');
                speakerSpan.textContent = `Speaker ${turn.speaker}: `;
                const speakerColors = { 'A': '#00c7d9', 'B': '#ffab00', 'C': '#ff6b6b', 'Unknown': '#cccccc' };
                speakerSpan.style.color = speakerColors[turn.speaker] || '#e1e1ff'; // Fallback color
                turnP.appendChild(speakerSpan);
                turnP.appendChild(document.createTextNode(turn.text));
                dialogueContainer.appendChild(turnP);
            });
            reportOutputDiv.appendChild(dialogueContainer);
        } else if (data.full_transcript) {
             // Fallback display for full transcript
             const transcriptHeader = document.createElement('h4');
             transcriptHeader.textContent = 'Full Transcript:';
             reportOutputDiv.appendChild(transcriptHeader);
             const transcriptPre = document.createElement('pre'); // Use <pre> for formatting
             transcriptPre.style.whiteSpace = 'pre-wrap';
             transcriptPre.style.wordWrap = 'break-word';
             transcriptPre.style.backgroundColor = '#1f1f3a';
             transcriptPre.style.padding = '10px';
             transcriptPre.style.borderRadius = '5px';
             transcriptPre.textContent = data.full_transcript;
             reportOutputDiv.appendChild(transcriptPre);
        } else {
             const noDataP = document.createElement('p');
             noDataP.textContent = "Processing completed, but no dialogue data was returned by the backend.";
             reportOutputDiv.appendChild(noDataP);
        }

        // You can add similar blocks here later to display other data if the
        // backend's process_audio_and_return_dialogue function starts returning
        // entities, keywords, summary etc. in the 'data' object.
        // Example:
        // if (data.entities && data.entities.length > 0) { ... display entities ... }
        // if (data.keywords && data.keywords.length > 0) { ... display keywords ... }
    }

    function displayError(message) {
        console.error("Displaying Error:", message);
        if (!reportOutputDiv || !processingStatusDiv) return;
        reportOutputDiv.innerHTML = ''; // Clear report area
        const errorP = document.createElement('p');
        errorP.style.color = '#ff4d4d'; // Error color
        errorP.style.fontWeight = 'bold';
        errorP.textContent = `Error: ${message}`;
        reportOutputDiv.appendChild(errorP);
        processingStatusDiv.textContent = 'Operation Failed!';
        processingStatusDiv.style.color = '#ff4d4d';
    }

     // --- Placeholder Function for Submit Prompt ---
     function handleSubmitPromptClick() {
         // Safety check elements
         if (!textPromptInput || !submitPromptButton || !processingStatusDiv) return;

          const promptText = textPromptInput.value.trim();
          const jobId = submitPromptButton.dataset.jobId; // Get job ID stored earlier

          if (!promptText) {
               displayError("Please enter a text prompt.");
               return;
          }
          if (!jobId) {
               displayError("Please process an audio file first to get a Job ID for the prompt.");
               return;
          }

          console.log(`Submitting prompt for Job ID ${jobId}: "${promptText}"`);
          processingStatusDiv.textContent = 'Submitting prompt... (Feature Not Implemented Yet)';
          processingStatusDiv.style.color = '#e1e1ff';
          submitPromptButton.disabled = true;
          generateButton.disabled = true;

          // TODO: Implement backend endpoint and fetch call for summary generation
          // For now, simulate and re-enable buttons
          setTimeout(() => {
               console.log("Simulated prompt submission complete.");
               processingStatusDiv.textContent = 'Prompt submitted (Simulation). Summary generation needs backend implementation.';
               submitPromptButton.disabled = false;
               generateButton.disabled = false;
               // Add a placeholder in the output area
               const summaryPlaceholder = document.createElement('div');
               summaryPlaceholder.innerHTML = `<h4 style="margin-top: 20px; color: #ffab00;">Generated Summary (Placeholder)</h4><p>Based on prompt: "${promptText}", a summary would appear here if the backend supported it.</p>`;
               // Append below existing dialogue if possible
               if (reportOutputDiv) reportOutputDiv.appendChild(summaryPlaceholder);

          }, 1500);
     }

}); // End DOMContentLoaded