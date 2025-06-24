import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import shutil

# Configuration
BASE_URL = "http://127.0.0.1:5000"  # Adjust to your Flask app URL
EMAIL = "demo@example.com"           # Your demo user
PASSWORD = "password123"             # Demo password
DOCUMENT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_document.pdf")
TAMPERED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tampered_document.pdf")

# Create demo directory if it doesn't exist
os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)

# Ensure we have a demo document to upload
if not os.path.exists(DOCUMENT_PATH):
    # Create a simple example if the file doesn't exist
    # This is a placeholder; replace with your own document
    with open(DOCUMENT_PATH, "wb") as f:
        f.write(b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n5 0 obj\n<< /Length 44 >>\nstream\nBT /F1 24 Tf 100 700 Td (Demo Document for Blockchain) Tj ET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000059 00000 n\n0000000118 00000 n\n0000000251 00000 n\n0000000319 00000 n\ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n406\n%%EOF")

# Create a "tampered" version of the document
if not os.path.exists(TAMPERED_PATH):
    shutil.copy(DOCUMENT_PATH, TAMPERED_PATH)
    with open(TAMPERED_PATH, "a") as f:
        f.write("\n<!-- This document has been altered -->\n")

def take_screenshot(driver, name):
    """Take a screenshot and save it with a timestamp"""
    screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{screenshots_dir}/{timestamp}_{name}.png"
    driver.save_screenshot(filename)
    print(f"Screenshot saved: {filename}")
    return filename

def wait_and_click(driver, selector, timeout=10):
    """Wait for an element to be clickable then click it"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(selector)
        )
        element.click()
        return element
    except ElementClickInterceptedException:
        # Try JavaScript click if normal click is intercepted
        element = driver.find_element(*selector)
        driver.execute_script("arguments[0].click();", element)
        return element
    except TimeoutException:
        print(f"Timeout waiting for element: {selector}")
        take_screenshot(driver, f"error_waiting_for_{selector[1].replace('/', '_')}")
        return None

def debug_page(driver):
    """Print page details for debugging"""
    print(f"Current URL: {driver.current_url}")
    print(f"Page title: {driver.title}")
    
    # Try to find form elements
    form_elements = driver.find_elements(By.TAG_NAME, "form")
    print(f"Found {len(form_elements)} form elements")
    
    # Try to find input elements
    input_elements = driver.find_elements(By.TAG_NAME, "input")
    print(f"Found {len(input_elements)} input elements")
    for i, input_el in enumerate(input_elements):
        input_type = input_el.get_attribute("type")
        input_name = input_el.get_attribute("name") or "no-name"
        input_id = input_el.get_attribute("id") or "no-id"
        print(f"  Input {i+1}: type={input_type}, name={input_name}, id={input_id}")

def main():
    # Set up Chrome options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-maximized")  # Start maximized for better recording
    # chrome_options.add_argument("--headless")  # Uncomment for headless mode
    
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(5)  # General implicit wait
    
    document_id = None  # We'll capture this after upload
    
    try:
        print("Starting automated demo...")
        
        # STEP 1: Login to the system
        print("Logging in...")
        driver.get(f"{BASE_URL}/auth/login")  # Make sure to use the correct login path
        
        # Debug page structure
        debug_page(driver)
        take_screenshot(driver, "login_page")
        
        # Try multiple selectors for email input
        email_selectors = [
            (By.NAME, "email"),
            (By.ID, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='email']")
        ]
        
        # Try to find and fill email field with various selectors
        email_input = None
        for selector in email_selectors:
            try:
                email_input = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located(selector)
                )
                if email_input:
                    print(f"Found email input with selector: {selector}")
                    break
            except:
                print(f"Email input not found with selector: {selector}")
                
        if email_input:
            email_input.send_keys(EMAIL)
        else:
            raise Exception("Could not find email input field")
        
        # Try multiple selectors for password input
        password_selectors = [
            (By.NAME, "password"),
            (By.ID, "password"),
            (By.CSS_SELECTOR, "input[type='password']")
        ]
        
        # Try to find and fill password field
        password_input = None
        for selector in password_selectors:
            try:
                password_input = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located(selector)
                )
                if password_input:
                    print(f"Found password input with selector: {selector}")
                    break
            except:
                print(f"Password input not found with selector: {selector}")
                
        if password_input:
            password_input.send_keys(PASSWORD)
        else:
            raise Exception("Could not find password input field")
        
        # Try to find login button with multiple approaches
        login_button_selectors = [
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.XPATH, "//button[contains(@type, 'submit')]"),
            (By.XPATH, "//input[contains(@type, 'submit')]"),
            (By.CSS_SELECTOR, "button.btn-primary"),
            (By.CSS_SELECTOR, "form button")
        ]
        
        login_clicked = False
        for selector in login_button_selectors:
            try:
                button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable(selector)
                )
                button.click()
                login_clicked = True
                print(f"Clicked login button with selector: {selector}")
                break
            except:
                print(f"Login button not found or not clickable with selector: {selector}")
        
        if not login_clicked:
            # Try submitting the form directly
            try:
                form = driver.find_element(By.TAG_NAME, "form")
                driver.execute_script("arguments[0].submit();", form)
                login_clicked = True
                print("Submitted form using JavaScript")
            except:
                print("Could not submit form")
        
        if not login_clicked:
            raise Exception("Could not find or click login button")
        
        # Wait for login to complete
        time.sleep(3)
        take_screenshot(driver, "after_login")
        
        # STEP 2: Check if we're now on the dashboard
        print("Checking if login was successful...")
        if "/dashboard" in driver.current_url or "upload" in driver.current_url:
            print("Login successful!")
        else:
            print("Login may have failed. Current URL:", driver.current_url)
            debug_page(driver)
            # Continue anyway as we might be redirected elsewhere
        
        # STEP 3: Go to document upload page
        print("Navigating to upload page...")
        driver.get(f"{BASE_URL}/user/upload")
        take_screenshot(driver, "upload_page")
        time.sleep(1)
        
        # Check if the upload form is present
        try:
            upload_form = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            print("Upload form found")
        except:
            print("Upload form not found, taking screenshot of current page")
            debug_page(driver)
            take_screenshot(driver, "upload_page_error")
            raise Exception("Upload form not found")
        
        # Fill upload form
        print("Uploading document...")
        
        # Try to find document name field
        try:
            name_field = driver.find_element(By.NAME, "document_name")
            name_field.send_keys(f"Demo Document {random.randint(1000, 9999)}")
        except:
            print("Document name field not found")
            
        # Try to find description field
        try:
            desc_field = driver.find_element(By.NAME, "document_description")
            desc_field.send_keys("This document is for blockchain verification demo")
        except:
            print("Document description field not found")
            
        # Try to find tags field
        try:
            tags_field = driver.find_element(By.NAME, "tags")
            tags_field.send_keys("demo, blockchain, verification")
        except:
            print("Tags field not found")
        
        # Upload the file - try different selectors for file input
        file_input_selectors = [
            (By.NAME, "file"),
            (By.CSS_SELECTOR, "input[type='file']"),
            (By.XPATH, "//input[@type='file']")
        ]
        
        file_input = None
        for selector in file_input_selectors:
            try:
                file_input = driver.find_element(*selector)
                print(f"Found file input with selector: {selector}")
                break
            except:
                print(f"File input not found with selector: {selector}")
                
        if file_input:
            file_input.send_keys(DOCUMENT_PATH)
        else:
            raise Exception("Could not find file input field")
        
        # Submit the form - try different approaches
        submit_selectors = [
            (By.XPATH, "//button[contains(text(), 'Upload')]"),
            (By.XPATH, "//button[contains(text(), 'Submit')]"),
            (By.XPATH, "//button[@type='submit']"),
            (By.CSS_SELECTOR, "form button")
        ]
        
        form_submitted = False
        for selector in submit_selectors:
            try:
                button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable(selector)
                )
                button.click()
                form_submitted = True
                print(f"Clicked submit button with selector: {selector}")
                break
            except:
                print(f"Submit button not found or not clickable with selector: {selector}")
        
        if not form_submitted:
            # Try submitting the form directly
            try:
                form = driver.find_element(By.TAG_NAME, "form")
                driver.execute_script("arguments[0].submit();", form)
                form_submitted = True
                print("Submitted form using JavaScript")
            except:
                print("Could not submit form")
        
        if not form_submitted:
            raise Exception("Could not submit upload form")
        
        print("Document uploaded, waiting for processing...")
        time.sleep(5)  # Wait for upload to complete
        take_screenshot(driver, "after_upload")
        
        # Check if we were redirected to the dashboard after upload
        print("Current URL after upload:", driver.current_url)
        
        # STEP 4: Go to dashboard to see the uploaded document
        print("Navigating to dashboard...")
        driver.get(f"{BASE_URL}/dashboard")
        time.sleep(2)
        take_screenshot(driver, "dashboard_with_document")
        
        # STEP 5: Find the most recently uploaded document
        print("Finding the uploaded document...")
        document_cards = driver.find_elements(By.CSS_SELECTOR, ".document-card")
        if document_cards:
            print(f"Found {len(document_cards)} document cards")
            # Click on "View Details" for the first document
            view_buttons = document_cards[0].find_elements(By.CSS_SELECTOR, "a.btn-secondary")
            if view_buttons:
                print(f"Found {len(view_buttons)} action buttons on document card")
                for btn in view_buttons:
                    if "View" in btn.text or "Details" in btn.text:
                        btn.click()
                        print("Clicked 'View Details' button")
                        break
                else:
                    print("'View Details' button text not found, trying first button")
                    view_buttons[0].click()
            else:
                print("No action buttons found on document card")
                # Try a different approach
                try:
                    first_link = document_cards[0].find_element(By.TAG_NAME, "a")
                    first_link.click()
                    print("Clicked first link on document card")
                except:
                    print("No links found on document card")
        else:
            print("No documents found on dashboard, looking for document ID elsewhere")
            # We might need to get the document ID from another page or source
        
        time.sleep(2)
        take_screenshot(driver, "document_details")
        
        # STEP 6: Extract the document ID for later verification
        print("Extracting document ID...")
        
        # Try different approaches to find document ID
        doc_id_found = False
        
        # Try approach 1: Look for a specific element with the ID
        try:
            document_id_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".filter-tag strong, .document-id"))
            )
            document_id = document_id_element.text.strip()
            doc_id_found = True
            print(f"Found document ID in dedicated element: {document_id}")
        except:
            print("Document ID element not found by class")
        
        # Try approach 2: Extract from URL
        if not doc_id_found:
            try:
                current_url = driver.current_url
                if "/document/" in current_url:
                    # Extract ID from URL like /document/1234-5678/
                    parts = current_url.split("/document/")
                    if len(parts) > 1:
                        document_id = parts[1].split("/")[0].strip()
                        doc_id_found = True
                        print(f"Extracted document ID from URL: {document_id}")
            except:
                print("Could not extract document ID from URL")
        
        # Try approach 3: Find in page content
        if not doc_id_found:
            # Look for text that might contain a UUID
            page_text = driver.page_source
            import re
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            uuid_matches = re.findall(uuid_pattern, page_text)
            if uuid_matches:
                document_id = uuid_matches[0]
                doc_id_found = True
                print(f"Found document ID in page content: {document_id}")
        
        if not doc_id_found or not document_id:
            print("Could not extract document ID, using a placeholder")
            document_id = "missing-document-id"
        
        print(f"Document ID for verification: {document_id}")
        
        # STEP 7: Go to verification page with the document ID
        print("Navigating to verification page...")
        driver.get(f"{BASE_URL}/security/verification?document_id={document_id}")
        time.sleep(2)
        take_screenshot(driver, "verification_page")
        
        # Ensure the document ID is in the input field
        try:
            document_id_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "document-id"))
            )
            current_value = document_id_input.get_attribute("value")
            if not current_value:
                document_id_input.send_keys(document_id)
                print(f"Entered document ID: {document_id}")
            else:
                print(f"Document ID already populated: {current_value}")
        except:
            print("Document ID input field not found")
            take_screenshot(driver, "verification_page_error")
        
        # Select blockchain verification method
        try:
            blockchain_method = driver.find_element(By.CSS_SELECTOR, ".verification-method.blockchain")
            if "active" not in blockchain_method.get_attribute("class"):
                blockchain_method.click()
                print("Selected blockchain verification method")
        except:
            print("Blockchain verification method selector not found")
            
        take_screenshot(driver, "verification_page_with_id")
        
        # STEP 8: Perform verification
        print("Performing blockchain verification...")
        try:
            verify_button = driver.find_element(By.ID, "verify-btn")
            verify_button.click()
            print("Clicked verify button")
        except:
            print("Verify button not found, trying other selectors")
            # Try other selectors
            verify_selectors = [
                (By.XPATH, "//button[contains(text(), 'Verify')]"),
                (By.CSS_SELECTOR, ".btn-primary")
            ]
            for selector in verify_selectors:
                try:
                    button = driver.find_element(*selector)
                    button.click()
                    print(f"Clicked verify button with selector: {selector}")
                    break
                except:
                    continue
        
        # Wait for verification to complete
        time.sleep(5)
        
        # Take screenshot of verification results
        take_screenshot(driver, "verification_results")
        
        # STEP 9: Check the logs for blockchain verification details
        print("Checking verification logs...")
        try:
            log_entries = driver.find_elements(By.CSS_SELECTOR, ".log-entry")
            print(f"Found {len(log_entries)} log entries")
            for entry in log_entries:
                print(f"Log: {entry.text}")
        except:
            print("No log entries found")
        
        # STEP 10: Take screenshots of verification results
        result_elements = driver.find_elements(By.CSS_SELECTOR, ".verification-results")
        if result_elements:
            print("Verification results found:")
            for i, elem in enumerate(result_elements):
                try:
                    result_title = elem.find_element(By.CSS_SELECTOR, ".result-title").text
                    result_message = elem.find_element(By.CSS_SELECTOR, ".result-message").text
                    print(f"Result: {result_title} - {result_message}")
                except:
                    print(f"Result element {i+1} found but couldn't extract details")
        else:
            print("No verification result elements found")
        
        # Successfully completed demo
        print("Demo completed successfully!")
        
    except Exception as e:
        print(f"Error during demo execution: {e}")
        import traceback
        traceback.print_exc()
        take_screenshot(driver, "error_screenshot")
        raise
    
    finally:
        # Keep browser open for 5 seconds to show final state
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    main()
