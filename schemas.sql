CREATE TABLE transcripts (
    transcript_id INT AUTO_INCREMENT PRIMARY KEY,
    audio_filename VARCHAR(255),
    raw_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE processed_text (
    processed_text_id INT AUTO_INCREMENT PRIMARY KEY,
    transcript_id INT,
    preprocessed_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transcript_id) REFERENCES transcripts(transcript_id) ON DELETE CASCADE
);

CREATE TABLE entities (
    entity_id INT AUTO_INCREMENT PRIMARY KEY,
    processed_text_id INT,
    entity_text VARCHAR(255),
    entity_type VARCHAR(255),
    FOREIGN KEY (processed_text_id) REFERENCES processed_text(processed_text_id) ON DELETE CASCADE
);

CREATE TABLE keywords (
    keyword_id INT AUTO_INCREMENT PRIMARY KEY,
    processed_text_id INT,
    keyword VARCHAR(255),
    relevance FLOAT,
    FOREIGN KEY (processed_text_id) REFERENCES processed_text(processed_text_id) ON DELETE CASCADE
);