"""
Synthesis Agent for KMS-Google-ADK
Handles query answering, summarization, and knowledge synthesis.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import asyncio
import logging
import json
from dataclasses import dataclass
from enum import Enum

from tools.vector_search_tool import VectorSearchTool
from tools.simple_entity_extraction_tool import SimpleEntityExtractionTool as EntityExtractionTool
from agents.linking_agent import LinkingAgent, LinkType


class SynthesisType(Enum):
    """Types of synthesis operations."""
    ANSWER = "answer"
    SUMMARY = "summary"
    EXPLANATION = "explanation"
    COMPARISON = "comparison"
    TIMELINE = "timeline"


@dataclass
class SynthesisResult:
    """Represents a synthesis result."""
    query: str
    synthesis_type: SynthesisType
    content: str
    sources: List[Dict[str, Any]]
    confidence: float
    metadata: Dict[str, Any]
    created_at: datetime


class SynthesisAgent:
    """
    Agent responsible for synthesizing information and answering queries.
    
    This agent handles:
    - Answering questions based on indexed content
    - Generating document summaries
    - Creating explanations and comparisons
    - Building timelines and relationships
    - Knowledge synthesis and reasoning
    """
    
    def __init__(self, db_path: str = "kms_index.db"):
        """
        Initialize the synthesis agent.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Initialize tools
        self.vector_search_tool = VectorSearchTool(db_path)
        self.entity_extraction_tool = EntityExtractionTool(db_path)
        self.linking_agent = LinkingAgent(db_path)
        
        self.logger.info("Synthesis Agent initialized")
    
    async def answer_question(
        self,
        question: str,
        context_limit: int = 5,
        include_sources: bool = True
    ) -> SynthesisResult:
        """
        Answer a question based on indexed content.
        
        Args:
            question: Question to answer
            context_limit: Maximum number of relevant documents to use
            include_sources: Whether to include source citations
            
        Returns:
            Synthesis result with answer
        """
        try:
            self.logger.info(f"Answering question: {question}")
            
            # Search for relevant content
            search_results = await self.vector_search_tool.search(
                query=question,
                limit=context_limit
            )
            
            if not search_results:
                return SynthesisResult(
                    query=question,
                    synthesis_type=SynthesisType.ANSWER,
                    content="I couldn't find any relevant information to answer your question.",
                    sources=[],
                    confidence=0.0,
                    metadata={"reason": "no_relevant_content"},
                    created_at=datetime.now(timezone.utc)
                )
            
            # Extract key information from search results
            context_pieces = []
            sources = []
            
            for result in search_results:
                context_pieces.append({
                    "content": result.snippet,
                    "title": result.metadata.get("title", ""),
                    "path": result.path,
                    "score": result.score
                })
                
                if include_sources:
                    sources.append({
                        "title": result.metadata.get("title", ""),
                        "path": result.path,
                        "heading": result.metadata.get("heading", ""),
                        "relevance_score": result.score
                    })
            
            # Generate answer based on context
            answer_content = await self._generate_answer(question, context_pieces)
            
            # Calculate confidence based on search scores and content quality
            confidence = self._calculate_confidence(search_results, answer_content)
            
            return SynthesisResult(
                query=question,
                synthesis_type=SynthesisType.ANSWER,
                content=answer_content,
                sources=sources,
                confidence=confidence,
                metadata={
                    "context_documents": len(context_pieces),
                    "search_scores": [r.score for r in search_results]
                },
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to answer question: {str(e)}")
            return SynthesisResult(
                query=question,
                synthesis_type=SynthesisType.ANSWER,
                content=f"Sorry, I encountered an error while processing your question: {str(e)}",
                sources=[],
                confidence=0.0,
                metadata={"error": str(e)},
                created_at=datetime.now(timezone.utc)
            )
    
    async def _generate_answer(
        self,
        question: str,
        context_pieces: List[Dict[str, Any]]
    ) -> str:
        """
        Generate an answer based on question and context pieces.
        
        Args:
            question: The question to answer
            context_pieces: Relevant context from search results
            
        Returns:
            Generated answer text
        """
        # Simple answer generation based on context
        # In a real implementation, this would use a language model
        
        if not context_pieces:
            return "I couldn't find any relevant information to answer your question."
        
        # Sort by relevance score
        context_pieces.sort(key=lambda x: x["score"], reverse=True)
        
        # Extract key information
        key_points = []
        for piece in context_pieces[:3]:  # Use top 3 most relevant pieces
            content = piece["content"]
            if content:
                # Simple extraction of key sentences
                sentences = content.split('. ')
                for sentence in sentences[:2]:  # Take first 2 sentences
                    if sentence.strip() and len(sentence) > 20:
                        key_points.append(sentence.strip())
        
        # Generate answer
        if len(key_points) == 1:
            answer = key_points[0]
        elif len(key_points) > 1:
            answer = f"Based on the available information:\n\n" + "\n\n".join(f"• {point}" for point in key_points)
        else:
            answer = "I found some relevant information but couldn't extract a clear answer."
        
        return answer
    
    def _calculate_confidence(
        self,
        search_results: List[Any],
        answer_content: str
    ) -> float:
        """
        Calculate confidence score for an answer.
        
        Args:
            search_results: Search results used for context
            answer_content: Generated answer content
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not search_results or not answer_content:
            return 0.0
        
        # Base confidence on search scores
        avg_score = sum(r.score for r in search_results) / len(search_results)
        
        # Adjust based on answer quality
        answer_length = len(answer_content.split())
        if answer_length < 10:
            length_factor = 0.5
        elif answer_length < 50:
            length_factor = 0.8
        else:
            length_factor = 1.0
        
        # Combine factors
        confidence = min(avg_score * length_factor, 1.0)
        return round(confidence, 2)
    
    async def generate_summary(
        self,
        document_id: str,
        max_length: int = 200
    ) -> SynthesisResult:
        """
        Generate a summary for a document.
        
        Args:
            document_id: Document ID to summarize
            max_length: Maximum summary length in words
            
        Returns:
            Synthesis result with summary
        """
        try:
            self.logger.info(f"Generating summary for document: {document_id}")
            
            # Get document content
            doc_info = await self.vector_search_tool.get_document_info(document_id)
            if not doc_info:
                return SynthesisResult(
                    query=f"Summarize document {document_id}",
                    synthesis_type=SynthesisType.SUMMARY,
                    content="Document not found.",
                    sources=[],
                    confidence=0.0,
                    metadata={"error": "document_not_found"},
                    created_at=datetime.now(timezone.utc)
                )
            
            # Get all chunks for the document
            chunks = await self.vector_search_tool.get_document_chunks(document_id)
            
            if not chunks:
                return SynthesisResult(
                    query=f"Summarize document {document_id}",
                    synthesis_type=SynthesisType.SUMMARY,
                    content="No content available for summarization.",
                    sources=[],
                    confidence=0.0,
                    metadata={"error": "no_content"},
                    created_at=datetime.now(timezone.utc)
                )
            
            # Generate summary
            summary_content = await self._generate_summary(chunks, max_length)
            
            return SynthesisResult(
                query=f"Summarize document {document_id}",
                synthesis_type=SynthesisType.SUMMARY,
                content=summary_content,
                sources=[{
                    "title": doc_info.get("title", ""),
                    "path": doc_info.get("path", ""),
                    "chunks_used": len(chunks)
                }],
                confidence=0.8,  # High confidence for summaries
                metadata={
                    "document_id": document_id,
                    "chunks_processed": len(chunks),
                    "max_length": max_length
                },
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {str(e)}")
            return SynthesisResult(
                query=f"Summarize document {document_id}",
                synthesis_type=SynthesisType.SUMMARY,
                content=f"Error generating summary: {str(e)}",
                sources=[],
                confidence=0.0,
                metadata={"error": str(e)},
                created_at=datetime.now(timezone.utc)
            )
    
    async def _generate_summary(
        self,
        chunks: List[Dict[str, Any]],
        max_length: int
    ) -> str:
        """
        Generate a summary from document chunks.
        
        Args:
            chunks: Document chunks
            max_length: Maximum summary length in words
            
        Returns:
            Generated summary
        """
        # Simple extractive summarization
        # In a real implementation, this would use more sophisticated techniques
        
        # Sort chunks by importance (using headings and content length)
        scored_chunks = []
        for chunk in chunks:
            score = 0
            
            # Higher score for chunks with headings
            if chunk.get("heading"):
                score += 2
            
            # Higher score for longer chunks (more content)
            content_length = len(chunk.get("text", "").split())
            score += min(content_length / 50, 3)  # Cap at 3
            
            scored_chunks.append((score, chunk))
        
        # Sort by score and take top chunks
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Build summary
        summary_parts = []
        word_count = 0
        
        for score, chunk in scored_chunks:
            if word_count >= max_length:
                break
            
            text = chunk.get("text", "")
            heading = chunk.get("heading", "")
            
            if heading and text:
                part = f"**{heading}**: {text}"
            elif text:
                part = text
            else:
                continue
            
            part_words = len(part.split())
            if word_count + part_words <= max_length:
                summary_parts.append(part)
                word_count += part_words
            else:
                # Truncate to fit
                remaining_words = max_length - word_count
                truncated = " ".join(part.split()[:remaining_words])
                if truncated:
                    summary_parts.append(truncated + "...")
                break
        
        if not summary_parts:
            return "No content available for summarization."
        
        return "\n\n".join(summary_parts)
    
    async def generate_explanation(
        self,
        topic: str,
        depth: int = 2
    ) -> SynthesisResult:
        """
        Generate an explanation of a topic.
        
        Args:
            topic: Topic to explain
            depth: Explanation depth (1-3)
            
        Returns:
            Synthesis result with explanation
        """
        try:
            self.logger.info(f"Generating explanation for topic: {topic}")
            
            # Search for relevant content
            search_results = await self.vector_search_tool.search(
                query=topic,
                limit=10
            )
            
            if not search_results:
                return SynthesisResult(
                    query=f"Explain {topic}",
                    synthesis_type=SynthesisType.EXPLANATION,
                    content=f"I couldn't find any information about '{topic}' in the knowledge base.",
                    sources=[],
                    confidence=0.0,
                    metadata={"reason": "no_content_found"},
                    created_at=datetime.now(timezone.utc)
                )
            
            # Find related concepts and links
            related_concepts = []
            for result in search_results[:3]:
                links = await self.linking_agent.get_links(result.note_id, min_strength=0.6)
                related_concepts.extend(links)
            
            # Generate explanation
            explanation = await self._generate_explanation(topic, search_results, related_concepts, depth)
            
            # Prepare sources
            sources = []
            for result in search_results[:5]:
                sources.append({
                    "title": result.metadata.get("title", ""),
                    "path": result.path,
                    "relevance_score": result.score
                })
            
            return SynthesisResult(
                query=f"Explain {topic}",
                synthesis_type=SynthesisType.EXPLANATION,
                content=explanation,
                sources=sources,
                confidence=0.7,
                metadata={
                    "topic": topic,
                    "depth": depth,
                    "related_concepts": len(related_concepts)
                },
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate explanation: {str(e)}")
            return SynthesisResult(
                query=f"Explain {topic}",
                synthesis_type=SynthesisType.EXPLANATION,
                content=f"Error generating explanation: {str(e)}",
                sources=[],
                confidence=0.0,
                metadata={"error": str(e)},
                created_at=datetime.now(timezone.utc)
            )
    
    async def _generate_explanation(
        self,
        topic: str,
        search_results: List[Any],
        related_concepts: List[Any],
        depth: int
    ) -> str:
        """
        Generate an explanation based on search results and related concepts.
        
        Args:
            topic: Topic to explain
            search_results: Relevant search results
            related_concepts: Related concepts and links
            depth: Explanation depth
            
        Returns:
            Generated explanation
        """
        # Simple explanation generation
        # In a real implementation, this would use more sophisticated techniques
        
        explanation_parts = [f"# Explanation: {topic}\n"]
        
        # Basic definition from top results
        if search_results:
            top_result = search_results[0]
            explanation_parts.append(f"## Overview\n{top_result.snippet}\n")
        
        # Related concepts
        if related_concepts and depth > 1:
            explanation_parts.append("## Related Concepts\n")
            for concept in related_concepts[:5]:
                explanation_parts.append(f"• {concept.context}")
        
        # Additional details from other results
        if len(search_results) > 1 and depth > 2:
            explanation_parts.append("## Additional Details\n")
            for result in search_results[1:3]:
                explanation_parts.append(f"• {result.snippet}")
        
        return "\n".join(explanation_parts)
    
    async def compare_topics(
        self,
        topic1: str,
        topic2: str
    ) -> SynthesisResult:
        """
        Compare two topics.
        
        Args:
            topic1: First topic
            topic2: Second topic
            
        Returns:
            Synthesis result with comparison
        """
        try:
            self.logger.info(f"Comparing topics: {topic1} vs {topic2}")
            
            # Search for both topics
            results1 = await self.vector_search_tool.search(query=topic1, limit=5)
            results2 = await self.vector_search_tool.search(query=topic2, limit=5)
            
            if not results1 and not results2:
                return SynthesisResult(
                    query=f"Compare {topic1} and {topic2}",
                    synthesis_type=SynthesisType.COMPARISON,
                    content="I couldn't find information about either topic for comparison.",
                    sources=[],
                    confidence=0.0,
                    metadata={"reason": "no_content_found"},
                    created_at=datetime.now(timezone.utc)
                )
            
            # Generate comparison
            comparison = await self._generate_comparison(topic1, topic2, results1, results2)
            
            # Prepare sources
            sources = []
            for result in results1 + results2:
                sources.append({
                    "title": result.metadata.get("title", ""),
                    "path": result.path,
                    "topic": topic1 if result in results1 else topic2
                })
            
            return SynthesisResult(
                query=f"Compare {topic1} and {topic2}",
                synthesis_type=SynthesisType.COMPARISON,
                content=comparison,
                sources=sources,
                confidence=0.6,
                metadata={
                    "topic1": topic1,
                    "topic2": topic2,
                    "results1_count": len(results1),
                    "results2_count": len(results2)
                },
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to compare topics: {str(e)}")
            return SynthesisResult(
                query=f"Compare {topic1} and {topic2}",
                synthesis_type=SynthesisType.COMPARISON,
                content=f"Error generating comparison: {str(e)}",
                sources=[],
                confidence=0.0,
                metadata={"error": str(e)},
                created_at=datetime.now(timezone.utc)
            )
    
    async def _generate_comparison(
        self,
        topic1: str,
        topic2: str,
        results1: List[Any],
        results2: List[Any]
    ) -> str:
        """
        Generate a comparison between two topics.
        
        Args:
            topic1: First topic
            topic2: Second topic
            results1: Search results for first topic
            results2: Search results for second topic
            
        Returns:
            Generated comparison
        """
        comparison_parts = [f"# Comparison: {topic1} vs {topic2}\n"]
        
        # Overview of each topic
        if results1:
            comparison_parts.append(f"## {topic1}\n{results1[0].snippet}\n")
        
        if results2:
            comparison_parts.append(f"## {topic2}\n{results2[0].snippet}\n")
        
        # Key differences
        comparison_parts.append("## Key Differences\n")
        
        if results1 and results2:
            comparison_parts.append("• Different approaches and methodologies")
            comparison_parts.append("• Varying levels of complexity")
            comparison_parts.append("• Different use cases and applications")
        
        # Similarities
        comparison_parts.append("\n## Similarities\n")
        comparison_parts.append("• Both topics are related to the same domain")
        comparison_parts.append("• Similar underlying concepts and principles")
        
        return "\n".join(comparison_parts)
    
    async def get_synthesis_history(
        self,
        limit: int = 20,
        synthesis_type: Optional[SynthesisType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get history of synthesis operations.
        
        Args:
            limit: Maximum number of results
            synthesis_type: Optional filter by synthesis type
            
        Returns:
            List of synthesis results
        """
        # In a real implementation, this would query a database
        # For now, return empty list
        return []
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """
        Get the current status of the synthesis agent.
        
        Returns:
            Dict with agent status
        """
        return {
            "agent_type": "synthesis",
            "status": "ready",
            "capabilities": [
                "answer_questions",
                "generate_summaries",
                "create_explanations",
                "compare_topics"
            ],
            "tools_available": {
                "vector_search": True,
                "entity_extraction": True,
                "linking": True
            }
        }
