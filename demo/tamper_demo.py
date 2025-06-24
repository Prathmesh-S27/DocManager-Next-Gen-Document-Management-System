import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import shutil

# Configuration
BASE_URL = "http://127.0.0.1:5000"  # Adjust to your Flask app URL
EMAIL = "demo@example.com"           # Your demo user
PASSWORD = "password123"             # Demo password

def take_screenshot(driver, name):
    """Take a screenshot and save it with a timestamp"""
    screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{screenshots_dir}/{timestamp}_{name}.png"
    driver.save_screenshot(filename)
    print(f"Screenshot saved: {filename}")
    return filename

def main(document_id):
    """Run a tamper detection demonstration for the specified document ID"""
    if not document_id:
        raise ValueError("Document ID must be provided")
        
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(5)
    
    try:
        print("Starting tamper detection demo...")
        
        # Step 1: Login to the system
        print("Logging in...")
        driver.get(f"{BASE_URL}/login")
        driver.find_element(By.NAME, "email").send_keys(EMAIL)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
        login_button.click()
        time.sleep(2)
        
        # Step 2: Go directly to the verification page
        print("Going to verification page...")
        driver.get(f"{BASE_URL}/security/verification?document_id={document_id}")
        time.sleep(2)
        take_screenshot(driver, "verification_page_tamper_demo")
        
        # Step 3: Ensure blockchain verification is selected
        print("Selecting blockchain verification...")
        blockchain_method = driver.find_element(By.CSS_SELECTOR, ".verification-method.blockchain")
        if "active" not in blockchain_method.get_attribute("class"):
            blockchain_method.click()
            time.sleep(1)
        
        # Step 4: Start verification
        print("Verifying document...")
        verify_button = driver.find_element(By.ID, "verify-btn")
        verify_button.click()
        time.sleep(5)  # Wait for verification to complete
        
        # Step 5: Capture verification result
        print("Capturing verification result...")
        take_screenshot(driver, "verification_result_before_tampering")
        
        # Read the verification result
        verification_result = driver.find_element(By.CSS_SELECTOR, ".verification-results h3 .result-title").text
        print(f"Before tampering - Verification result: {verification_result}")
        
        # Step 6: Now simulate tampering by using a tampered document
        # In a real scenario, this would involve uploading a modified document version
        # For demo purposes, we'll explain the process:
        print("\n----------------------------------------")
        print("TAMPERING DEMONSTRATION")
        print("In a real scenario, the document would now be modified outside the system.")
        print("This could be simulated by:")
        print("1. Using the /upload/version/{document_id} endpoint to upload a tampered version")
        print("2. Directly modifying the document in the database/storage")
        print("For this demo, we assume tampering has occurred and we're now re-verifying.")
        print("----------------------------------------\n")
        
        # Step 7: After "tampering", re-verify the document
        # In a full demo, we would upload a tampered version first
        time.sleep(3)  # Pause for effect
        
        # Step 8: Refresh the page to simulate coming back to verify after tampering
        driver.refresh()
        time.sleep(2)
        
        # Ensure document ID is still in field
        document_id_input = driver.find_element(By.ID, "document-id")
        if not document_id_input.get_attribute("value"):
            document_id_input.send_keys(document_id)
        
        # Ensure blockchain verification is selected
        blockchain_method = driver.find_element(By.CSS_SELECTOR, ".verification-method.blockchain")
        if "active" not in blockchain_method.get_attribute("class"):
            blockchain_method.click()
            time.sleep(1)
            
        # Click verify again
        verify_button = driver.find_element(By.ID, "verify-btn")
        verify_button.click()
        time.sleep(5)  # Wait for verification to complete
        
        # Capture the result after "tampering"
        take_screenshot(driver, "verification_result_after_tampering")
        
        # Successfully completed demo
        print("Tamper detection demo completed!")
        
    except Exception as e:
        print(f"Error during tamper demo execution: {e}")
        take_screenshot(driver, "tamper_demo_error")
        raise
    
    finally:
        # Keep browser open for 5 seconds to show final state
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    # You need to provide a valid document ID from a previous upload
    # document_id = "YOUR_DOCUMENT_ID_HERE"
    document_id = input("Enter the document ID to use for tamper detection demo: ")
    main(document_id)
