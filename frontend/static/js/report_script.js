document.addEventListener('DOMContentLoaded', function() {
    // Get the job_id from the URL
    const pathParts = window.location.pathname.split('/');
    const jobId = pathParts[pathParts.length - 1];
    
    // Function to format the dialogue
    function formatDialogue(dialogue) {
        return dialogue.map(entry => {
            return `<div class="dialogue-entry">
                <span class="speaker">Speaker ${entry.speaker}:</span>
                <span class="text">${entry.text}</span>
            </div>`;
        }).join('');
    }

    // Function to format entities
    function formatEntities(entities) {
        if (!entities || entities.length === 0) return 'No entities detected';
        return entities.map(([entity, type]) => {
            return `<span class="entity"><strong>${entity}</strong> (${type})</span>`;
        }).join(', ');
    }

    // Function to format sentences by category
    function formatClassifiedSentences(classified) {
        if (!classified) return '';
        let html = '';
        for (const [category, sentences] of Object.entries(classified)) {
            if (sentences && sentences.length > 0) {
                html += `<h4>${category}</h4><ul>`;
                html += sentences.map(sentence => `<li>${sentence}</li>`).join('');
                html += '</ul>';
            }
        }
        return html;
    }

    // Fetch the report data
    fetch(`/api/report/${jobId}`)
        .then(response => response.json())
        .then(data => {
            const reportContent = document.getElementById('reportContent');
            
            reportContent.innerHTML = `
                <div class="status completed">
                    <h2>Report Generated Successfully</h2>
                </div>
                <div class="report-text">
                    <h3>File Analysis: ${data.audio_filename}</h3>
                    
                    <section class="report-section">
                        <h4>Full Transcript</h4>
                        <p>${data.raw_transcript}</p>
                    </section>

                    <section class="report-section">
                        <h4>Conversation Flow</h4>
                        <div class="dialogue-container">
                            ${formatDialogue(data.dialogue_json)}
                        </div>
                    </section>

                    <section class="report-section">
                        <h4>Named Entities</h4>
                        <p>${formatEntities(data.entities_json)}</p>
                    </section>

                    <section class="report-section">
                        <h4>Analysis</h4>
                        ${formatClassifiedSentences(data.classified_sentences_json)}
                    </section>
                </div>
            `;
        })
        .catch(error => {
            const reportContent = document.getElementById('reportContent');
            reportContent.innerHTML = `
                <div class="status error">
                    <h2>Error Generating Report</h2>
                    <p>There was an error generating your report. Please try again later.</p>
                </div>
            `;
            console.error('Error:', error);
        });

    // Regenerate button handling
    const regenerateBtn = document.getElementById('regenerateBtn');
    regenerateBtn.addEventListener('click', function() {
        const customPrompt = document.getElementById('customPrompt').value;
        const reportContent = document.getElementById('reportContent');
        
        reportContent.innerHTML = `
            <div class="status generating">
                <div class="loading-spinner"></div>
                <p>Regenerating your report...</p>
            </div>
        `;

        // Send regeneration request
        fetch(`/api/regenerate/${jobId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ custom_prompt: customPrompt })
        })
        .then(response => response.json())
        .then(data => {
            // Refresh the page to show new report
            window.location.reload();
        })
        .catch(error => {
            reportContent.innerHTML = `
                <div class="status error">
                    <h2>Error Regenerating Report</h2>
                    <p>There was an error regenerating your report. Please try again later.</p>
                </div>
            `;
            console.error('Error:', error);
        });
    });
});