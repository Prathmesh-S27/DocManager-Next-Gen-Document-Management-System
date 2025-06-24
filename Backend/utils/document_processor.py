import os
import io
import google.generativeai as genai
from PIL import Image
import pandas as pd
import PyPDF2
import docx
import json
import base64

# Configure the Gemini API key
GEMINI_API_KEY = "#"  # Replace with your actual API key
genai.configure(api_key=GEMINI_API_KEY)

# Set up the generative model
generation_config = {
    "temperature": 0.1,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 2048,
}

# Update the model initialization section in document_processor.py
try:
    # Setup text model
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",  # Updated to recommended model
        generation_config=generation_config
    )
    
    # Update vision model to use gemini-1.5-flash which supports both text and vision
    vision_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",  # Updated from deprecated gemini-pro-vision
        generation_config=generation_config
    )
    print("Using Gemini 1.5 Flash models")
except Exception as e:
    print(f"Error with Gemini models: {str(e)}")
    # Set to None, application will handle accordingly
    model = None
    vision_model = None

def extract_text_from_excel(file_stream, file_extension):
    """Extract text content from Excel files (xls, xlsx, csv)"""
    try:
        # Reset the file pointer
        file_stream.seek(0)
        
        # Use pandas to read the Excel file
        if file_extension == 'csv':
            df = pd.read_csv(file_stream)
        else:  # xlsx or xls
            df = pd.read_excel(file_stream)
        
        # Convert dataframe to string representation
        text_content = []
        
        # Add column headers
        text_content.append(" | ".join(df.columns.astype(str)))
        
        # Add rows (limit to first 100 rows for large files)
        max_rows = min(100, len(df))
        for i in range(max_rows):
            row = df.iloc[i]
            text_content.append(" | ".join(row.astype(str)))
        
        # If there are more rows, indicate truncation
        if len(df) > max_rows:
            text_content.append(f"... (truncated, showing {max_rows} of {len(df)} rows)")
            
        # Join all lines with newlines
        return "\n".join(text_content)
    except Exception as e:
        print(f"Error extracting text from Excel: {str(e)}")
        return f"Error extracting Excel content: {str(e)}"

def extract_text_from_pdf(file_stream):
    """Extract text content from PDF files"""
    try:
        # Reset the file pointer
        file_stream.seek(0)
        
        # Use PyPDF2 to extract text - updated to use PdfReader instead of deprecated PdfFileReader
        pdf_reader = PyPDF2.PdfReader(file_stream)
        text_content = []
        
        # Extract text from each page (limit to first 20 pages for large PDFs)
        max_pages = min(20, len(pdf_reader.pages))
        for page_num in range(max_pages):
            page = pdf_reader.pages[page_num]
            text_content.append(page.extract_text())
            
        # If there are more pages, indicate truncation
        if len(pdf_reader.pages) > max_pages:
            text_content.append(f"... (truncated, showing {max_pages} of {len(pdf_reader.pages)} pages)")
            
        # Join all pages with newlines
        return "\n\n".join(text_content)
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return f"Error extracting PDF content: {str(e)}"

def extract_text_from_docx(file_stream):
    """Extract text content from Word documents"""
    try:
        # Reset the file pointer
        file_stream.seek(0)
        
        # Use python-docx to extract text
        doc = docx.Document(file_stream)
        text_content = []
        
        # Extract text from each paragraph
        for para in doc.paragraphs:
            if para.text.strip():  # Skip empty paragraphs
                text_content.append(para.text)
                
        # Join all paragraphs with newlines
        return "\n".join(text_content)
    except Exception as e:
        print(f"Error extracting text from DOCX: {str(e)}")
        return f"Error extracting Word document content: {str(e)}"

def process_image_with_gemini(file_stream):
    """Process image files with Gemini Vision model"""
    try:
        if vision_model is None:
            return {
                "description": "Image processing unavailable. AI model not initialized.",
                "keywords": ["image"],
                "text_content": ""
            }
        
        # Reset file pointer and open image
        file_stream.seek(0)
        image = Image.open(file_stream)
        
        # Use Gemini Vision model to analyze the image
        prompt = """
        Analyze this image in detail and provide the following:
        1. A detailed description of what you see
        2. Any text content visible in the image
        3. A list of relevant keywords that describe the image content
        
        Format your response as a JSON object with these keys:
        {
            "description": "detailed description here",
            "text_content": "any text visible in the image",
            "keywords": ["keyword1", "keyword2", "keyword3", etc.]
        }
        """
        
        # Convert image to appropriate format for the model
        response = vision_model.generate_content([prompt, image])
        
        # Parse response as JSON
        try:
            result_text = response.text
            
            # Extract JSON portion if response contains markdown code blocks
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            
            # Handle non-JSON response
            if not (result_text.startswith('{') and result_text.endswith('}')):
                # Try to extract just the JSON part
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result_text = result_text[json_start:json_end]
                else:
                    # Create a simple JSON structure from plain text response
                    return {
                        "description": result_text[:500],
                        "keywords": ["image"],
                        "text_content": ""
                    }
                
            # Parse the JSON
            result = json.loads(result_text)
            
            # Ensure all expected keys exist
            if "keywords" not in result:
                result["keywords"] = ["image"]
            if "description" not in result:
                result["description"] = "Image analysis completed"
            if "text_content" not in result:
                result["text_content"] = ""
                
            return result
            
        except json.JSONDecodeError as json_error:
            print(f"Error parsing JSON from Gemini response: {str(json_error)}")
            # Create a basic response
            return {
                "description": response.text[:500],  # Take first 500 chars of raw response
                "keywords": ["image"],
                "text_content": ""
            }
            
    except Exception as e:
        print(f"Error processing image with Gemini: {str(e)}")
        return {
            "description": "Error processing image",
            "keywords": ["image"],
            "text_content": ""
        }

def process_text_with_gemini(text):
    """Process text content with Gemini model"""
    try:
        if model is None:
            return {
                "summary": "Text processing unavailable. AI model not initialized.",
                "keywords": ["document"],
                "topics": []
            }
        
        # Trim text if it's too long
        max_length = 10000  # Adjust based on model's context window
        text_for_analysis = text[:max_length]
        if len(text) > max_length:
            text_for_analysis += "\n...(content truncated)..."
        
        prompt = f"""
        Analyze the following document text thoroughly and provide:

        1. SUMMARY:
           Create a well-structured summary (250-350 words) organized into 2-3 paragraphs that:
           - Begins with a clear overview of the document's main purpose
           - Highlights key findings, arguments, or data points in the middle
           - Concludes with implications or next steps mentioned in the document
           - Uses professional language appropriate for business documentation

        2. KEYWORDS:
           Extract 12-15 specific keywords/phrases that:
           - Precisely represent the document's core concepts and terminology
           - Include technical terms specific to the document's domain
           - Capture proper nouns (people, organizations, products) if present
           - Reflect both major themes and important details
           - Could be used to find this document in a search system

        3. MAIN TOPICS:
           Identify 3-5 primary topics or themes that:
           - Represent the document's major sections or subject areas
           - Are expressed as brief phrases (2-4 words each)
           - Could serve as section headings in a table of contents

        Format your response STRICTLY as a clean, properly-formatted JSON object with these keys:
        {{
            "summary": "your comprehensive summary here",
            "keywords": ["keyword1", "keyword2", "keyword3", ...],
            "topics": ["topic1", "topic2", "topic3", ...]
        }}

        Here is the document text to analyze:

        {text_for_analysis}
        """
        
        # Get response from model
        response = model.generate_content(prompt)
        
        # Parse response as JSON
        try:
            result_text = response.text
            
            # Extract JSON portion if response contains markdown code blocks
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            elif "```" in result_text:
                json_start = result_text.find("```") + 3
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            
            # Handle non-JSON response
            if not (result_text.startswith('{') and result_text.endswith('}')):
                # Try to extract just the JSON part
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result_text = result_text[json_start:json_end]
                else:
                    # Create a simple JSON structure from plain text response
                    return {
                        "summary": result_text[:500],
                        "keywords": ["document"],
                        "topics": []
                    }
            
            # Parse the JSON
            result = json.loads(result_text)
            
            # Ensure all expected keys exist
            if "summary" not in result:
                result["summary"] = "Document analysis completed"
            if "keywords" not in result:
                result["keywords"] = ["document"]
            if "topics" not in result:
                result["topics"] = []
                
            return result
            
        except json.JSONDecodeError as json_error:
            print(f"Error parsing JSON from Gemini response: {str(json_error)}")
            # Create a basic response
            return {
                "summary": response.text[:500],  # Take first 500 chars of raw response
                "keywords": ["document"],
                "topics": []
            }
            
    except Exception as e:
        print(f"Error processing text with Gemini: {str(e)}")
        return {
            "summary": "Error processing document text",
            "keywords": ["document"],
            "topics": []
        }

def extract_basic_keywords(text, max_keywords=10):
    """Extract basic keywords from text without AI."""
    # Convert to lowercase and remove common punctuation
    text = text.lower()
    for char in ['.', ',', '!', '?', '(', ')', '[', ']', '{', '}', ':', ';', '"', "'"]:
        text = text.replace(char, ' ')
    
    # Split into words
    words = text.split()
    
    # Remove common stop words
    stop_words = {
        'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
        'when', 'where', 'how', 'who', 'which', 'this', 'that', 'these', 'those',
        'then', 'just', 'so', 'than', 'such', 'both', 'through', 'about', 'for',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'having', 'do', 'does', 'did', 'doing', 'to', 'from', 'by', 'with', 'of',
        'at', 'in', 'on', 'it', 'its', 'it\'s', 'they', 'them', 'their', 'theirs'
    }
    
    # Count word frequency
    word_count = {}
    for word in words:
        if len(word) > 3 and word not in stop_words:  # Only count words longer than 3 letters
            if word in word_count:
                word_count[word] += 1
            else:
                word_count[word] = 1
    
    # Sort by frequency and get top words
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    top_keywords = [word for word, count in sorted_words[:max_keywords] if count > 1]
    
    return top_keywords

def extract_keywords_from_filename(filename):
    """Extract meaningful keywords from filename"""
    # Remove extension
    name = os.path.splitext(filename)[0].lower()
    
    # Replace common separators with spaces
    for sep in ["_", "-", ".", "(", ")"]:
        name = name.replace(sep, " ")
        
    # Split into words
    words = name.split()
    
    # Filter out very short words and numbers-only words
    words = [word for word in words if len(word) > 2 and not word.isdigit()]
    
    # Remove common prefixes like IMG, DSC, etc.
    common_prefixes = ["img", "dsc", "pic", "photo", "image"]
    words = [word for word in words if word not in common_prefixes]
    
    return words

def analyze_image_colors(img):
    """Analyze dominant colors in an image"""
    try:
        # Resize image for faster processing
        img = img.resize((100, 100))
        # Convert to RGB if not already
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        # Get image colors
        colors = img.getcolors(10000)  # Get up to 10000 different colors
        if not colors:
            return None
            
        # Sort colors by count (most common first)
        sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)
        
        # Define basic color ranges
        color_ranges = {
            "red": ([150, 0, 0], [255, 100, 100]),
            "green": ([0, 150, 0], [100, 255, 100]),
            "blue": ([0, 0, 150], [100, 100, 255]),
            "yellow": ([150, 150, 0], [255, 255, 100]),
            "purple": ([128, 0, 128], [255, 0, 255]),
            "orange": ([255, 165, 0], [255, 200, 100]),
            "black": ([0, 0, 0], [50, 50, 50]),
            "white": ([200, 200, 200], [255, 255, 255]),
            "gray": ([100, 100, 100], [150, 150, 150])
        }
        
        # Count dominant colors
        color_counts = {}
        total_pixels = sum(count for count, _ in sorted_colors[:10])
        
        for count, color in sorted_colors[:10]:  # Check top 10 colors
            for name, (lower, upper) in color_ranges.items():
                if all(lower[i] <= color[i] <= upper[i] for i in range(3)):
                    color_counts[name] = color_counts.get(name, 0) + count
                    
        # Get dominant colors (more than 15% of image)
        dominant_colors = [name for name, count in color_counts.items() 
                          if count/total_pixels > 0.15]
        
        if dominant_colors:
            return {
                "description": f"Image contains predominantly {', '.join(dominant_colors)} colors",
                "keywords": dominant_colors + ["color", "colored"]
            }
        return None
    except Exception as e:
        print(f"Error analyzing colors: {str(e)}")
        return None

def process_image_with_enhanced_fallback(file_stream, filename):
    """Process image files with enhanced fallback when AI is unavailable"""
    try:
        # Reset file pointer and open image
        file_stream.seek(0)
        img = Image.open(file_stream)
        width, height = img.size
        mode = img.mode
        format_name = img.format
        
        # Extract basic metadata
        image_info = {
            "description": f"Image document ({format_name}, {width}x{height}, {mode} mode)",
            "text_content": f"Image dimensions: {width}x{height}, Format: {format_name}, Mode: {mode}"
        }
        
        # Extract more meaningful keywords from the filename
        filename_keywords = extract_keywords_from_filename(filename)
        orientation = "portrait" if height > width else "landscape"
        
        # Add basic image type keywords
        image_keywords = [format_name.lower(), "document", "image", orientation] + filename_keywords
        
        # Analyze colors in the image
        try:
            file_stream.seek(0)
            color_info = analyze_image_colors(img)
            if color_info:
                image_info["description"] += f". {color_info['description']}"
                image_keywords.extend(color_info["keywords"])
        except Exception as color_err:
            print(f"Error analyzing image colors: {str(color_err)}")
        
        # Add keywords to the result
        image_info["keywords"] = list(set(image_keywords))  # Remove duplicates
        
        return image_info
    except Exception as e:
        print(f"Error in enhanced image fallback: {str(e)}")
        return {
            "description": "Image document",
            "keywords": ["image", "document"],
            "text_content": ""
        }

def process_document(file_stream, file_extension):
    """Process an uploaded document based on its file type with robust fallback for API limits."""
    try:
        # Make a copy of the file stream for multiple reads
        file_bytes = file_stream.read()
        file_stream = io.BytesIO(file_bytes)
        
        # Extract text based on file type
        extracted_text = ""
        basic_keywords = [file_extension.lower(), "document"]
        
        # Process based on file type
        if file_extension in ['jpg', 'jpeg', 'png']:
            # For images, try to use AI but have robust fallback
            file_stream.seek(0)
            original_filename = getattr(file_stream, 'filename', f"image.{file_extension}")
            
            try:
                # Try to use AI for image analysis
                if vision_model is not None:
                    result = process_image_with_gemini(file_stream)
                    if result and result.get("keywords") and len(result.get("keywords")) > 2:
                        # Successful AI processing
                        print(f"AI processing completed for {file_extension} image")
                        return {
                            "summary": result.get("description", "Image document"),
                            "keywords": result.get("keywords", basic_keywords),
                            "topics": [],
                            "text_content": result.get("text_content", "")
                        }
            except Exception as img_err:
                print(f"Error in image AI processing, using fallback: {str(img_err)}")
            
            # Enhanced fallback for images
            file_stream.seek(0)
            result = process_image_with_enhanced_fallback(file_stream, original_filename)
            
            return {
                "summary": result.get("description", "Image document"),
                "keywords": result.get("keywords", basic_keywords),
                "topics": [],
                "text_content": result.get("text_content", "")
            }
            
        # Extract text from document based on file type    
        elif file_extension == 'pdf':
            file_stream.seek(0)
            extracted_text = extract_text_from_pdf(file_stream)
            basic_keywords.append("pdf")
        elif file_extension in ['doc', 'docx']:
            file_stream.seek(0)
            extracted_text = extract_text_from_docx(file_stream)
            basic_keywords.append("word")
            basic_keywords.append("document")
        elif file_extension in ['csv', 'xls', 'xlsx']:
            file_stream.seek(0)
            extracted_text = extract_text_from_excel(file_stream, file_extension)
            basic_keywords.append("spreadsheet")
            basic_keywords.append("data")
        elif file_extension == 'txt':
            file_stream.seek(0)
            extracted_text = file_stream.read().decode('utf-8')
            basic_keywords.append("text")
        else:
            return {
                "summary": f"Document with {file_extension} extension",
                "keywords": basic_keywords,
                "topics": [],
                "text_content": ""
            }
        
        # Try AI-based analysis for text but with robust fallback
        if extracted_text:
            # Save partial text content for search
            text_preview = extracted_text[:1000] if len(extracted_text) > 1000 else extracted_text
            
            # Try to extract additional keywords without AI
            additional_keywords = extract_basic_keywords(extracted_text)
            all_keywords = list(set(basic_keywords + additional_keywords))
            
            # Create a basic summary from the first paragraph
            first_para = extracted_text.split('\n\n')[0] if '\n\n' in extracted_text else extracted_text[:200]
            basic_summary = first_para[:200] + "..." if len(first_para) > 200 else first_para
            
            try:
                if model is not None:
                    # Try to use AI for text analysis
                    result = process_text_with_gemini(extracted_text)
                    if result.get("keywords") and len(result.get("keywords")) > 1:
                        # The AI succeeded, use its analysis
                        print(f"AI processing completed for {file_extension} document")
                        result["text_content"] = text_preview
                        return result
                    else:
                        # AI returned empty or minimal results, use our fallback
                        print(f"AI returned minimal results for {file_extension}, using fallback")
            except Exception as ai_err:
                print(f"Error processing text with AI, using fallback: {str(ai_err)}")
            
            # If we reach here, AI failed or is unavailable, use our basic extraction
            return {
                "summary": basic_summary,
                "keywords": all_keywords,
                "topics": [],
                "text_content": text_preview
            }
        else:
            return {
                "summary": f"No text content could be extracted from this {file_extension} document.",
                "keywords": basic_keywords,
                "topics": [],
                "text_content": ""
            }
    except Exception as e:
        print(f"Error in document processing: {str(e)}")
        # Return something to prevent upload failure
        return {
            "summary": "Error processing document.",
            "keywords": [file_extension, "document"],
            "topics": [],
            "text_content": ""
        }