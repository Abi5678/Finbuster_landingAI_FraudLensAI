"""
Fraud Collaboration Network Analyzer
Detects fraud rings by analyzing connections between claims, claimants, and providers
"""
import random
from typing import Dict, List, Any
from datetime import datetime, timedelta


class FraudNetworkAnalyzer:
    """Analyzes multi-claim patterns to detect fraud rings and collaboration networks"""
    
    def __init__(self):
        self.analyzer_name = "FraudNetworkAnalyzer"
    
    def analyze_network(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze if this claim is part of a larger fraud network
        
        Args:
            claim_data: Current claim information
            
        Returns:
            Network analysis results with connections and risk assessment
        """
        claimant_name = claim_data.get('claimant', {}).get('name', 'Unknown')
        provider_name = self._extract_provider(claim_data)
        claim_amount = claim_data.get('claimed_amount', 0)
        
        # Analyze claimant history
        claimant_connections = self._analyze_claimant_history(claimant_name)
        
        # Analyze provider history
        provider_connections = self._analyze_provider_history(provider_name, claim_amount)
        
        # Detect fraud ring patterns
        fraud_ring_detected = self._detect_fraud_ring(claimant_connections, provider_connections)
        
        # Calculate network risk score
        network_risk_score = self._calculate_network_risk(
            claimant_connections, 
            provider_connections, 
            fraud_ring_detected
        )
        
        return {
            'claimant_name': claimant_name,
            'provider_name': provider_name,
            'claimant_connections': claimant_connections,
            'provider_connections': provider_connections,
            'fraud_ring_detected': fraud_ring_detected,
            'network_risk_score': network_risk_score,
            'risk_level': self._get_risk_level(network_risk_score)
        }
    
    def _extract_provider(self, claim_data: Dict) -> str:
        """Extract provider/company name from claim data"""
        # Try to extract from various fields
        incident_type = claim_data.get('incident_type', '').lower()
        
        if 'hertz' in incident_type or 'rental' in incident_type:
            return "Hertz Corporation"
        elif 'repair' in incident_type:
            return "ABC Repair Shop"
        else:
            return "Unknown Provider"
    
    def _analyze_claimant_history(self, claimant_name: str) -> Dict[str, Any]:
        """
        Analyze claimant's history across all claims
        For demo purposes, generates realistic patterns
        """
        # Simulate database lookup
        # In production, this would query a real claims database
        
        # Generate realistic claim history
        has_history = random.random() > 0.6  # 40% chance of prior claims
        
        if not has_history:
            return {
                'total_claims': 1,
                'prior_claims': [],
                'patterns': [],
                'red_flags': 0
            }
        
        # Generate 2-4 prior claims
        num_prior_claims = random.randint(2, 4)
        prior_claims = []
        patterns = []
        red_flags = 0
        
        for i in range(num_prior_claims):
            days_ago = random.randint(90, 730)  # 3 months to 2 years ago
            claim_date = datetime.now() - timedelta(days=days_ago)
            
            claim = {
                'claim_id': f"CLM{random.randint(1000, 9999)}",
                'date': claim_date.strftime('%Y-%m-%d'),
                'amount': random.randint(2000, 8000),
                'status': random.choice(['Paid', 'Denied', 'Pending', 'Under Investigation'])
            }
            prior_claims.append(claim)
        
        # Detect patterns
        if num_prior_claims >= 3:
            patterns.append("Multiple claims in short timeframe")
            red_flags += 1
        
        # Check for same provider pattern
        if random.random() > 0.5:
            patterns.append("Same provider used in multiple claims")
            red_flags += 1
        
        # Check for amount escalation
        amounts = [c['amount'] for c in prior_claims]
        if len(amounts) >= 2 and all(amounts[i] < amounts[i+1] for i in range(len(amounts)-1)):
            patterns.append("Escalating claim amounts over time")
            red_flags += 1
        
        return {
            'total_claims': num_prior_claims + 1,
            'prior_claims': prior_claims,
            'patterns': patterns,
            'red_flags': red_flags
        }
    
    def _analyze_provider_history(self, provider_name: str, current_amount: float) -> Dict[str, Any]:
        """
        Analyze provider's history across all claims
        For demo purposes, generates realistic patterns
        """
        if provider_name == "Unknown Provider":
            return {
                'total_claims': 1,
                'claims_this_year': 1,
                'average_claim_amount': current_amount,
                'confirmed_frauds': 0,
                'patterns': [],
                'red_flags': 0
            }
        
        # Simulate provider with suspicious history
        is_suspicious = random.random() > 0.4  # 60% chance of suspicious provider
        
        if not is_suspicious:
            return {
                'total_claims': random.randint(5, 15),
                'claims_this_year': random.randint(3, 8),
                'average_claim_amount': current_amount * random.uniform(0.8, 1.2),
                'confirmed_frauds': 0,
                'patterns': [],
                'red_flags': 0
            }
        
        # Generate suspicious provider profile
        total_claims = random.randint(35, 75)
        claims_this_year = random.randint(15, 35)
        confirmed_frauds = random.randint(5, 20)
        
        patterns = []
        red_flags = 0
        
        # High volume pattern
        if claims_this_year > 20:
            patterns.append(f"Unusually high claim volume ({claims_this_year} claims this year)")
            red_flags += 1
        
        # Same address pattern
        if random.random() > 0.5:
            same_address_count = random.randint(10, 30)
            patterns.append(f"{same_address_count} claims share same billing address")
            red_flags += 1
        
        # Confirmed fraud history
        if confirmed_frauds > 0:
            patterns.append(f"{confirmed_frauds} confirmed fraudulent claims")
            red_flags += 2
        
        # Amount inflation pattern
        if random.random() > 0.6:
            patterns.append("Claims consistently above market average")
            red_flags += 1
        
        return {
            'total_claims': total_claims,
            'claims_this_year': claims_this_year,
            'average_claim_amount': current_amount * random.uniform(0.9, 1.1),
            'confirmed_frauds': confirmed_frauds,
            'patterns': patterns,
            'red_flags': red_flags
        }
    
    def _detect_fraud_ring(self, claimant_data: Dict, provider_data: Dict) -> Dict[str, Any]:
        """Detect if this appears to be part of a fraud ring"""
        
        # Calculate fraud ring indicators
        total_red_flags = claimant_data['red_flags'] + provider_data['red_flags']
        
        # High red flags = likely fraud ring
        if total_red_flags >= 4:
            ring_size = random.randint(12, 25)
            return {
                'detected': True,
                'confidence': 0.85 + (total_red_flags * 0.03),
                'estimated_ring_size': ring_size,
                'description': f"This claim appears to be part of a larger fraud operation involving {ring_size}+ individuals and entities.",
                'indicators': [
                    "Multiple connected claims with same patterns",
                    "Provider has history of confirmed fraud",
                    "Network analysis shows coordinated activity"
                ]
            }
        elif total_red_flags >= 2:
            return {
                'detected': True,
                'confidence': 0.60 + (total_red_flags * 0.05),
                'estimated_ring_size': random.randint(5, 10),
                'description': "Possible fraud collaboration detected between claimant and provider.",
                'indicators': [
                    "Suspicious patterns in claim history",
                    "Provider shows concerning activity patterns"
                ]
            }
        else:
            return {
                'detected': False,
                'confidence': 0.0,
                'estimated_ring_size': 0,
                'description': "No evidence of fraud ring collaboration.",
                'indicators': []
            }
    
    def _calculate_network_risk(self, claimant_data: Dict, provider_data: Dict, fraud_ring: Dict) -> float:
        """Calculate overall network risk score (0-100)"""
        
        # Base score from red flags
        red_flag_score = (claimant_data['red_flags'] + provider_data['red_flags']) * 12
        
        # Fraud ring detection bonus
        fraud_ring_score = 0
        if fraud_ring['detected']:
            fraud_ring_score = fraud_ring['confidence'] * 40
        
        # Provider history penalty
        provider_fraud_score = min(provider_data['confirmed_frauds'] * 5, 30)
        
        # Calculate total
        total_score = min(red_flag_score + fraud_ring_score + provider_fraud_score, 100)
        
        return round(total_score, 1)
    
    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to risk level"""
        if score >= 75:
            return "CRITICAL"
        elif score >= 50:
            return "HIGH"
        elif score >= 25:
            return "MEDIUM"
        else:
            return "LOW"


def display_network_analysis(claim_data: Dict[str, Any]):
    """
    Streamlit component to display fraud network analysis
    
    Args:
        claim_data: Current claim information
    """
    import streamlit as st
    
    # Initialize analyzer
    analyzer = FraudNetworkAnalyzer()
    
    # Run analysis
    with st.spinner("🕸️ Analyzing fraud collaboration network..."):
        results = analyzer.analyze_network(claim_data)
    
    # Display header
    st.markdown("### 🕸️ Fraud Collaboration Network Analysis")
    st.markdown(
        "<p style='color: #B0B0B0; margin-bottom: 1.5rem;'>"
        "Cross-claim analysis to detect fraud rings and coordinated fraud schemes"
        "</p>",
        unsafe_allow_html=True
    )
    
    # Risk colors
    risk_color = {
        "CRITICAL": "#D32F2F",
        "HIGH": "#FF9800",
        "MEDIUM": "#F57C00",
        "LOW": "#4CAF50"
    }.get(results['risk_level'], "#757575")
    
    fraud_ring = results['fraud_ring_detected']
    
    # ========== 1. PRIMARY ALERT BANNER (TOP PRIORITY) ==========
    if fraud_ring['detected']:
        # Calculate gauge percentage for visual
        risk_percentage = results['network_risk_score']
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #2d1b1b 0%, #1a0f0f 100%);
                    border: 3px solid {risk_color};
                    padding: 2rem;
                    border-radius: 16px;
                    margin-bottom: 2rem;
                    box-shadow: 0 8px 24px rgba(211, 47, 47, 0.3);'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='flex: 1;'>
                    <h2 style='color: {risk_color}; margin: 0 0 1rem 0; font-size: 1.8rem; font-weight: 700;'>
                        ⚠️ FRAUD RING DETECTED
                    </h2>
                    <p style='color: #E0E0E0; margin: 0 0 1.5rem 0; font-size: 1.1rem; line-height: 1.6;'>
                        {fraud_ring['description']}
                    </p>
                    <div style='display: flex; gap: 2rem; margin-bottom: 1rem;'>
                        <div>
                            <p style='color: #B0B0B0; margin: 0; font-size: 0.85rem;'>CONFIDENCE</p>
                            <p style='color: {risk_color}; margin: 0; font-size: 1.5rem; font-weight: 700;'>{fraud_ring['confidence']:.0%}</p>
                        </div>
                        <div>
                            <p style='color: #B0B0B0; margin: 0; font-size: 0.85rem;'>RING SIZE</p>
                            <p style='color: {risk_color}; margin: 0; font-size: 1.5rem; font-weight: 700;'>{fraud_ring['estimated_ring_size']}+ individuals</p>
                        </div>
                    </div>
                </div>
                <div style='text-align: center; padding-left: 2rem;'>
                    <div style='position: relative; width: 160px; height: 160px;'>
                        <svg width="160" height="160" viewBox="0 0 160 160">
                            <circle cx="80" cy="80" r="70" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="12"/>
                            <circle cx="80" cy="80" r="70" fill="none" stroke="{risk_color}" stroke-width="12"
                                    stroke-dasharray="{risk_percentage * 4.4} 440"
                                    stroke-linecap="round"
                                    transform="rotate(-90 80 80)"/>
                        </svg>
                        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);'>
                            <p style='color: {risk_color}; margin: 0; font-size: 2.5rem; font-weight: 700;'>{results['network_risk_score']:.0f}</p>
                            <p style='color: #B0B0B0; margin: 0; font-size: 0.8rem;'>RISK SCORE</p>
                        </div>
                    </div>
                    <p style='color: {risk_color}; margin: 0.5rem 0 0 0; font-size: 1.2rem; font-weight: 600;'>{results['risk_level']}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Action button
        if st.button("🔍 Investigate Fraud Ring", type="primary", use_container_width=True):
            st.info("🚧 Detailed fraud ring investigation view - Feature coming soon!")
    else:
        # Low risk banner
        st.markdown(f"""
        <div style='background: rgba(76, 175, 80, 0.15);
                    border: 2px solid #4CAF50;
                    padding: 1.5rem;
                    border-radius: 12px;
                    margin-bottom: 2rem;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='flex: 1;'>
                    <h3 style='color: #4CAF50; margin: 0 0 0.5rem 0;'>✓ No Fraud Ring Detected</h3>
                    <p style='color: #E0E0E0; margin: 0;'>This claim shows no evidence of coordinated fraud activity.</p>
                </div>
                <div style='text-align: center; padding-left: 2rem;'>
                    <p style='color: {risk_color}; margin: 0; font-size: 2.5rem; font-weight: 700;'>{results['network_risk_score']:.0f}</p>
                    <p style='color: #B0B0B0; margin: 0; font-size: 0.8rem;'>RISK SCORE</p>
                    <p style='color: {risk_color}; margin: 0.5rem 0 0 0; font-weight: 600;'>{results['risk_level']}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========== 2. TWO-COLUMN LAYOUT: CLAIMANT & PROVIDER ==========
    col1, col2 = st.columns(2)
    
    with col1:
        # Claimant Analysis Card
        claimant_red_flags = results['claimant_connections']['red_flags']
        flag_color = "#FF5757" if claimant_red_flags > 0 else "#4CAF50"
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    border: 2px solid rgba(255,255,255,0.1);
                    border-radius: 12px;
                    padding: 1.5rem;
                    height: 100%;
                    transition: all 0.3s ease;'>
            <h4 style='color: #F0F0F0; margin: 0 0 0.5rem 0; font-size: 1.1rem;'>
                👤 Claimant Analysis
            </h4>
            <p style='color: #B0B0B0; margin: 0 0 1.5rem 0; font-size: 1rem; font-weight: 600;'>
                {results['claimant_name']}
            </p>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;'>
                <div style='background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px;'>
                    <p style='color: #B0B0B0; margin: 0; font-size: 0.75rem; text-transform: uppercase;'>Total Claims</p>
                    <p style='color: #F0F0F0; margin: 0.25rem 0 0 0; font-size: 1.8rem; font-weight: 700;'>
                        {results['claimant_connections']['total_claims']}
                    </p>
                </div>
                <div style='background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px;'>
                    <p style='color: #B0B0B0; margin: 0; font-size: 0.75rem; text-transform: uppercase;'>
                        🚩 Red Flags
                    </p>
                    <p style='color: {flag_color}; margin: 0.25rem 0 0 0; font-size: 1.8rem; font-weight: 700;'>
                        {claimant_red_flags}
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Make red flags clickable
        if claimant_red_flags > 0:
            with st.expander(f"🔍 View {claimant_red_flags} Red Flag Details"):
                for pattern in results['claimant_connections']['patterns']:
                    st.markdown(f"• {pattern}")
    
    with col2:
        # Provider Analysis Card
        provider_red_flags = results['provider_connections']['red_flags']
        provider_frauds = results['provider_connections']['confirmed_frauds']
        flag_color = "#FF5757" if provider_red_flags > 0 else "#4CAF50"
        fraud_color = "#D32F2F" if provider_frauds > 0 else "#4CAF50"
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    border: 2px solid rgba(255,255,255,0.1);
                    border-radius: 12px;
                    padding: 1.5rem;
                    height: 100%;
                    transition: all 0.3s ease;'>
            <h4 style='color: #F0F0F0; margin: 0 0 0.5rem 0; font-size: 1.1rem;'>
                🏢 Provider Analysis
            </h4>
            <p style='color: #B0B0B0; margin: 0 0 1.5rem 0; font-size: 1rem; font-weight: 600;'>
                {results['provider_name']}
            </p>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;'>
                <div style='background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px;'>
                    <p style='color: #B0B0B0; margin: 0; font-size: 0.75rem; text-transform: uppercase;'>Total Claims</p>
                    <p style='color: #F0F0F0; margin: 0.25rem 0 0 0; font-size: 1.8rem; font-weight: 700;'>
                        {results['provider_connections']['total_claims']}
                    </p>
                </div>
                <div style='background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px;'>
                    <p style='color: #B0B0B0; margin: 0; font-size: 0.75rem; text-transform: uppercase;'>This Year</p>
                    <p style='color: #F0F0F0; margin: 0.25rem 0 0 0; font-size: 1.8rem; font-weight: 700;'>
                        {results['provider_connections']['claims_this_year']}
                    </p>
                </div>
            </div>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;'>
                <div style='background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px;'>
                    <p style='color: #B0B0B0; margin: 0; font-size: 0.75rem; text-transform: uppercase;'>
                        ⚠️ Confirmed Frauds
                    </p>
                    <p style='color: {fraud_color}; margin: 0.25rem 0 0 0; font-size: 1.8rem; font-weight: 700;'>
                        {provider_frauds}
                    </p>
                </div>
                <div style='background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px;'>
                    <p style='color: #B0B0B0; margin: 0; font-size: 0.75rem; text-transform: uppercase;'>
                        🚩 Red Flags
                    </p>
                    <p style='color: {flag_color}; margin: 0.25rem 0 0 0; font-size: 1.8rem; font-weight: 700;'>
                        {provider_red_flags}
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Make red flags clickable
        if provider_red_flags > 0:
            with st.expander(f"🔍 View {provider_red_flags} Red Flag Details"):
                for pattern in results['provider_connections']['patterns']:
                    st.markdown(f"• {pattern}")
    
    # ========== 3. PRIOR CLAIMS HISTORY (OPTIONAL DETAIL) ==========
    prior_claims = results['claimant_connections'].get('prior_claims', [])
    if prior_claims and len(prior_claims) > 0:
        st.markdown("---")
        with st.expander(f"📋 View Claimant's Prior Claims History ({len(prior_claims)} claims)", expanded=False):
            for claim in prior_claims:
                status_color = {
                    'Paid': '#4CAF50',
                    'Denied': '#FF5757',
                    'Pending': '#FF9800',
                    'Under Investigation': '#F57C00'
                }.get(claim['status'], '#757575')
                
                st.markdown(f"""
                <div style='background: rgba(0,0,0,0.3); padding: 0.75rem; margin-bottom: 0.5rem; border-radius: 6px;'>
                    <strong style='color: #F0F0F0;'>{claim['claim_id']}</strong> - 
                    <span style='color: #B0B0B0;'>{claim['date']}</span> - 
                    <span style='color: #E0E0E0;'>${claim['amount']:,}</span> - 
                    <span style='color: {status_color};'>{claim['status']}</span>
                </div>
                """, unsafe_allow_html=True)

