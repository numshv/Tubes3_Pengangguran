import re
import pdfplumber

def flatten_file_for_pattern_matching(file_path):
    try:
        full_text = ''
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                full_text += page.extract_text() + ' '

        # Flatten all whitespace into single space
        flat_text = re.sub(r'\s+', ' ', full_text)
        return flat_text.strip()
    
    except FileNotFoundError:
        return "Error: File not found."
    except Exception as e:
        return f"Error: {e}"

def flatten_file_for_regex(pdf_path: str) -> str:
    """
    Extracts text from PDF while preserving structure and newlines.
    Only removes bullet characters, keeping everything else as-is.
    Handles multi-column layouts properly.
    """
    full_text = ""
    bullet_chars = ['•', '●', '-', '▪', '◦', '▫', '‣', '*']
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract text while preserving layout
            text = page.extract_text(layout=True, x_tolerance=3, y_tolerance=3)
            
            if not text:
                continue
            
            lines = text.split('\n')
            
            for line in lines:
                # Keep original line structure, just process bullet points
                if line.strip():  # Only process non-empty lines
                    processed_line = remove_bullet_chars(line, bullet_chars)
                    full_text += processed_line + '\n'
                else:
                    # Preserve empty lines
                    full_text += '\n'
    
    return full_text.strip()

def remove_bullet_chars(line: str, bullet_chars: list) -> str:
    """
    Remove bullet characters from the beginning of a line while preserving spacing.
    """
    stripped = line.lstrip()  # Remove leading whitespace temporarily
    leading_spaces = line[:len(line) - len(stripped)]  # Capture original indentation
    
    # Check if line starts with any bullet character
    for bullet in bullet_chars:
        if stripped.startswith(bullet):
            # Remove bullet and any immediately following spaces
            content = stripped[len(bullet):].lstrip()
            # Return with original indentation
            return leading_spaces + content
    
    # If no bullet found, return original line
    return line

# Alternative version with more explicit multi-column handling
def flatten_file_for_regex_multicolumn(pdf_path: str) -> str:
    """
    Alternative version with explicit multi-column detection.
    Use this if the simple version doesn't handle columns well.
    """
    full_text = ""
    bullet_chars = ['•', '●', '-', '▪', '◦', '▫', '‣', '*']
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Try to detect if page has multiple columns
            page_width = page.width
            
            # Extract with different settings for better column handling
            try:
                # First try with layout preservation
                text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=3)
                
                if not text:
                    # Fallback to regular extraction
                    text = page.extract_text()
                
                if text:
                    lines = text.split('\n')
                    
                    for line in lines:
                        if line.strip():
                            processed_line = remove_bullet_chars(line, bullet_chars)
                            full_text += processed_line + '\n'
                        else:
                            full_text += '\n'
                            
            except Exception:
                # Final fallback - basic extraction
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        if line.strip():  # Only process non-empty lines
                            processed_line = remove_bullet_chars(line, bullet_chars)
                            full_text += processed_line + '\n'
                        else:
                            full_text += '\n'
    
    return full_text.strip()

# Example usage
if __name__ == "__main__":
    file_path = input("Enter the relative path to your file: ").strip()
    result = flatten_file_for_regex_multicolumn(file_path)
    print(result)
