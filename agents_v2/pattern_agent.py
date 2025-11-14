"""
Pattern Matching Agent
Uses Gemini to identify known fraud patterns
"""
import requests
from typing import Dict, Any, List
from loguru import logger


class PatternMatchingAgent:
    """Specialized agent for detecting known fraud patterns"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.agent_name = "PatternMatchingAgent"
        self.known_patterns = self._load_fraud_patterns()
        logger.info(f"{self.agent_name} initialized with {len(self.known_patterns)} patterns")

    def _load_fraud_patterns(self) -> List[Dict]:
        """Load known fraud patterns from knowledge base"""
        return [
            {
                "name": "Staged Accident",
                "keywords": ["sudden stop", "intentional", "pre-planned", "witness coaching"],
                "severity": "critical",
                "confidence_threshold": 0.7
            },
            {
                "name": "Inflated Damages",
                "keywords": ["excessive", "unreasonable", "market value", "overpriced"],
                "severity": "high",
                "confidence_threshold": 0.6
            },
            {
                "name": "Phantom Passenger",
                "keywords": ["additional passenger", "unbuckled", "not mentioned initially"],
                "severity": "high",
                "confidence_threshold": 0.7
            },
            {
                "name": "Prior Damage Claim",
                "keywords": ["pre-existing", "previous damage", "old injury", "prior claim"],
                "severity": "medium",
                "confidence_threshold": 0.6
            },
            {
                "name": "Medical Mill",
                "keywords": ["multiple providers", "unnecessary treatment", "excessive therapy"],
                "severity": "high",
                "confidence_threshold": 0.7
            },
            {
                "name": "Rent-a-Crash",
                "keywords": ["rental car", "multiple claims", "short rental", "immediate accident"],
                "severity": "critical",
                "confidence_threshold": 0.75
            },
            {
                "name": "Insurance Fraud Ring",
                "keywords": ["same location", "multiple claims", "connected parties", "coordinated"],
                "severity": "critical",
                "confidence_threshold": 0.8
            }
        ]

    async def analyze(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze for known fraud patterns

        Args:
            document_data: Extracted document data

        Returns:
            Dict containing pattern matches and confidence scores
        """
        logger.info(f"{self.agent_name}: Starting pattern analysis")

        if not document_data.get("success"):
            return {
                "success": False,
                "agent": self.agent_name,
                "error": "Document extraction failed"
            }

        markdown = document_data.get("markdown", "")

        # Keyword-based pattern matching
        keyword_matches = self._keyword_pattern_matching(markdown)

        # LLM-based pattern analysis
        llm_patterns = await self._gemini_pattern_analysis(markdown)

        # Combine results
        all_indicators = keyword_matches + llm_patterns

        logger.success(f"{self.agent_name}: Found {len(all_indicators)} pattern matches")

        return {
            "success": True,
            "agent": self.agent_name,
            "indicators": all_indicators,
            "patterns_detected": len(all_indicators),
            "confidence": self._calculate_confidence(all_indicators)
        }

    def _keyword_pattern_matching(self, text: str) -> List[Dict]:
        """Simple keyword-based pattern matching"""
        indicators = []
        text_lower = text.lower()

        for pattern in self.known_patterns:
            # Count matching keywords
            matches = sum(1 for kw in pattern["keywords"] if kw in text_lower)

            if matches >= 2:  # At least 2 keywords must match
                confidence = min(0.9, 0.4 + (matches * 0.1))

                if confidence >= pattern["confidence_threshold"]:
                    indicators.append({
                        "type": "fraud_pattern",
                        "severity": pattern["severity"],
                        "description": f"Detected '{pattern['name']}' pattern ({matches} indicators)",
                        "confidence": confidence,
                        "agent": self.agent_name,
                        "pattern_name": pattern["name"]
                    })

        return indicators

    async def _gemini_pattern_analysis(self, text: str) -> List[Dict]:
        """Use Gemini to identify fraud patterns"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"

        # Build pattern descriptions for the prompt
        pattern_descriptions = "\n".join([
            f"- {p['name']}: {', '.join(p['keywords'][:3])}"
            for p in self.known_patterns
        ])

        prompt = f"""
Analyze this insurance claim for known fraud patterns.

KNOWN FRAUD PATTERNS TO CHECK:
{pattern_descriptions}

CLAIM TEXT (first 8000 chars):
{text[:8000]}

For each pattern you detect, provide:
PATTERN: [Pattern name]
CONFIDENCE: [0.0-1.0]
EVIDENCE: [Specific text from claim]

Only list patterns you are confident about (>0.6 confidence).
If no patterns detected, write "NO PATTERNS DETECTED".
"""

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    analysis = result['candidates'][0]['content']['parts'][0]['text']
                    return self._parse_pattern_analysis(analysis)

        except Exception as e:
            logger.error(f"{self.agent_name}: Gemini analysis failed - {str(e)}")

        return []

    def _parse_pattern_analysis(self, analysis: str) -> List[Dict]:
        """Parse Gemini's pattern analysis"""
        indicators = []

        if "NO PATTERNS DETECTED" in analysis.upper():
            return indicators

        # Simple parsing for patterns
        import re
        lines = analysis.split('\n')

        current_pattern = None
        current_confidence = 0.6

        for line in lines:
            if line.strip().startswith("PATTERN:"):
                current_pattern = line.split(":", 1)[1].strip()
            elif line.strip().startswith("CONFIDENCE:"):
                try:
                    conf_str = line.split(":", 1)[1].strip()
                    current_confidence = float(re.search(r'([0-9.]+)', conf_str).group(1))
                except:
                    current_confidence = 0.6

                if current_pattern and current_confidence >= 0.6:
                    indicators.append({
                        "type": "fraud_pattern",
                        "severity": "high",
                        "description": f"LLM detected pattern: {current_pattern}",
                        "confidence": current_confidence,
                        "agent": self.agent_name
                    })
                    current_pattern = None

        return indicators[:5]  # Limit to 5 patterns

    def _calculate_confidence(self, indicators: List[Dict]) -> float:
        """Calculate overall pattern matching confidence"""
        if not indicators:
            return 0.9  # High confidence in no patterns

        # Average confidence of detected patterns
        total_conf = sum(ind.get("confidence", 0.6) for ind in indicators)
        return round(total_conf / len(indicators), 3)
