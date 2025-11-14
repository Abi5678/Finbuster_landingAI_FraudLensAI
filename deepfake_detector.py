"""
Deepfake and Photo Manipulation Detection
Analyzes photos for AI-generated or manipulated content
"""
import os
from PIL import Image
from PIL.ExifTags import TAGS
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
import hashlib


def detect_photo_manipulation(image_path: str) -> dict:
    """
    Detect if photo is AI-generated or manipulated
    
    Args:
        image_path: Path to image file
    
    Returns:
        Dictionary with detection results
    """
    
    results = {
        'ai_generated_probability': check_ai_artifacts(image_path),
        'manipulation_detected': detect_photoshop_traces(image_path),
        'metadata_tampering': check_exif_manipulation(image_path),
        'consistency_score': check_lighting_physics(image_path),
        'duplicate_detection': check_duplicate_regions(image_path)
    }
    
    # Calculate overall authenticity score
    authenticity = calculate_authenticity_score(results)
    
    # Determine issues
    issues_found = []
    if results['ai_generated_probability'] > 0.5:
        issues_found.append('Possible AI-generated content')
    if results['manipulation_detected'] > 0.5:
        issues_found.append('Digital manipulation detected')
    if results['metadata_tampering'] > 0.5:
        issues_found.append('EXIF metadata tampering')
    if results['consistency_score'] < 0.5:
        issues_found.append('Lighting/physics inconsistencies')
    if results['duplicate_detection'] > 0.5:
        issues_found.append('Duplicate/cloned regions found')
    
    return {
        'authentic': authenticity > 0.7,
        'authenticity_score': authenticity,
        'confidence': max(results.values()),
        'issues_found': issues_found,
        'detailed_results': results,
        'recommendation': get_recommendation(authenticity, issues_found)
    }


def check_ai_artifacts(image_path: str) -> float:
    """
    Check for AI generation artifacts
    
    Returns:
        Probability score (0-1) that image is AI-generated
    """
    try:
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # Check for common AI artifacts
        score = 0.0
        checks = 0
        
        # 1. Check for unnatural smoothness (AI images often too smooth)
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
            variance = np.var(gray)
            if variance < 500:  # Very smooth
                score += 0.3
            checks += 1
        
        # 2. Check for repetitive patterns (AI generation artifact)
        if has_repetitive_patterns(img_array):
            score += 0.4
            checks += 1
        
        # 3. Check for impossible details (too perfect)
        if has_impossible_details(img_array):
            score += 0.3
            checks += 1
        
        return min(score, 1.0)
        
    except Exception as e:
        print(f"Error checking AI artifacts: {e}")
        return 0.0


def detect_photoshop_traces(image_path: str) -> float:
    """
    Detect traces of photo editing software
    
    Returns:
        Probability score (0-1) of manipulation
    """
    try:
        img = Image.open(image_path)
        
        score = 0.0
        
        # Check EXIF for editing software
        exif_data = get_exif_data(img)
        if exif_data:
            software = exif_data.get('Software', '').lower()
            if 'photoshop' in software or 'gimp' in software or 'paint' in software:
                score += 0.5
            
            # Check for multiple save operations
            if 'edit' in software or 'modified' in software:
                score += 0.2
        
        # Check for compression artifacts inconsistencies
        if has_compression_inconsistencies(img):
            score += 0.3
        
        return min(score, 1.0)
        
    except Exception as e:
        print(f"Error detecting photoshop traces: {e}")
        return 0.0


def check_exif_manipulation(image_path: str) -> float:
    """
    Check for EXIF metadata tampering
    
    Returns:
        Probability score (0-1) of tampering
    """
    try:
        img = Image.open(image_path)
        exif_data = get_exif_data(img)
        
        if not exif_data:
            return 0.7  # No EXIF data is suspicious for modern cameras
        
        score = 0.0
        
        # Check for missing expected fields
        expected_fields = ['DateTime', 'Make', 'Model']
        missing_fields = sum(1 for field in expected_fields if field not in exif_data)
        score += missing_fields * 0.2
        
        # Check for date inconsistencies
        if 'DateTime' in exif_data and 'DateTimeOriginal' in exif_data:
            if exif_data['DateTime'] != exif_data['DateTimeOriginal']:
                score += 0.3
        
        # Check for impossible camera settings
        if has_impossible_camera_settings(exif_data):
            score += 0.3
        
        return min(score, 1.0)
        
    except Exception as e:
        print(f"Error checking EXIF: {e}")
        return 0.0


def check_lighting_physics(image_path: str) -> float:
    """
    Check for lighting and physics consistency
    
    Returns:
        Consistency score (0-1, higher is more consistent)
    """
    try:
        img = Image.open(image_path)
        img_array = np.array(img)
        
        if len(img_array.shape) != 3:
            return 0.5  # Can't analyze grayscale
        
        score = 1.0
        
        # Check for inconsistent shadows
        if has_inconsistent_shadows(img_array):
            score -= 0.3
        
        # Check for unnatural color distribution
        if has_unnatural_colors(img_array):
            score -= 0.2
        
        # Check for impossible reflections
        if has_impossible_reflections(img_array):
            score -= 0.3
        
        return max(score, 0.0)
        
    except Exception as e:
        print(f"Error checking lighting: {e}")
        return 0.5


def check_duplicate_regions(image_path: str) -> float:
    """
    Check for cloned/duplicated regions (clone stamp tool)
    
    Returns:
        Probability score (0-1) of duplication
    """
    try:
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # Simple duplicate detection using block matching
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array
        
        # Check for duplicate blocks
        block_size = 16
        duplicates_found = 0
        total_blocks = 0
        
        h, w = gray.shape
        for i in range(0, h - block_size, block_size):
            for j in range(0, w - block_size, block_size):
                block = gray[i:i+block_size, j:j+block_size]
                
                # Compare with other blocks
                for ii in range(i + block_size, h - block_size, block_size):
                    for jj in range(0, w - block_size, block_size):
                        other_block = gray[ii:ii+block_size, jj:jj+block_size]
                        
                        # Calculate similarity
                        diff = np.mean(np.abs(block - other_block))
                        if diff < 5:  # Very similar
                            duplicates_found += 1
                
                total_blocks += 1
        
        if total_blocks > 0:
            duplicate_ratio = duplicates_found / total_blocks
            return min(duplicate_ratio * 2, 1.0)
        
        return 0.0
        
    except Exception as e:
        print(f"Error checking duplicates: {e}")
        return 0.0


def calculate_authenticity_score(results: dict) -> float:
    """
    Calculate overall authenticity score from individual checks
    
    Args:
        results: Dictionary of check results
    
    Returns:
        Overall authenticity score (0-1, higher is more authentic)
    """
    # Weight different factors
    weights = {
        'ai_generated_probability': -0.4,  # Negative because higher = less authentic
        'manipulation_detected': -0.3,
        'metadata_tampering': -0.2,
        'consistency_score': 0.5,  # Positive because higher = more authentic
        'duplicate_detection': -0.2
    }
    
    score = 1.0  # Start at fully authentic
    
    for key, weight in weights.items():
        if key in results:
            score += weight * results[key]
    
    return max(0.0, min(1.0, score))


def get_recommendation(authenticity_score: float, issues: List[str]) -> str:
    """Generate recommendation based on analysis"""
    
    if authenticity_score > 0.8:
        return "Photo appears authentic. Proceed with claim processing."
    elif authenticity_score > 0.6:
        return "Minor concerns detected. Recommend manual review of photo."
    elif authenticity_score > 0.4:
        return "Moderate manipulation detected. Recommend SIU investigation."
    else:
        return "High probability of manipulation or AI generation. Flag for immediate investigation."


# Helper functions

def get_exif_data(img: Image) -> dict:
    """Extract EXIF data from image"""
    exif_data = {}
    try:
        exif = img._getexif()
        if exif:
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value
    except:
        pass
    return exif_data


def has_repetitive_patterns(img_array: np.ndarray) -> bool:
    """Check for repetitive patterns (AI artifact)"""
    # Simplified check - in production, use FFT analysis
    if len(img_array.shape) == 3:
        gray = np.mean(img_array, axis=2)
    else:
        gray = img_array
    
    # Check for high frequency repetition
    variance = np.var(gray)
    return variance < 300


def has_impossible_details(img_array: np.ndarray) -> bool:
    """Check for impossibly perfect details"""
    # Simplified - check for unnatural sharpness
    if len(img_array.shape) == 3:
        edges = np.sum(np.abs(np.diff(img_array, axis=0))) + np.sum(np.abs(np.diff(img_array, axis=1)))
        return edges > img_array.size * 100
    return False


def has_compression_inconsistencies(img: Image) -> bool:
    """Check for inconsistent compression levels"""
    # Simplified check
    try:
        quality = img.info.get('quality', 95)
        return quality < 70  # Low quality might indicate re-compression
    except:
        return False


def has_impossible_camera_settings(exif_data: dict) -> bool:
    """Check for impossible camera settings"""
    # Check for unrealistic values
    if 'FNumber' in exif_data:
        f_number = float(exif_data['FNumber'])
        if f_number < 0.5 or f_number > 64:
            return True
    
    if 'ISOSpeedRatings' in exif_data:
        iso = int(exif_data['ISOSpeedRatings'])
        if iso < 25 or iso > 102400:
            return True
    
    return False


def has_inconsistent_shadows(img_array: np.ndarray) -> bool:
    """Check for inconsistent shadow directions"""
    # Simplified - in production, use shadow analysis
    return False  # Placeholder


def has_unnatural_colors(img_array: np.ndarray) -> bool:
    """Check for unnatural color distribution"""
    # Check for oversaturation
    if len(img_array.shape) == 3:
        saturation = np.std(img_array)
        return saturation > 80  # Very high saturation
    return False


def has_impossible_reflections(img_array: np.ndarray) -> bool:
    """Check for physically impossible reflections"""
    # Placeholder for advanced analysis
    return False


# Streamlit integration
def display_deepfake_analysis(image_path: str, image_name: str = "Photo"):
    """
    Display deepfake analysis in Streamlit
    
    Args:
        image_path: Path to image file
        image_name: Display name for image
    """
    import streamlit as st
    
    st.markdown(f"### 🤖 Photo Authenticity Analysis: {image_name}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Display image
        st.image(image_path, caption=image_name, use_container_width=True)
    
    with col2:
        # Run analysis
        with st.spinner("🔍 Analyzing photo for manipulation..."):
            results = detect_photo_manipulation(image_path)
        
        # Display authenticity score
        authenticity = results['authenticity_score']
        
        # Color based on score
        if authenticity > 0.8:
            color = "#4CAF50"
            status = "✅ AUTHENTIC"
        elif authenticity > 0.6:
            color = "#FF9800"
            status = "⚠️ MINOR CONCERNS"
        elif authenticity > 0.4:
            color = "#FF5722"
            status = "⚠️ SUSPICIOUS"
        else:
            color = "#D32F2F"
            status = "🚨 LIKELY MANIPULATED"
        
        st.markdown(f"""
        <div style='background: rgba(0,0,0,0.5);
                    border-left: 5px solid {color};
                    padding: 1.5rem;
                    border-radius: 8px;
                    margin-bottom: 1rem;'>
            <h2 style='color: {color}; margin: 0 0 1rem 0;'>{status}</h2>
            <h1 style='color: {color}; margin: 0; font-size: 3rem;'>
                {authenticity*100:.0f}%
            </h1>
            <p style='color: #B0B0B0; margin: 0.5rem 0 0 0;'>Authenticity Score</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display issues found
        if results['issues_found']:
            st.markdown("**⚠️ Issues Detected:**")
            for issue in results['issues_found']:
                st.markdown(f"- {issue}")
        else:
            st.success("✅ No manipulation detected")
        
        # Recommendation
        st.markdown(f"""
        <div style='background: rgba(255, 87, 87, 0.15);
                    border: 2px solid {color};
                    padding: 1rem;
                    border-radius: 8px;
                    margin-top: 1rem;'>
            <strong>Recommendation:</strong><br>
            {results['recommendation']}
        </div>
        """, unsafe_allow_html=True)
    
    # Detailed analysis
    with st.expander("📊 Detailed Analysis Results"):
        detailed = results['detailed_results']
        
        metrics_col1, metrics_col2 = st.columns(2)
        
        with metrics_col1:
            st.metric("AI Generation Probability", f"{detailed['ai_generated_probability']*100:.0f}%")
            st.metric("Manipulation Detection", f"{detailed['manipulation_detected']*100:.0f}%")
            st.metric("Metadata Tampering", f"{detailed['metadata_tampering']*100:.0f}%")
        
        with metrics_col2:
            st.metric("Lighting Consistency", f"{detailed['consistency_score']*100:.0f}%")
            st.metric("Duplicate Regions", f"{detailed['duplicate_detection']*100:.0f}%")
            st.metric("Overall Confidence", f"{results['confidence']*100:.0f}%")


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        results = detect_photo_manipulation(image_path)
        
        print("\n" + "="*60)
        print("PHOTO AUTHENTICITY ANALYSIS")
        print("="*60)
        print(f"Image: {image_path}")
        print(f"Authentic: {'YES' if results['authentic'] else 'NO'}")
        print(f"Authenticity Score: {results['authenticity_score']*100:.1f}%")
        print(f"Confidence: {results['confidence']*100:.1f}%")
        print(f"\nIssues Found:")
        for issue in results['issues_found']:
            print(f"  - {issue}")
        print(f"\nRecommendation: {results['recommendation']}")
        print("="*60)
    else:
        print("Usage: python deepfake_detector.py <image_path>")

