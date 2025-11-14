"""
Document Extraction Agent
Uses Landing AI ADE for document parsing
"""
import requests
from typing import Dict, Any
from loguru import logger


class DocumentAgent:
    """Specialized agent for document extraction using Landing AI ADE"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.agent_name = "DocumentAgent"
        logger.info(f"{self.agent_name} initialized")

    async def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract structured data from PDF using Landing AI ADE

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict containing extracted data, metadata, and confidence scores
        """
        logger.info(f"{self.agent_name}: Starting document extraction")

        url = "https://api.va.landing.ai/v1/ade/parse"
        # Use Bearer token authentication
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            with open(pdf_path, 'rb') as f:
                files = {'document': ('document.pdf', f, 'application/pdf')}
                data = {'model': 'dpt-2-latest'}

                response = requests.post(url, headers=headers, files=files, data=data, timeout=180)

                if response.status_code == 200:
                    result = response.json()

                    # Calculate extraction confidence
                    confidence = self._calculate_extraction_confidence(result)

                    logger.success(f"{self.agent_name}: Extraction complete (confidence: {confidence:.2%})")

                    return {
                        "success": True,
                        "agent": self.agent_name,
                        "markdown": result.get("markdown", ""),
                        "chunks": result.get("chunks", []),
                        "splits": result.get("splits", []),
                        "metadata": result.get("metadata", {}),
                        "grounding": result.get("grounding", {}),
                        "confidence": confidence,
                        "indicators": self._extract_document_indicators(result)
                    }
                else:
                    logger.error(f"{self.agent_name}: Extraction failed - {response.status_code}")
                    return {
                        "success": False,
                        "agent": self.agent_name,
                        "error": f"API returned status {response.status_code}",
                        "confidence": 0.0
                    }

        except Exception as e:
            logger.error(f"{self.agent_name}: Exception - {str(e)}")
            return {
                "success": False,
                "agent": self.agent_name,
                "error": str(e),
                "confidence": 0.0
            }

    def _calculate_extraction_confidence(self, result: Dict) -> float:
        """Calculate confidence score for extraction quality"""
        confidence = 1.0

        # Check if we got meaningful content
        markdown = result.get("markdown", "")
        if len(markdown) < 100:
            confidence *= 0.3
        elif len(markdown) < 1000:
            confidence *= 0.6

        # Check chunks
        chunks = result.get("chunks", [])
        if len(chunks) == 0:
            confidence *= 0.5

        # Check metadata
        metadata = result.get("metadata", {})
        if metadata.get("page_count", 0) == 0:
            confidence *= 0.5

        return round(confidence, 3)

    def _extract_document_indicators(self, result: Dict) -> list:
        """Extract fraud indicators from document structure"""
        indicators = []

        metadata = result.get("metadata", {})
        markdown = result.get("markdown", "")

        # Check for poor quality document (possible alteration)
        if metadata.get("page_count", 0) > 50:
            indicators.append({
                "type": "document_quality",
                "severity": "low",
                "description": f"Unusually long document ({metadata.get('page_count')} pages)",
                "confidence": 0.4,
                "agent": self.agent_name
            })

        # Check for missing key information
        key_terms = ["claim", "amount", "date", "name"]
        missing_terms = [term for term in key_terms if term.lower() not in markdown.lower()]

        if len(missing_terms) >= 2:
            indicators.append({
                "type": "missing_information",
                "severity": "medium",
                "description": f"Missing key information: {', '.join(missing_terms)}",
                "confidence": 0.6,
                "agent": self.agent_name
            })

        return indicators
