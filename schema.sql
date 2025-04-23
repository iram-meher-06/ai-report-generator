CREATE TABLE IF NOT EXISTS transcripts (
    transcript_id INT AUTO_INCREMENT PRIMARY KEY,
    audio_filename VARCHAR(255),
    raw_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

