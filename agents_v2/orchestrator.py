"""
Fraud Orchestrator
Coordinates all specialized agents for comprehensive fraud analysis
"""
import asyncio
from typing import Dict, Any
from loguru import logger
from datetime import datetime

from .document_agent import DocumentAgent
from .inconsistency_agent import InconsistencyAgent
from .pattern_agent import PatternMatchingAgent
from .scoring_agent import ScoringAgent


class FraudOrchestrator:
    """
    Master orchestrator that coordinates all fraud detection agents
    """

    def __init__(self, landingai_api_key: str, gemini_api_key: str):
        """Initialize orchestrator with all specialized agents"""
        self.landingai_api_key = landingai_api_key
        self.gemini_api_key = gemini_api_key

        logger.info("=" * 60)
        logger.info("Initializing ReconAI Multi-Agent System")
        logger.info("=" * 60)

        # Initialize all agents
        self.document_agent = DocumentAgent(landingai_api_key)
        self.inconsistency_agent = InconsistencyAgent(gemini_api_key)
        self.pattern_agent = PatternMatchingAgent(gemini_api_key)
        self.scoring_agent = ScoringAgent()

        logger.info("All agents initialized successfully")
        logger.info("=" * 60)

    async def analyze_claim(self, pdf_path: str) -> Dict[str, Any]:
        """
        Orchestrate complete fraud analysis of a claim

        Args:
            pdf_path: Path to PDF document

        Returns:
            Comprehensive fraud analysis result
        """
        start_time = datetime.now()

        logger.info(f"Starting multi-agent analysis of: {pdf_path}")
        logger.info("=" * 60)

        try:
            # Phase 1: Document Extraction
            logger.info("PHASE 1: Document Extraction")
            document_result = await self.document_agent.extract(pdf_path)

            if not document_result.get("success"):
                logger.error("Document extraction failed - aborting analysis")
                return {
                    "success": False,
                    "error": "Document extraction failed",
                    "phase": "document_extraction"
                }

            logger.success(f"✓ Document extracted ({len(document_result.get('markdown', ''))} chars)")

            # Phase 2: Parallel Specialized Analysis
            logger.info("\nPHASE 2: Parallel Agent Analysis")

            tasks = [
                self.inconsistency_agent.analyze(document_result),
                self.pattern_agent.analyze(document_result)
            ]

            # Run agents in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            inconsistency_result = results[0] if not isinstance(results[0], Exception) else {"success": False, "error": str(results[0])}
            pattern_result = results[1] if not isinstance(results[1], Exception) else {"success": False, "error": str(results[1])}

            # Log agent results
            if inconsistency_result.get("success"):
                logger.success(f"✓ Inconsistency Agent: {inconsistency_result.get('inconsistency_count', 0)} issues found")
            if pattern_result.get("success"):
                logger.success(f"✓ Pattern Agent: {pattern_result.get('patterns_detected', 0)} patterns detected")

            # Phase 3: Collect All Indicators
            logger.info("\nPHASE 3: Indicator Collection")

            all_indicators = []

            # From document agent
            all_indicators.extend(document_result.get("indicators", []))

            # From inconsistency agent
            if inconsistency_result.get("success"):
                all_indicators.extend(inconsistency_result.get("indicators", []))

            # From pattern agent
            if pattern_result.get("success"):
                all_indicators.extend(pattern_result.get("indicators", []))

            logger.info(f"Total indicators collected: {len(all_indicators)}")

            # Phase 4: Scoring
            logger.info("\nPHASE 4: Fraud Scoring")

            agent_results = {
                "document_agent": document_result,
                "inconsistency_agent": inconsistency_result,
                "pattern_agent": pattern_result
            }

            scoring_result = await self.scoring_agent.calculate_score(all_indicators, agent_results)

            logger.success(f"✓ Final Score: {scoring_result['fraud_score']:.1%} ({scoring_result['risk_level'].upper()})")

            # Phase 5: Generate Summary
            logger.info("\nPHASE 5: Summary Generation")

            summary = self.scoring_agent.generate_summary(
                scoring_result['fraud_score'],
                all_indicators,
                agent_results
            )

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info("=" * 60)
            logger.success(f"Analysis complete in {processing_time:.1f} seconds")
            logger.info("=" * 60)

            # Build final result
            final_result = {
                "success": True,
                "fraud_score": scoring_result['fraud_score'],
                "risk_level": scoring_result['risk_level'],
                "recommendation": scoring_result['recommendation'],
                "confidence": scoring_result['confidence'],
                "summary": summary,
                "total_indicators": len(all_indicators),
                "indicators": all_indicators,
                "scoring_breakdown": scoring_result['breakdown'],
                "agent_results": {
                    "document_extraction": {
                        "success": document_result.get("success"),
                        "content_length": len(document_result.get("markdown", "")),
                        "pages": document_result.get("metadata", {}).get("page_count", 0),
                    "chunks": len(document_result.get("chunks", [])),
                    "raw_chunks": document_result.get("chunks", []),
                    "raw_splits": document_result.get("splits", []),
                    "raw_grounding": document_result.get("grounding", {}),
                        "confidence": document_result.get("confidence", 0),
                        "indicators": len(document_result.get("indicators", [])),
                        "markdown": document_result.get("markdown", "")
                    },
                    "inconsistency_detection": {
                        "success": inconsistency_result.get("success"),
                        "inconsistencies_found": inconsistency_result.get("inconsistency_count", 0),
                        "confidence": inconsistency_result.get("confidence", 0),
                        "indicators": len(inconsistency_result.get("indicators", []))
                    },
                    "pattern_matching": {
                        "success": pattern_result.get("success"),
                        "patterns_detected": pattern_result.get("patterns_detected", 0),
                        "confidence": pattern_result.get("confidence", 0),
                        "indicators": len(pattern_result.get("indicators", []))
                    }
                },
                "metadata": {
                    "processing_time_seconds": processing_time,
                    "timestamp": datetime.now().isoformat(),
                    "agents_used": ["DocumentAgent", "InconsistencyAgent", "PatternMatchingAgent", "ScoringAgent"]
                }
            }

            return final_result

        except Exception as e:
            logger.error(f"Orchestrator error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

            return {
                "success": False,
                "error": str(e),
                "phase": "orchestration"
            }

    def get_agent_status(self) -> Dict[str, str]:
        """Get status of all agents"""
        return {
            "document_agent": "✓ Ready",
            "inconsistency_agent": "✓ Ready",
            "pattern_agent": "✓ Ready",
            "scoring_agent": "✓ Ready",
            "orchestrator": "✓ Ready"
        }
