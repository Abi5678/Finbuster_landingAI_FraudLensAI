"""
Fraud Story Narrative Generator
Generates human-readable narrative explaining how fraud was committed
"""
import os
import json
import requests
from typing import Dict, List
from datetime import datetime


def generate_fraud_narrative(claim_data: dict, indicators: list, gemini_api_key: str = None) -> str:
    """
    Generate compelling narrative story of fraud scheme
    
    Args:
        claim_data: Dictionary containing claim information
        indicators: List of fraud indicators detected
        gemini_api_key: Google Gemini API key (or from env)
    
    Returns:
        Narrative story as string
    """
    
    # Get API key
    if not gemini_api_key:
        gemini_api_key = os.getenv("GOOGLE_API_KEY")
    
    if not gemini_api_key:
        return generate_mock_narrative(claim_data, indicators)
    
    # Prepare evidence summary
    evidence_summary = []
    for indicator in indicators:
        evidence_summary.append({
            'type': indicator.get('type', 'unknown'),
            'severity': indicator.get('severity', 'medium'),
            'description': indicator.get('description', ''),
            'confidence': indicator.get('confidence', 0)
        })
    
    # Extract key claim details
    claim_summary = {
        'claim_id': claim_data.get('claim_id', 'Unknown'),
        'claimant': claim_data.get('claimant', {}).get('name', 'Unknown'),
        'incident_date': str(claim_data.get('incident_date', 'Unknown')),
        'claimed_amount': claim_data.get('claimed_amount', 0),
        'incident_type': claim_data.get('incident_type', 'Unknown')
    }
    
    # Create prompt for Gemini
    prompt = f"""You are an experienced fraud investigator analyzing an insurance claim. Based on the evidence below, 
write a clear, factual narrative (200-250 words) explaining what happened and what fraud indicators were detected.

IMPORTANT CONTEXT:
- This is a rental car damage claim where Hertz (rental company) is charging the customer
- The customer's insurance (Progressive or similar) is being billed for the damage
- Analyze WHO might be committing fraud: Is it the rental company inflating charges? The customer falsifying damage? Or collusion?
- Be objective and let the evidence guide your conclusion

CLAIM DETAILS:
{json.dumps(claim_summary, indent=2)}

FRAUD INDICATORS DETECTED:
{json.dumps(evidence_summary, indent=2)}

Write a narrative that:
1. Starts with the basic facts: "On [date], [company/person] submitted a claim for [amount]..."
2. Explains the timeline of events chronologically
3. Highlights the key inconsistencies or suspicious patterns found
4. Identifies WHO appears to be committing fraud based on the evidence
5. Explains WHAT type of fraud scheme this appears to be

Be specific with dates and amounts. Connect the evidence logically. Write as if presenting facts to an investigator.
Do not make assumptions beyond what the evidence shows.
"""
    
    try:
        # Call Gemini API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={gemini_api_key}"
        
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 500
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            narrative = result['candidates'][0]['content']['parts'][0]['text']
            return narrative.strip()
        else:
            print(f"API Error: {response.status_code}")
            return generate_mock_narrative(claim_data, indicators)
            
    except Exception as e:
        print(f"Error generating narrative: {e}")
        return generate_mock_narrative(claim_data, indicators)


def generate_mock_narrative(claim_data: dict, indicators: list) -> str:
    """Generate mock narrative when API is unavailable"""
    
    claimant = claim_data.get('claimant', {}).get('name', 'the party')
    incident_date = claim_data.get('incident_date', datetime.now())
    if isinstance(incident_date, str):
        incident_date_str = incident_date
    else:
        incident_date_str = incident_date.strftime('%B %d, %Y')
    
    claimed_amount = claim_data.get('claimed_amount', 0)
    claim_id = claim_data.get('claim_id', 'Unknown')
    
    # Build narrative from indicators
    narrative_parts = [
        f"On {incident_date_str}, a claim was submitted regarding {claim_id} for ${claimed_amount:,.2f}. "
        f"Analysis of the documentation reveals several concerning inconsistencies:"
    ]
    
    # Categorize indicators
    has_timing_issues = False
    has_documentation_issues = False
    has_cost_issues = False
    has_relationship_issues = False
    
    for indicator in indicators:
        desc = indicator.get('description', '').lower()
        if 'date' in desc or 'time' in desc or 'before' in desc:
            has_timing_issues = True
        if 'document' in desc or 'metadata' in desc or 'invoice' in desc:
            has_documentation_issues = True
        if 'cost' in desc or 'inflation' in desc or 'market' in desc:
            has_cost_issues = True
        if 'address' in desc or 'phone' in desc or 'relationship' in desc:
            has_relationship_issues = True
    
    # Add narrative elements based on what was detected
    if has_timing_issues:
        narrative_parts.append(
            "\n\nTiming inconsistencies were detected in the documentation. Key dates do not align with "
            "the claimed sequence of events, suggesting possible backdating or manipulation of records."
        )
    
    if has_documentation_issues:
        narrative_parts.append(
            "\n\nDocument metadata analysis reveals irregularities. The creation dates and modification "
            "timestamps do not match the stated timeline, raising questions about document authenticity."
        )
    
    if has_cost_issues:
        narrative_parts.append(
            f"\n\nThe claimed amount of ${claimed_amount:,.2f} appears significantly inflated compared to "
            "market averages for similar incidents. This pattern is consistent with known cost inflation schemes."
        )
    
    if has_relationship_issues:
        narrative_parts.append(
            "\n\nUnusual relationships were identified between parties involved in this claim. "
            "Shared contact information or addresses suggest potential collusion rather than independent parties."
        )
    
    # Conclusion based on severity
    high_severity_count = sum(1 for ind in indicators if ind.get('severity') in ['high', 'critical'])
    
    if high_severity_count >= 3:
        conclusion = (
            "\n\nCONCLUSION: Multiple high-severity fraud indicators suggest this claim requires immediate "
            "investigation. The pattern of inconsistencies indicates potential fraudulent activity rather than "
            "legitimate errors or oversights."
        )
    elif high_severity_count >= 1:
        conclusion = (
            "\n\nCONCLUSION: Significant fraud indicators warrant further investigation before processing. "
            "The inconsistencies detected should be resolved and verified with additional documentation."
        )
    else:
        conclusion = (
            "\n\nCONCLUSION: Minor inconsistencies detected. Recommend standard verification procedures "
            "before claim approval."
        )
    
    narrative_parts.append(conclusion)
    
    return "".join(narrative_parts)


def format_narrative_for_display(narrative: str) -> str:
    """
    Format narrative with HTML styling for Streamlit display
    
    Args:
        narrative: Plain text narrative
    
    Returns:
        HTML formatted narrative
    """
    
    # Add emphasis to key phrases
    narrative = narrative.replace('CONCLUSION:', '<strong style="color: #FF5757;">CONCLUSION:</strong>')
    narrative = narrative.replace('However,', '<strong>However,</strong>')
    narrative = narrative.replace('BEFORE', '<strong style="color: #FF5757;">BEFORE</strong>')
    narrative = narrative.replace('pre-planned', '<strong style="color: #FF9800;">pre-planned</strong>')
    
    # Convert newlines to HTML breaks
    narrative = narrative.replace('\n\n', '<br><br>')
    narrative = narrative.replace('\n', '<br>')
    
    return narrative


# Streamlit integration function
def display_fraud_story(claim_data: dict, indicators: list, gemini_api_key: str = None):
    """
    Display fraud story in Streamlit with dramatic styling
    
    Args:
        claim_data: Claim information dictionary
        indicators: List of fraud indicators
        gemini_api_key: Optional API key
    """
    import streamlit as st
    
    st.markdown("### Executive Summary")
    st.markdown(
        "<p style='color: #B0B0B0; margin-bottom: 1rem;'>"
        "AI-generated analysis of key findings and fraud indicators"
        "</p>",
        unsafe_allow_html=True
    )
    
    # Show loading spinner while generating
    with st.spinner("🔍 Analyzing evidence and reconstructing fraud timeline..."):
        narrative = generate_fraud_narrative(claim_data, indicators, gemini_api_key)
    
    # Format narrative
    formatted_narrative = format_narrative_for_display(narrative)
    
    # Display with dramatic styling
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border-left: 5px solid #FF5757;
                padding: 1.5rem;
                border-radius: 12px;
                font-family: Georgia, serif;
                line-height: 1.8;
                color: #E0E0E0;
                font-size: 1.05rem;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);'>
        {formatted_narrative}
    </div>
    """, unsafe_allow_html=True)
    
    # Add metadata footer
    st.markdown(f"""
    <div style='margin-top: 1rem; padding: 0.75rem; 
                background: rgba(0, 0, 0, 0.3); 
                border-radius: 8px;
                font-size: 0.85rem;
                color: #888;'>
        📊 Generated from {len(indicators)} fraud indicators | 
        🤖 Powered by Gemini 2.0 Flash | 
        ⏱️ Generated at {datetime.now().strftime('%I:%M %p')}
    </div>
    """, unsafe_allow_html=True)


# Example usage
if __name__ == "__main__":
    # Test data
    test_claim = {
        'claim_id': 'TEST-001',
        'claimant': {'name': 'John Doe'},
        'incident_date': '2024-01-15',
        'claimed_amount': 45000,
        'incident_type': 'auto'
    }
    
    test_indicators = [
        {
            'type': 'invoice_metadata',
            'severity': 'high',
            'description': 'Invoice created 5 days before incident date',
            'confidence': 0.92
        },
        {
            'type': 'relationship',
            'severity': 'high',
            'description': 'Claimant and provider share same address',
            'confidence': 0.88
        },
        {
            'type': 'cost_inflation',
            'severity': 'high',
            'description': 'Costs 150% above market average',
            'confidence': 0.85
        }
    ]
    
    narrative = generate_fraud_narrative(test_claim, test_indicators)
    print("FRAUD STORY:")
    print("=" * 60)
    print(narrative)

