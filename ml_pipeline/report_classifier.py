# ml_pipeline/report_classifier.py
from typing import Dict, List, Tuple

def classify_sentences(processed_text: str) -> Dict[str, List[str]]:
    """
    Classifies sentences from processed text into predefined report sections
    using a basic rule-based approach.

    Args:
        processed_text: The input text string that has been preprocessed.

    Returns:
        A dictionary where keys are section labels (e.g., "Summary", "Action Items")
        and values are lists of sentences belonging to that section.
    """
    sections = {
        "Summary": [],
        "Action Items": [],
        "Key Decisions": []
    }
    sentences = processed_text.split('. ')  # Simple sentence splitting

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Basic rule-based classification
        if any(keyword in sentence.lower() for keyword in ["in summary", "to conclude", "overall"]):
            sections["Summary"].append(sentence)
        elif any(keyword in sentence.lower() for keyword in ["we should", "need to", "must", "action required", "to do"]):
            sections["Action Items"].append(sentence)
        elif any(keyword in sentence.lower() for keyword in ["decided to", "decision is", "agreed on", "the plan is"]):
            sections["Key Decisions"].append(sentence)
        else:
            sections["Summary"].append(sentence)

    return sections


def generate_report_text(structured_data: Dict) -> str:
    """
    Generates a basic text-based report from the structured data.

    Args:
        structured_data: A dictionary containing the report data
                         (metadata, classified_sentences, entities, keywords).

    Returns:
        A string representing the basic report.
    """
    report_lines = []
    report_lines.append(f"Report for Transcript ID: {structured_data.get('metadata', {}).get('transcript_id', 'N/A')}\n")

    if "Summary" in structured_data.get("classified_sentences", {}):
        report_lines.append("--- Summary ---\n")
        for sentence in structured_data["classified_sentences"]["Summary"]:
            report_lines.append(f"- {sentence}\n")

    if "Action Items" in structured_data.get("classified_sentences", {}):
        report_lines.append("\n--- Action Items ---\n")
        for sentence in structured_data["classified_sentences"]["Action Items"]:
            report_lines.append(f"- {sentence}\n")

    if "Key Decisions" in structured_data.get("classified_sentences", {}):
        report_lines.append("\n--- Key Decisions ---\n")
        for sentence in structured_data["classified_sentences"]["Key Decisions"]:
            report_lines.append(f"- {sentence}\n")

    if "entities" in structured_data:
        report_lines.append("\n--- Entities ---\n")
        for entity, entity_type in structured_data["entities"]:
            report_lines.append(f"- {entity} ({entity_type})\n")

    if "keywords" in structured_data:
        report_lines.append("\n--- Keywords ---\n")
        for keyword, relevance in structured_data["keywords"]:
            report_lines.append(f"- {keyword}: {relevance:.2f}\n")

    return "".join(report_lines)


if __name__ == '__main__':
    text = "The main points are summarized below. We should implement this feature by next week. The team decided to proceed with option A. Overall, the project is on track. Action required: send out the minutes."
    classified = classify_sentences(text)
    print(f"Classified Sentences: {classified}")

    # Example structured data (this would come from the backend)
    example_data = {
        "metadata": {"transcript_id": 123},
        "classified_sentences": {
            "Summary": ["The project is on track.", "Key findings include X and Y."],
            "Action Items": ["Follow up on Z."],
            "Key Decisions": ["Proceed with option A."]
        },
        "entities": [("Project X", "PRODUCT"), ("Team A", "ORG")],
        "keywords": [("project", 0.9), ("findings", 0.7)]
    }
    report = generate_report_text(example_data)
    print(report)