"""
Inconsistency Detection Agent
Uses Gemini to detect logical inconsistencies in claims
"""
import requests
import re
from typing import Dict, Any, List
from datetime import datetime
from loguru import logger


class InconsistencyAgent:
    """Specialized agent for detecting inconsistencies in claim data"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.agent_name = "InconsistencyAgent"
        logger.info(f"{self.agent_name} initialized")

    async def analyze(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze extracted document for inconsistencies

        Args:
            document_data: Extracted document data from DocumentAgent

        Returns:
            Dict containing inconsistency indicators and confidence scores
        """
        logger.info(f"{self.agent_name}: Starting inconsistency analysis")

        if not document_data.get("success"):
            return {
                "success": False,
                "agent": self.agent_name,
                "error": "Document extraction failed"
            }

        markdown = document_data.get("markdown", "")
        metadata = document_data.get("metadata", {})

        # Use Gemini to analyze for inconsistencies
        indicators = await self._gemini_inconsistency_check(markdown, metadata)

        # Add rule-based checks
        indicators.extend(self._rule_based_checks(markdown, metadata))

        logger.success(f"{self.agent_name}: Found {len(indicators)} inconsistencies")

        return {
            "success": True,
            "agent": self.agent_name,
            "indicators": indicators,
            "inconsistency_count": len(indicators),
            "confidence": self._calculate_confidence(indicators)
        }

    async def _gemini_inconsistency_check(self, text: str, metadata: Dict) -> List[Dict]:
        """Use Gemini to identify inconsistencies"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"

        prompt = f"""
Analyze this insurance claim document for ACTUAL LOGICAL INCONSISTENCIES - where information directly contradicts itself or is impossible.

DOCUMENT TEXT (first 10000 chars):
{text[:10000]}

METADATA:
- Pages: {metadata.get('page_count', 'Unknown')}
- Processing Time: {metadata.get('duration_ms', 'Unknown')}ms

IMPORTANT:
- Be VERY strict - only report clear contradictions.
- Each description must show what contradicts what.
- If you find fewer than 3 real inconsistencies, that's fine. Quality over quantity.

AN INCONSISTENCY MUST BE:
- A direct contradiction between two pieces of information in the document.
- A logical impossibility (e.g., event A happened before event B, but document says B came first).
- A mathematical error (e.g., line items don't add up to the stated total).
- Conflicting dates, amounts, or facts that cannot both be true.

NOT INCONSISTENCIES (DO NOT REPORT THESE):
- Suspicious patterns (e.g., pre-existing knowledge of an insurance company).
- Missing information (that's not an inconsistency, just incomplete data).
- Round numbers or formatting issues.
- Things that seem unusual but don't contradict anything.

EXAMPLES OF REAL INCONSISTENCIES:
✓ "Claim states incident occurred on 09/01/2025 but vehicle was returned on 09/03/2025 - the damage date is before the rental ended."
✓ "Document lists total as $5000 but itemized charges add up to $3500."
✓ "Claimant states they were in New York on June 1st in one section, but another section says they were in California on June 1st."

EXAMPLES OF WHAT IS NOT AN INCONSISTENCY:
✗ "Document mentions Progressive insurance company in rental agreement" - This is just information, not a contradiction.
✗ "Multiple round-number amounts detected" - This is a pattern, not an inconsistency.
✗ "Missing phone number for witness" - This is incomplete data, not contradictory information.

Identify ONLY actual inconsistencies in this EXACT format:

INCONSISTENCY 1:
Type: [timeline/amount/location/statement]
Severity: [critical/high/medium/low]
Description: [Write 1-2 complete, clear sentences explaining what contradicts what. Be thorough and specific. Maximum 400 characters.]
Evidence: [Short quote showing the contradiction]
Confidence: [0.0-1.0]

IMPORTANT: Each Description must be a COMPLETE thought. Do not cut off mid-sentence. Explain the full contradiction clearly.

If you find NO actual logical inconsistencies, write "NO INCONSISTENCIES DETECTED".
"""

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    analysis = result['candidates'][0]['content']['parts'][0]['text']
                    return self._parse_gemini_inconsistencies(analysis)

        except Exception as e:
            logger.error(f"{self.agent_name}: Gemini analysis failed - {str(e)}")

        return []

    def _parse_gemini_inconsistencies(self, analysis: str) -> List[Dict]:
        """Parse Gemini's inconsistency analysis into structured indicators"""
        indicators = []

        if "NO INCONSISTENCIES DETECTED" in analysis.upper():
            return indicators

        # Parse each inconsistency block
        sections = re.split(r'INCONSISTENCY \d+:', analysis)

        for section in sections[1:]:  # Skip first empty section
            try:
                indicator = {
                    "type": "inconsistency",
                    "agent": self.agent_name
                }

                # Extract fields
                type_match = re.search(r'Type:\s*\[?([^\]\n]+)\]?', section, re.IGNORECASE)
                if type_match:
                    indicator["subtype"] = type_match.group(1).strip().lower()

                severity_match = re.search(r'Severity:\s*\[?([^\]\n]+)\]?', section, re.IGNORECASE)
                if severity_match:
                    indicator["severity"] = severity_match.group(1).strip().lower()
                else:
                    indicator["severity"] = "medium"

                desc_match = re.search(r'Description:\s*(.+?)(?=\n\s*Evidence:|\n\s*Confidence:|\n\s*INCONSISTENCY|\Z)', section, re.DOTALL | re.IGNORECASE)
                if desc_match:
                    # Take the full description without truncation
                    # The AI prompt instructs to keep it under 400 chars
                    full_desc = desc_match.group(1).strip()
                    # Remove any trailing brackets or incomplete text
                    full_desc = re.sub(r'\[.*$', '', full_desc).strip()
                    indicator["description"] = full_desc
                else:
                    continue  # Skip if no description

                conf_match = re.search(r'Confidence:\s*([0-9.]+)', section, re.IGNORECASE)
                if conf_match:
                    indicator["confidence"] = float(conf_match.group(1))
                else:
                    indicator["confidence"] = 0.6

                indicators.append(indicator)

            except Exception as e:
                logger.warning(f"{self.agent_name}: Failed to parse inconsistency - {str(e)}")
                continue

        return indicators[:10]  # Limit to 10 inconsistencies

    def _rule_based_checks(self, text: str, metadata: Dict) -> List[Dict]:
        """Simple rule-based inconsistency checks"""
        indicators = []

        text_lower = text.lower()

        # Check for common fraud keywords
        fraud_keywords = ['guaranteed', 'no risk', '100% safe', 'act now', 'limited time']
        found_keywords = [kw for kw in fraud_keywords if kw in text_lower]

        if found_keywords:
            indicators.append({
                "type": "suspicious_language",
                "severity": "low",
                "description": f"Document contains suspicious keywords: {', '.join(found_keywords[:3])}",
                "confidence": 0.4,
                "agent": self.agent_name
            })

        # Check for round numbers (often fraudulent)
        round_amounts = re.findall(r'\$\s*([0-9,]+)\.00', text)
        if len(round_amounts) >= 3:
            indicators.append({
                "type": "round_numbers",
                "severity": "low",
                "description": f"Multiple round-number amounts detected ({len(round_amounts)} instances)",
                "confidence": 0.5,
                "agent": self.agent_name
            })

        return indicators

    def _calculate_confidence(self, indicators: List[Dict]) -> float:
        """Calculate overall confidence in inconsistency detection"""
        if not indicators:
            return 1.0  # High confidence that there are no inconsistencies

        # Average confidence of all indicators
        total_conf = sum(ind.get("confidence", 0.5) for ind in indicators)
        return round(total_conf / len(indicators), 3)
