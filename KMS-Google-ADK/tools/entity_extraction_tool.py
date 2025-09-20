"""
Entity Extraction Tool for KMS-Google-ADK
Extracts entities, keyphrases, and concepts from markdown content.
"""

from typing import Dict, List, Any, Optional, Tuple
import re
import spacy
from dataclasses import dataclass
from collections import Counter
import json


@dataclass
class Entity:
    """Represents an extracted entity."""
    text: str
    label: str
    start: int
    end: int
    confidence: float
    context: str


@dataclass
class Keyphrase:
    """Represents an extracted keyphrase."""
    text: str
    score: float
    positions: List[Tuple[int, int]]


class EntityExtractionTool:
    """Tool for extracting entities, keyphrases, and concepts from text."""
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize with spaCy model."""
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            # Fallback to basic model if en_core_web_sm not available
            self.nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
        
        # Entity types we care about
        self.relevant_entities = {
            "PERSON", "ORG", "GPE", "PRODUCT", "EVENT", "WORK_OF_ART",
            "LAW", "LANGUAGE", "DATE", "TIME", "PERCENT", "MONEY",
            "QUANTITY", "ORDINAL", "CARDINAL"
        }
        
        # Common academic/technical terms
        self.technical_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Title Case terms
            r'\b[a-z]+(?:\s+[a-z]+)*\s+(?:algorithm|method|technique|approach|model|framework|system|architecture)\b',
            r'\b[A-Z]{2,}\b',  # Acronyms
            r'\b(?:API|SDK|UI|UX|ML|AI|NLP|CV|RL|DL|CNN|RNN|LSTM|BERT|GPT)\b',
        ]
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract entities, keyphrases, and concepts from text.
        
        Args:
            text: Input text to process
            
        Returns:
            Dict with entities, keyphrases, concepts, and metadata
        """
        try:
            doc = self.nlp(text)
            
            # Extract named entities
            entities = self._extract_named_entities(doc)
            
            # Extract keyphrases
            keyphrases = self._extract_keyphrases(doc)
            
            # Extract technical concepts
            concepts = self._extract_technical_concepts(text)
            
            # Extract wikilinks and explicit references
            wikilinks = self._extract_wikilinks(text)
            
            # Extract URLs
            urls = self._extract_urls(text)
            
            return {
                "entities": [self._entity_to_dict(e) for e in entities],
                "keyphrases": [self._keyphrase_to_dict(k) for k in keyphrases],
                "concepts": concepts,
                "wikilinks": wikilinks,
                "urls": urls,
                "metadata": {
                    "text_length": len(text),
                    "word_count": len(doc),
                    "sentence_count": len(list(doc.sents)),
                    "entity_count": len(entities),
                    "keyphrase_count": len(keyphrases)
                }
            }
            
        except Exception as e:
            return {
                "entities": [],
                "keyphrases": [],
                "concepts": [],
                "wikilinks": [],
                "urls": [],
                "metadata": {"error": str(e)}
            }
    
    def _extract_named_entities(self, doc) -> List[Entity]:
        """Extract named entities using spaCy NER."""
        entities = []
        
        for ent in doc.ents:
            if ent.label_ in self.relevant_entities:
                # Get context around the entity
                start = max(0, ent.start_char - 50)
                end = min(len(doc.text), ent.end_char + 50)
                context = doc.text[start:end]
                
                entities.append(Entity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.8,  # spaCy doesn't provide confidence by default
                    context=context
                ))
        
        return entities
    
    def _extract_keyphrases(self, doc) -> List[Keyphrase]:
        """Extract keyphrases using noun phrases and frequency."""
        keyphrases = []
        
        # Extract noun phrases
        noun_phrases = [chunk.text for chunk in doc.noun_chunks]
        
        # Count frequency and filter
        phrase_counts = Counter(noun_phrases)
        
        for phrase, count in phrase_counts.most_common(20):
            if len(phrase.split()) >= 2 and len(phrase) > 5:
                # Find all positions of this phrase
                positions = []
                start = 0
                while True:
                    pos = doc.text.find(phrase, start)
                    if pos == -1:
                        break
                    positions.append((pos, pos + len(phrase)))
                    start = pos + 1
                
                # Calculate score based on frequency and length
                score = count * len(phrase.split()) / 10.0
                
                keyphrases.append(Keyphrase(
                    text=phrase,
                    score=min(score, 1.0),
                    positions=positions
                ))
        
        return keyphrases[:10]  # Return top 10
    
    def _extract_technical_concepts(self, text: str) -> List[str]:
        """Extract technical concepts using regex patterns."""
        concepts = set()
        
        for pattern in self.technical_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                concept = match.group().strip()
                if len(concept) > 3:  # Filter out very short matches
                    concepts.add(concept)
        
        return list(concepts)
    
    def _extract_wikilinks(self, text: str) -> List[Dict[str, Any]]:
        """Extract [[wikilinks]] from text."""
        wikilinks = []
        pattern = r'\[\[([^\]]+)\]\]'
        
        for match in re.finditer(pattern, text):
            link_text = match.group(1)
            # Handle aliases: [[display text|actual link]]
            if '|' in link_text:
                display, actual = link_text.split('|', 1)
                wikilinks.append({
                    "display": display.strip(),
                    "target": actual.strip(),
                    "start": match.start(),
                    "end": match.end()
                })
            else:
                wikilinks.append({
                    "display": link_text.strip(),
                    "target": link_text.strip(),
                    "start": match.start(),
                    "end": match.end()
                })
        
        return wikilinks
    
    def _extract_urls(self, text: str) -> List[Dict[str, Any]]:
        """Extract URLs from text."""
        urls = []
        pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        
        for match in re.finditer(pattern, text):
            urls.append({
                "url": match.group(),
                "start": match.start(),
                "end": match.end()
            })
        
        return urls
    
    def _entity_to_dict(self, entity: Entity) -> Dict[str, Any]:
        """Convert Entity to dictionary."""
        return {
            "text": entity.text,
            "label": entity.label,
            "start": entity.start,
            "end": entity.end,
            "confidence": entity.confidence,
            "context": entity.context
        }
    
    def _keyphrase_to_dict(self, keyphrase: Keyphrase) -> Dict[str, Any]:
        """Convert Keyphrase to dictionary."""
        return {
            "text": keyphrase.text,
            "score": keyphrase.score,
            "positions": keyphrase.positions
        }
