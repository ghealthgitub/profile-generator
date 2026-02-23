"""
🫚 GINGER UNIVERSE - Dictionary Matcher
Matches doctor to procedures from database
"""

def match_procedures(doctor_data, procedures_db):
    """
    Matches doctor information to procedures in database
    
    Args:
        doctor_data: Extracted doctor information
        procedures_db: List of procedures from Google Sheets
        
    Returns:
        list: Matched procedures with relevance scores
    """
    matched = []
    
    # Combine all doctor text for matching
    doctor_text = ' '.join([
        doctor_data.get('full_text', ''),
        ' '.join(doctor_data.get('specialties', [])),
        ' '.join(doctor_data.get('qualifications', []))
    ]).lower()
    
    # Match procedures
    for procedure in procedures_db:
        # Get procedure details
        proc_name = str(procedure.get('Entity_Name', '')).lower()
        specialty = str(procedure.get('Top_Specialty', '')).lower()
        sub_specialty = str(procedure.get('Sub_Specialty', '')).lower()
        
        # Calculate relevance score
        score = 0
        
        # Check if procedure name appears in doctor text
        if proc_name in doctor_text:
            score += 10
        
        # Check if specialty matches
        if specialty in doctor_text:
            score += 5
        
        # Check if sub-specialty matches
        if sub_specialty in doctor_text:
            score += 3
        
        # Check for keywords
        keywords = proc_name.split()
        for keyword in keywords:
            if len(keyword) > 3 and keyword in doctor_text:
                score += 1
        
        if score > 0:
            matched.append({
                'procedure': procedure.get('Entity_Name'),
                'specialty': procedure.get('Top_Specialty'),
                'sub_specialty': procedure.get('Sub_Specialty'),
                'complexity': procedure.get('Complexity_Level'),
                'score': score
            })
    
    # Sort by score (highest first)
    matched.sort(key=lambda x: x['score'], reverse=True)
    
    # Return top 15 matches
    return matched[:15]
