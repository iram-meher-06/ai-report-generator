// AI-REPORT-GENERATOR/frontend/static/js/report_script.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("Report Page JS Loaded - Initializing Report Fetch Logic");

    // --- Configuration ---
    const BACKEND_URL = 'http://127.0.0.1:5000'; // Ensure this matches your Flask backend

    // --- Select UI Elements ---
    const reportContentDiv = document.getElementById('report-content-dynamic');
    const statusMessageDiv = document.getElementById('report-status-message');
    const submitRegeneratePromptButton = document.getElementById('submitRegeneratePrompt');
    const regenerateTextInput = document.getElementById('regenerate-text');

    // --- Get job_id from the hidden span ---
    let jobId = null;
    const jobIdHolder = document.getElementById('job-id-holder');
    if (jobIdHolder && jobIdHolder.dataset.jobid) {
        jobId = jobIdHolder.dataset.jobid;
        console.log("Job ID retrieved from data attribute:", jobId);
    } else {
        console.error("CRITICAL: Job ID holder not found or job ID missing in HTML!");
        if (statusMessageDiv) statusMessageDiv.innerHTML = "<p style='color:red;'>Error: Could not identify report to load.</p>";
        return; // Stop execution if no job ID
    }

    // Safety checks for other essential elements
    if (!reportContentDiv) { console.error("CRITICAL: #report-content-dynamic div not found!"); return; }
    if (!statusMessageDiv) { console.error("CRITICAL: #report-status-message div not found!"); return; }


    async function fetchAndDisplayReport() {
        if (!jobId) { // Should have been caught above, but double check
            displayErrorOnReportPage("Error: No Job ID available to fetch report.");
            return;
        }

        console.log(`Fetching final report data for Job ID: ${jobId}`);
        statusMessageDiv.innerHTML = `<p><i>Fetching report data for Job ID: ${jobId}...</i></p>`;

        try {
            // The API endpoint path is relative to BACKEND_URL
            const response = await fetch(`${BACKEND_URL}/api/get_report_data/${jobId}`);

            if (!response.ok) {
                let errorMsg = `Error fetching report data! Status: ${response.status}`;
                try {
                    const errData = await response.json();
                    errorMsg = errData.error || errData.detail || `Server error ${response.status}`;
                } catch(e) {
                    console.warn("Could not parse error response as JSON for details.");
                }
                throw new Error(errorMsg);
            }

            const resultData = await response.json(); // This is the content of the "data" field from backend's analysis_results
            console.log("Fetched report data:", resultData);

            statusMessageDiv.innerHTML = "<p style='color:#00c7d9;'>Report loaded successfully!</p>";
            reportContentDiv.innerHTML = ''; // Clear placeholder "Please wait..."

            // --- Display Full Transcript (if available) ---
            if (resultData.full_transcript) {
                const transcriptHeader = document.createElement('h4');
                transcriptHeader.textContent = 'Full Transcript:';
                reportContentDiv.appendChild(transcriptHeader);
                const transcriptPre = document.createElement('pre');
                transcriptPre.textContent = resultData.full_transcript;
                reportContentDiv.appendChild(transcriptPre);
            }

            // --- Display Speaker Dialogue ---
            if (resultData.dialogue && resultData.dialogue.length > 0) {
                const dialogueHeader = document.createElement('h4');
                dialogueHeader.textContent = 'Conversation Dialogue:';
                reportContentDiv.appendChild(dialogueHeader);

                const dialogueContainer = document.createElement('div');
                dialogueContainer.className = 'dialogue-output'; // From your CSS

                resultData.dialogue.forEach(turn => {
                    const turnP = document.createElement('p');
                    turnP.className = 'dialogue-turn';
                    const speakerSpan = document.createElement('strong');
                    speakerSpan.textContent = `Speaker ${turn.speaker}: `;
                    // Assign colors based on speaker label A, B, C...
                    const speakerColors = { 'A': '#00c7d9', 'B': '#ffab00', 'C': '#ff6b6b', 'Unknown': '#cccccc' };
                    speakerSpan.style.color = speakerColors[turn.speaker] || '#e1e1ff'; // Fallback color
                    speakerSpan.className = `speaker-${turn.speaker}`; // For potential CSS styling
                    turnP.appendChild(speakerSpan);
                    turnP.appendChild(document.createTextNode(turn.text));
                    dialogueContainer.appendChild(turnP);
                });
                reportContentDiv.appendChild(dialogueContainer);
            }

            // --- Display Processed Text (if available) ---
            if (resultData.processed_text && !resultData.processed_text.startsWith("[")) { // Avoid showing error indicators
                const processedHeader = document.createElement('h4');
                processedHeader.textContent = 'Preprocessed Text (for Analysis):';
                reportContentDiv.appendChild(processedHeader);
                const processedP = document.createElement('p');
                processedP.style.fontStyle = 'italic';
                processedP.style.backgroundColor = '#2a2a4a'; // Slightly different BG
                processedP.style.padding = '10px';
                processedP.style.borderRadius = '3px';
                processedP.style.wordBreak = 'break-all';
                processedP.textContent = resultData.processed_text;
                reportContentDiv.appendChild(processedP);
            }

            // TODO Later: Add display logic for entities, keywords, generated summary from data object

        } catch (error) {
            console.error("Error in fetchAndDisplayReport:", error);
            displayErrorOnReportPage(`Failed to load report: ${error.message}`);
        }
    }

    function displayErrorOnReportPage(message) {
        console.error("Displaying Error on Report Page:", message);
        if(reportContentDiv) reportContentDiv.innerHTML = ''; // Clear report area
        if(statusMessageDiv) {
            statusMessageDiv.innerHTML = `<p style="color:#ff4d4d; font-weight:bold;">${message}</p>`;
        }
    }

    // --- Placeholder Function for Submit Prompt (on report.html) ---
     function handleSubmitRegeneratePromptClick() {
         if (!regenerateTextInput || !submitRegeneratePromptButton || !statusMessageDiv) return;

          const promptText = regenerateTextInput.value.trim();
          if (!jobId) {
               displayErrorOnReportPage("Job ID is missing, cannot submit prompt.");
               return;
          }
          if (!promptText) {
               displayErrorOnReportPage("Please enter a text prompt.");
               return;
          }
          console.log(`Submitting prompt for Job ID ${jobId}: "${promptText}"`);
          statusMessageDiv.innerHTML = '<p><i>Submitting prompt... (Feature Not Implemented Yet)</i></p>';
          submitRegeneratePromptButton.disabled = true;

          setTimeout(() => { // Simulate
               console.log("Simulated prompt submission complete on report page.");
               statusMessageDiv.innerHTML = '<p>Prompt submitted (Simulation). Further report generation not implemented.</p>';
               submitRegeneratePromptButton.disabled = false;
               const summaryPlaceholder = document.createElement('div');
               summaryPlaceholder.innerHTML = `<h4 style="margin-top: 20px; color: #ffab00;">Generated Summary (Placeholder)</h4><p>Based on prompt: "${promptText}", a summary would appear here if the backend supported it.</p>`;
               if (reportContentDiv) reportContentDiv.appendChild(summaryPlaceholder);
          }, 1500);
     }

     if(submitRegeneratePromptButton){
          submitRegeneratePromptButton.addEventListener('click', handleSubmitRegeneratePromptClick);
     }

    // --- Initial call to fetch data when report.html loads ---
    if(jobId) {
        fetchAndDisplayReport();
    } else {
        // This else block is crucial if jobId wasn't found
        console.error("Job ID not found on page load via data-attribute or URL. Cannot fetch report.");
        displayErrorOnReportPage("Could not determine which report to load (Job ID missing from page).");
    }

}); // End DOMContentLoaded