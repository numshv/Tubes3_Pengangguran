import os
import re
import fitz  # PyMuPDF
# ... (all your existing constants and regex patterns remain here) ...

# --- Constants ---
SIMILARITY_THRESHOLD = 0.75

# --- Regex Patterns for Information Extraction ---
NAME_REGEX = re.compile(
    r"^(?:[A-Z][a-z'-]+(?: [A-Z][a-z'-]+){1,3}|[A-Z][A-Z'-]+(?: [A-Z][A-Z'-]+){1,3})(?:\s+[A-Z]\.?)?(?=\s*\n|\s*Email|Contact|Phone|Mobile|$)",
    re.MULTILINE
)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}(?:[-.\s]?\d{1,4})?")
SUMMARY_SECTION_REGEX = re.compile(
    r"^(SUMMARY|OBJECTIVE|PROFILE|ABOUT\s?ME|PROFESSIONAL\sSUMMARY)\s*:?\n?((?:.|\n)*?)(?=\n\s*(?:EXPERIENCE|EDUCATION|SKILLS|PROJECTS|WORK\sHISTORY|TECHNICAL\sSKILLS)|$)",
    re.IGNORECASE | re.MULTILINE
)
SKILLS_SECTION_REGEX = re.compile(
    r"^(SKILLS|TECHNICAL\sSKILLS|EXPERTISE|PROFICIENCIES)\s*:?\n?((?:.|\n)*?)(?=\n\s*(?:EXPERIENCE|EDUCATION|PROJECTS|WORK\sHISTORY|AWARDS)|$)",
    re.IGNORECASE | re.MULTILINE
)
EXPERIENCE_SECTION_REGEX = re.compile(
    r"^(EXPERIENCE|WORK\sHISTORY|EMPLOYMENT\sHISTORY|PROFESSIONAL\sEXPERIENCE)\s*:?\n?((?:.|\n)*?)(?=\n\s*(?:EDUCATION|SKILLS|PROJECTS|AWARDS|CERTIFICATIONS)|$)",
    re.IGNORECASE | re.MULTILINE
)
EDUCATION_SECTION_REGEX = re.compile(
    r"^(EDUCATION|QUALIFICATIONS|ACADEMIC\sBACKGROUND)\s*:?\n?((?:.|\n)*?)(?=\n\s*(?:EXPERIENCE|SKILLS|PROJECTS|WORK\sHISTORY|AWARDS)|$)",
    re.IGNORECASE | re.MULTILINE
)

# --- PDF Processing ---
def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""

# --- String Similarity ---
def levenshtein_distance(s1, s2):
    s1 = s1.lower()
    s2 = s2.lower()
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def is_similar(text1, text2, threshold=SIMILARITY_THRESHOLD):
    if not text1 or not text2:
        return False
    distance = levenshtein_distance(text1, text2)
    len1, len2 = len(text1), len(text2)
    if max(len1, len2) == 0: 
        return True 
    similarity_score = 1 - (distance / max(len1, len2))
    return similarity_score >= threshold

# --- Information Extraction ---
def extract_name(text):
    match = NAME_REGEX.search(text)
    if match:
        return match.group(0).strip()
    lines = text.split('\n')
    for line in lines[:5]: 
        line = line.strip()
        if re.match(r"^([A-Z][a-z'-]+(?:\s+[A-Z][a-z'-]+){1,3})(?:\s+[A-Z]\.?)?$", line):
            if len(line.split()) <= 4: 
                if not any(header.lower() in line.lower() for header in ["SUMMARY", "OBJECTIVE", "EXPERIENCE", "EDUCATION", "SKILLS", "CONTACT"]):
                    return line
    return None

def extract_emails(text):
    return list(set(EMAIL_REGEX.findall(text))) 

def extract_phones(text):
    return list(set(PHONE_REGEX.findall(text)))

def extract_section_content(text, section_regex):
    match = section_regex.search(text)
    if match and len(match.groups()) > 1:
        content = match.group(2).strip()
        title_in_content_match = re.match(r"^(SUMMARY|OBJECTIVE|PROFILE|ABOUT\s?ME|PROFESSIONAL\sSUMMARY|SKILLS|TECHNICAL\sSKILLS|EXPERTISE|PROFICIENCIES|EXPERIENCE|WORK\sHISTORY|EMPLOYMENT\sHISTORY|PROFESSIONAL\sEXPERIENCE|EDUCATION|QUALIFICATIONS|ACADEMIC\sBACKGROUND)\s*:?\n?", content, re.IGNORECASE)
        if title_in_content_match:
            content = content[len(title_in_content_match.group(0)):].strip()
        return content
    return None

def extract_summary_overview(text):
    return extract_section_content(text, SUMMARY_SECTION_REGEX)

def extract_skills_section(text):
    skills_block = extract_section_content(text, SKILLS_SECTION_REGEX)
    if skills_block:
        skills_list = []
        potential_skills = re.split(r'\n|\s*,\s*|\s*•\s*|\s*-\s*|\s*\|\s*', skills_block)
        for skill in potential_skills:
            skill = skill.strip()
            if skill and len(skill) > 1 and len(skill) < 50: 
                if len(skill.split()) < 5:
                    skills_list.append(skill)
        return list(set(s for s in skills_list if s)) 
    return []

def extract_experience_section(text):
    return extract_section_content(text, EXPERIENCE_SECTION_REGEX)

def extract_education_section(text):
    return extract_section_content(text, EDUCATION_SECTION_REGEX)

def extract_all_info(text_content, cv_id="N/A", category="N/A"):
    name = extract_name(text_content)
    if not name: 
        name = f"Applicant {category}-{cv_id}"
    return {
        'name': name,
        'emails': extract_emails(text_content),
        'phones': extract_phones(text_content),
        'summary_overview': extract_summary_overview(text_content),
        'skills_list': extract_skills_section(text_content),
        'experience_section': extract_experience_section(text_content),
        'education_section': extract_education_section(text_content),
    }

# --- Data Loading (with progress_callback) ---
def load_cv_data(cv_root_dir="data", max_files_per_category=20, progress_callback=None):
    """
    Loads CV data from the specified directory structure.
    Calls progress_callback after each category is about to be processed.
    """
    all_cv_data = []
    if not os.path.isdir(cv_root_dir):
        print(f"Error: CV root directory '{cv_root_dir}' not found.")
        if progress_callback:
            progress_callback(0, 0, "Error: CV root directory not found", is_error=True)
        return all_cv_data

    try:
        categories = sorted([d for d in os.listdir(cv_root_dir) if os.path.isdir(os.path.join(cv_root_dir, d))])
    except Exception as e:
        print(f"Error listing categories in '{cv_root_dir}': {e}")
        if progress_callback:
            progress_callback(0, 0, f"Error listing categories: {e}", is_error=True)
        return all_cv_data
        
    total_categories = len(categories)
    if total_categories == 0:
        print(f"No categories found in '{cv_root_dir}'.")
        if progress_callback:
            progress_callback(0, 0, "No categories found", is_complete=True) # Indicate completion even if no categories
        return all_cv_data

    for i, category in enumerate(categories):
        if progress_callback:
            # Call callback before processing files for this category
            progress_callback(i, total_categories, category) # current_index, total, name

        category_path = os.path.join(cv_root_dir, category)
        
        try:
            pdf_files = sorted([f for f in os.listdir(category_path) if f.lower().endswith('.pdf')])
        except FileNotFoundError:
            print(f"Warning: Category path {category_path} not found or not accessible. Skipping.")
            continue # Skip to next category
            
        files_to_process = pdf_files[:max_files_per_category]
        print(f"Processing category: {category} ({i+1}/{total_categories}) - {len(files_to_process)} files")

        for pdf_file in files_to_process:
            file_path = os.path.join(category_path, pdf_file)
            cv_id = os.path.splitext(pdf_file)[0]
            
            text_content = extract_text_from_pdf(file_path)
            
            if not text_content:
                print(f"    Warning: Could not extract text from {pdf_file} in category {category}. Skipping.")
                continue

            extracted_info = extract_all_info(text_content, cv_id, category)
            
            cv_entry = {
                'id': cv_id,
                'display_name': extracted_info['name'],
                'filepath': file_path,
                'category': category,
                'text_content': text_content,
                'extracted_details': extracted_info 
            }
            all_cv_data.append(cv_entry)
            
    if progress_callback: # Final call to indicate completion
        progress_callback(total_categories, total_categories, "All categories processed", is_complete=True)

    print(f"Total CVs loaded: {len(all_cv_data)}")
    return all_cv_data

# This block is only for testing utils.py directly
if __name__ == '__main__':
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_script_dir)
    project_root_for_utils_test = os.path.dirname(src_dir)
    data_directory_for_utils_test = os.path.join(project_root_for_utils_test, "data")
    
    def test_progress_callback(current, total, name, is_error=False, is_complete=False):
        if is_error:
            print(f"TEST CALLBACK ERROR: {name}")
        elif is_complete:
            print(f"TEST CALLBACK COMPLETE: {name} ({current}/{total})")
        else:
            print(f"TEST CALLBACK: Processing category {name} ({current+1}/{total})")

    print(f"--- Testing utils.py directly ---")
    print(f"Looking for CVs in: {data_directory_for_utils_test}")
    
    loaded_cvs = load_cv_data(
        cv_root_dir=data_directory_for_utils_test,
        max_files_per_category=2,
        progress_callback=test_progress_callback # Pass the test callback
    )

    if loaded_cvs:
        print(f"\n--- Example of Loaded CV Data (First CV from utils.py test) ---")
        # ... (rest of your test print statements)
    else:
        print("No CVs were loaded during utils.py test.")

