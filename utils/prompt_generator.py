"""
🫚 GINGER UNIVERSE - Prompt Generator
Creates perfect prompts for Claude AI
"""

def generate_claude_prompt(doctor_data, matched_procedures):
    """
    Generates optimized prompt for Claude AI
    
    Args:
        doctor_data: Extracted doctor information
        matched_procedures: List of matched procedures
        
    Returns:
        str: Complete prompt for Claude
    """
    
    # Build procedure list
    procedure_list = "\n".join([
        f"- {p['procedure']} ({p['specialty']} - {p['sub_specialty']})"
        for p in matched_procedures[:10]  # Top 10
    ])
    
    prompt = f"""You are a professional medical content writer for Ginger Universe, a healthcare information platform.

TASK: Create a comprehensive, professional doctor profile based on the information provided.

DOCTOR INFORMATION EXTRACTED:
- Name: {doctor_data.get('name', 'Not found')}
- Specialties: {', '.join(doctor_data.get('specialties', ['Not specified']))}
- Qualifications: {', '.join(doctor_data.get('qualifications', ['Not specified']))}
- Experience: {doctor_data.get('experience', 'Not specified')}
- Hospital Affiliations: {', '.join(doctor_data.get('hospitals', ['Not specified']))}

MATCHED MEDICAL PROCEDURES FROM DATABASE:
{procedure_list if procedure_list else 'No specific procedures matched'}

ADDITIONAL CONTEXT FROM WEBPAGE:
{doctor_data.get('full_text', '')[:1500]}

---

Please create a professional doctor profile with the following structure:

**PROFESSIONAL SUMMARY**
Write a compelling 2-3 paragraph professional summary that:
- Introduces the doctor professionally
- Highlights key specializations and expertise
- Mentions years of experience and notable achievements
- Uses a warm, professional tone suitable for patients

**SPECIALIZATIONS**
List the doctor's main medical specialties (bullet points)

**PROCEDURES & EXPERTISE**
List specific medical procedures the doctor performs, matching from the database provided above (bullet points, maximum 10-12 procedures)

**EDUCATION & QUALIFICATIONS**
List academic degrees, certifications, and professional qualifications (bullet points)

**PROFESSIONAL EXPERIENCE**
Describe the doctor's career journey, key positions, and years of experience (2-3 sentences)

**HOSPITAL AFFILIATIONS**
List hospitals or medical centers where the doctor practices (bullet points)

**AWARDS & RECOGNITION** (if information available)
List any awards, publications, or recognition (bullet points, or write "Information not available" if none found)

---

IMPORTANT GUIDELINES:
1. Be factual and professional - only include information that can be verified from the provided data
2. If certain information is not available, write "Information not available" for that section
3. Use clear, patient-friendly language while maintaining medical accuracy
4. Keep the tone warm and trustworthy
5. Format with clear headings and bullet points for easy reading
6. Do NOT invent or assume information not provided
7. Total length should be 400-600 words

Please generate the doctor profile now."""

    return prompt
