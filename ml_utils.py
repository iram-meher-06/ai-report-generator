import spacy
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer

# Load the English language model for SpaCy
nlp = spacy.load("en_core_web_sm")

def extract_entities(processed_text: str) -> List[Tuple[str, str]]:
    """
    Extracts named entities from processed text using SpaCy.

    Args:
        processed_text: The input text string that has been preprocessed.

    Returns:
        A list of tuples, where each tuple contains (entity_text, entity_type).
    """
    doc = nlp(processed_text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

def extract_keywords(processed_text: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """
    Extracts top keywords from processed text using TF-IDF.

    Args:
        processed_text: The input text string that has been preprocessed.
        top_n: The number of top keywords to return (default is 10).

    Returns:
        A list of tuples, where each tuple contains (keyword, tfidf_score),
        sorted by TF-IDF score in descending order.
    """
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([processed_text])
    feature_names = vectorizer.get_feature_names_out()

    # Get the TF-IDF scores for the document
    scores = tfidf_matrix.toarray()[0]

    # Create a list of (keyword, score) tuples
    keywords_with_scores = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)

    return keywords_with_scores[:top_n]

if __name__ == '__main__':
    text_entities = "Apple is planning to open a new store in London next month."
    entities = extract_entities(text_entities)
    print(f"Entities: {entities}")

    text_keywords = "Apple is planning to open a new store in London next month. They will hire many employees for the new store."
    keywords = extract_keywords(text_keywords, top_n=5)
    print(f"Keywords: {keywords}")