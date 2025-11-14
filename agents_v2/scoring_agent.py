"""
Scoring Agent
Calculates final fraud score from all agent indicators
"""
from typing import Dict, Any, List
from loguru import logger


class ScoringAgent:
    """Specialized agent for calculating fraud scores"""

    def __init__(self):
        self.agent_name = "ScoringAgent"
        self.severity_weights = {
            "critical": 1.0,
            "high": 0.75,
            "medium": 0.50,
            "low": 0.25
        }
        logger.info(f"{self.agent_name} initialized")

    async def calculate_score(self, all_indicators: List[Dict], agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate final fraud score from all indicators

        Args:
            all_indicators: List of all fraud indicators from all agents
            agent_results: Results from all agents

        Returns:
            Dict containing fraud score and risk assessment
        """
        logger.info(f"{self.agent_name}: Calculating fraud score from {len(all_indicators)} indicators")

        if not all_indicators:
            return {
                "fraud_score": 0.0,
                "risk_level": "low",
                "recommendation": "approve",
                "confidence": 1.0,
                "breakdown": {
                    "indicator_score": 0.0,
                    "severity_score": 0.0,
                    "confidence_score": 1.0
                }
            }

        # Calculate different scoring components
        indicator_score = self._score_from_indicators(all_indicators)
        severity_score = self._score_from_severity(all_indicators)
        confidence_score = self._score_from_confidence(all_indicators)

        # Weighted combination
        fraud_score = (
            indicator_score * 0.4 +
            severity_score * 0.4 +
            confidence_score * 0.2
        )

        # Cap at 1.0
        fraud_score = min(fraud_score, 1.0)

        # Determine risk level
        risk_level = self._determine_risk_level(fraud_score)

        # Generate recommendation
        recommendation = self._generate_recommendation(fraud_score, all_indicators)

        logger.success(f"{self.agent_name}: Score calculated - {fraud_score:.1%} ({risk_level})")

        return {
            "fraud_score": round(fraud_score, 3),
            "risk_level": risk_level,
            "recommendation": recommendation,
            "confidence": round(confidence_score, 3),
            "breakdown": {
                "indicator_score": round(indicator_score, 3),
                "severity_score": round(severity_score, 3),
                "confidence_score": round(confidence_score, 3),
                "total_indicators": len(all_indicators),
                "critical_indicators": sum(1 for i in all_indicators if i.get("severity") == "critical"),
                "high_indicators": sum(1 for i in all_indicators if i.get("severity") == "high")
            }
        }

    def _score_from_indicators(self, indicators: List[Dict]) -> float:
        """Score based on number and type of indicators"""
        if not indicators:
            return 0.0

        # Scale based on count (logarithmic)
        import math
        count_factor = min(math.log(len(indicators) + 1) / math.log(10), 1.0)

        return count_factor

    def _score_from_severity(self, indicators: List[Dict]) -> float:
        """Score based on severity of indicators"""
        if not indicators:
            return 0.0

        total_weight = 0.0
        total_score = 0.0

        for indicator in indicators:
            severity = indicator.get("severity", "medium")
            weight = self.severity_weights.get(severity, 0.5)
            confidence = indicator.get("confidence", 0.5)

            total_weight += weight
            total_score += weight * confidence

        if total_weight > 0:
            normalized = total_score / total_weight
        else:
            normalized = 0.0

        return normalized

    def _score_from_confidence(self, indicators: List[Dict]) -> float:
        """Calculate average confidence across all indicators"""
        if not indicators:
            return 1.0  # High confidence in no fraud

        total_conf = sum(ind.get("confidence", 0.5) for ind in indicators)
        avg_conf = total_conf / len(indicators)

        return avg_conf

    def _determine_risk_level(self, fraud_score: float) -> str:
        """Determine risk level from fraud score"""
        if fraud_score >= 0.85:
            return "critical"
        elif fraud_score >= 0.70:
            return "high"
        elif fraud_score >= 0.50:
            return "medium"
        else:
            return "low"

    def _generate_recommendation(self, fraud_score: float, indicators: List[Dict]) -> str:
        """Generate processing recommendation"""
        critical_count = sum(1 for i in indicators if i.get("severity") == "critical")

        if fraud_score >= 0.85 or critical_count >= 2:
            return "deny"
        elif fraud_score >= 0.60:
            return "investigate"
        elif fraud_score >= 0.40:
            return "review"
        else:
            return "approve"

    def generate_summary(self, fraud_score: float, indicators: List[Dict], agent_results: Dict) -> str:
        """Generate executive summary"""
        risk_level = self._determine_risk_level(fraud_score)
        recommendation = self._generate_recommendation(fraud_score, indicators)

        # Count indicators by severity
        critical = sum(1 for i in indicators if i.get("severity") == "critical")
        high = sum(1 for i in indicators if i.get("severity") == "high")
        medium = sum(1 for i in indicators if i.get("severity") == "medium")
        low = sum(1 for i in indicators if i.get("severity") == "low")

        summary_lines = [
            "Executive Summary:",
            f"- Overall risk: {risk_level.upper()} (fraud score {fraud_score:.0%})",
            f"- Recommendation: {recommendation.upper()}",
            f"- Indicators detected: critical {critical}, high {high}, medium {medium}, low {low} (total {len(indicators)})",
        ]

        agent_notes = []
        for agent_name, result in agent_results.items():
            if result.get("success"):
                ind_count = len(result.get("indicators", []))
                confidence = result.get("confidence", 0.0)
                agent_notes.append(f"{agent_name}: {ind_count} indicators (confidence {confidence:.0%})")

        if agent_notes:
            summary_lines.append("- Agent findings: " + "; ".join(agent_notes))

        if fraud_score >= 0.70:
            summary_lines.append("Next steps: High risk detected; perform full investigation before processing.")
        elif fraud_score >= 0.50:
            summary_lines.append("Next steps: Medium risk; schedule additional review and verification.")
        else:
            summary_lines.append("Next steps: Low risk; proceed with standard processing.")

        return "\n".join(summary_lines)
