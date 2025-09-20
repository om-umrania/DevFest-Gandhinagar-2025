"""
Simple Entity Extraction Tool for KMS-Google-ADK MVP
Basic entity and keyphrase extraction without external dependencies.
"""

from typing import Dict, List, Any
import re
from collections import Counter


class SimpleEntityTool:
    """Simple tool for extracting entities and keyphrases from text."""
    
    def __init__(self):
        """Initialize the simple entity extraction tool."""
        # Simple patterns for common entities
        self.patterns = {
            "PERSON": r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
            "ORG": r'\b[A-Z][a-z]+ (?:Inc|Corp|LLC|Ltd|Company|University|Institute)\b',
            "TECH": r'\b(?:API|SDK|UI|UX|ML|AI|NLP|CV|RL|DL|CNN|RNN|LSTM|BERT|GPT)\b',
            "ACRONYM": r'\b[A-Z]{2,}\b',
        }
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract entities, keyphrases, and concepts from text.
        
        Args:
            text: Input text to process
            
        Returns:
            Dict with entities, keyphrases, and metadata
        """
        try:
            # Extract entities using patterns
            entities = []
            for label, pattern in self.patterns.items():
                for match in re.finditer(pattern, text):
                    entities.append({
                        "text": match.group(),
                        "label": label,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.8
                    })
            
            # Extract keyphrases (simple noun phrases)
            keyphrases = self._extract_simple_keyphrases(text)
            
            # Extract wikilinks
            wikilinks = self._extract_wikilinks(text)
            
            # Extract URLs
            urls = self._extract_urls(text)
            
            return {
                "entities": entities,
                "keyphrases": keyphrases,
                "wikilinks": wikilinks,
                "urls": urls,
                "metadata": {
                    "text_length": len(text),
                    "entity_count": len(entities),
                    "keyphrase_count": len(keyphrases)
                }
            }
            
        except Exception as e:
            return {
                "entities": [],
                "keyphrases": [],
                "wikilinks": [],
                "urls": [],
                "metadata": {"error": str(e)}
            }
    
    def _extract_simple_keyphrases(self, text: str) -> List[Dict[str, Any]]:
        """Extract simple keyphrases using basic patterns."""
        # Find capitalized phrases (potential keyphrases)
        capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        # Count frequency
        phrase_counts = Counter(capitalized_phrases)
        
        # Return top keyphrases
        keyphrases = []
        for phrase, count in phrase_counts.most_common(10):
            if len(phrase.split()) >= 2:  # At least 2 words
                keyphrases.append({
                    "text": phrase,
                    "score": min(count / 5.0, 1.0),  # Normalize score
                    "count": count
                })
        
        return keyphrases
    
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
