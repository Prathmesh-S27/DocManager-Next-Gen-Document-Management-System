import os
import time
import random
import string
import shutil
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import requests

# Configuration
BASE_URL = "http://127.0.0.1:5000"  # Flask app URL
DEMO_FOLDER = os.path.dirname(os.path.abspath(__file__))
SCREENSHOTS_DIR = os.path.join(DEMO_FOLDER, "screenshots")
GANACHE_URL = "http://localhost:7545"  # Default Ganache URL

# Correctly mapped routes based on backend route definitions
AUTH_ROUTES = {
    'login': f"{BASE_URL}/auth/login",
    'signup': f"{BASE_URL}/auth/signup",
    'logout': f"{BASE_URL}/auth/logout"
}

USER_ROUTES = {
    'dashboard': f"{BASE_URL}/user/dashboard",
    'profile': f"{BASE_URL}/user/profile",
    'upload_page': f"{BASE_URL}/user/upload-document"  # GET - form page
}

VIEW_ROUTES = {
    'all_documents': f"{BASE_URL}/view/documents",  # Primary route
    'documents_alt': f"{BASE_URL}/documents",       # Alternative route
    'document_details': f"{BASE_URL}/view/document"  # /<document_id> will be appended
}

UPLOAD_ROUTES = {
    'upload_submit': f"{BASE_URL}/upload",                    # POST endpoint
    'multiple_upload': f"{BASE_URL}/upload/multiple",         # POST endpoint
    'delete_document': f"{BASE_URL}/upload/document/delete",  # /<document_id> will be appended
    'upload_version': f"{BASE_URL}/upload/version"            # /<document_id> will be appended
}

SECURITY_ROUTES = {
    'verification_page': f"{BASE_URL}/security/verification",
    'verify_document': f"{BASE_URL}/security/verify-document",         # /<document_id> will be appended
    'verify_blockchain': f"{BASE_URL}/security/verify-document-blockchain" # /<document_id> will be appended
}

# Create unique email for this demo run to avoid duplicates
DEMO_EMAIL = f"demo_user_{int(time.time())}@example.com"
DEMO_PASSWORD = "Demo@123"  # Demo password
DEMO_FULLNAME = "Demo User"
DEMO_PHONE = "123-456-7890"  # Added phone number since it appears in the form

# List of real documents to upload (using user-provided paths)
DEMO_DOCUMENTS = [
    {
        "name": "Ishan Shivankar Resume",
        "description": "Professional resume document",
        "tags": "",  # No tags as per user request
        "path": r"I:\Resume\Ishan_Shivankar.pdf"
    },
    {
        "name": "Seizure Detection Research",
        "description": "Research paper on seizure detection technology",
        "tags": "",  # No tags as per user request
        "path": r"C:\Users\ASUS\Downloads\Seizure Detection.pdf" 
    },
    {
        "name": "Blockchain Journal Paper",
        "description": "Research paper on blockchain technology",
        "tags": "",  # No tags as per user request
        "path": r"I:\Resume\Blockchain Paper for Journal.pdf"
    }
]

# Ensure demo files exist
def create_demo_files():
    """Check if specified documents exist, show error if not"""
    missing_files = []
    for document in DEMO_DOCUMENTS:
        if not os.path.exists(document["path"]):
            missing_files.append(document["path"])
    
    if missing_files:
        print("⚠️ WARNING: The following files could not be found:")
        for path in missing_files:
            print(f"  • {path}")
        print("\nPlease verify that these files exist at the specified locations.")
        proceed = input("Would you like to continue anyway? (y/n): ")
        if proceed.lower() != 'y':
            import sys
            sys.exit(1)

def take_screenshot(driver, name):
    """Take a screenshot and save it with a timestamp"""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{SCREENSHOTS_DIR}/{timestamp}_{name}.png"
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

def is_server_running():
    """Check if the Flask server is running"""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def is_ganache_running():
    """Check if Ganache is running"""
    try:
        # First try the standard HTTP endpoint
        response = requests.get(GANACHE_URL, timeout=3)
        if response.status_code == 200:
            print("✅ Ganache HTTP server detected at port 7545")
            return True
    except requests.exceptions.RequestException:
        # If HTTP check fails, try a different approach for Ganache GUI
        try:
            # Try Web3 connection which works better with Ganache GUI
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
            if w3.is_connected():
                print("✅ Connected to Ganache via Web3")
                return True
            else:
                print("⚠️ Web3 connection to Ganache failed")
        except Exception as e:
            print(f"⚠️ Alternative Ganache check failed: {str(e)}")
    
    # At this point, both checks have failed
    print("ℹ️ Could not automatically detect Ganache")
    user_confirm = input("Are you sure Ganache is running? (y/n): ")
    return user_confirm.lower() == 'y'

def debug_form_fields(driver):
    """Debug function to print all form fields on the current page"""
    print("\n🔍 Debugging form fields on current page:")
    forms = driver.find_elements(By.TAG_NAME, "form")
    print(f"Found {len(forms)} forms")
    
    for i, form in enumerate(forms):
        print(f"Form #{i+1}:")
        inputs = form.find_elements(By.TAG_NAME, "input")
        print(f"  Found {len(inputs)} input fields:")
        
        for j, input_field in enumerate(inputs):
            field_type = input_field.get_attribute("type")
            field_name = input_field.get_attribute("name") or "no-name"
            field_id = input_field.get_attribute("id") or "no-id"
            field_placeholder = input_field.get_attribute("placeholder") or "no-placeholder"
            print(f"    Input #{j+1}: type={field_type}, name={field_name}, id={field_id}, placeholder={field_placeholder}")
            
        buttons = form.find_elements(By.TAG_NAME, "button")
        print(f"  Found {len(buttons)} buttons:")
        for j, button in enumerate(buttons):
            button_type = button.get_attribute("type")
            button_text = button.text
            print(f"    Button #{j+1}: type={button_type}, text={button_text}")
    
    print("--- End of Form Debug ---\n")

def type_naturally(input_field, text, speed='medium'):
    """
    Simulates more natural typing with variable speed for better video presentation
    
    Parameters:
    - input_field: The element to type into
    - text: The text to type
    - speed: 'slow', 'medium', 'fast'
    """
    # Clear the field first
    input_field.clear()
    
    # Determine the base delay between keypresses
    base_delays = {
        'slow': 0.15,      # Slower for emphasis
        'medium': 0.08,    # Good for most inputs
        'fast': 0.05       # Faster but still visible
    }
    base_delay = base_delays.get(speed, 0.08)
    
    # Type with slight randomization for naturalistic effect
    for char in text:
        # Variable delay between characters (realistic typing effect)
        variation = base_delay * (0.8 + 0.4 * random.random())
        
        # Longer pause for punctuation
        if char in ['.', ',', '!', '?', ';', ':', '-']:
            variation *= 1.5
        
        # Send single character
        input_field.send_keys(char)
        time.sleep(variation)
    
    # Pause slightly at the end of typing
    time.sleep(0.3)

def scroll_smoothly(driver, direction='down', speed='medium', distance=None):
    """
    Smoothly scroll the page for better visual demonstration
    
    Parameters:
    - direction: 'up', 'down', 'top', or 'bottom'
    - speed: 'slow', 'medium', or 'fast'
    - distance: Number of pixels to scroll (if None, scroll ~80% of viewport)
    """
    # Get viewport height
    viewport_height = driver.execute_script("return window.innerHeight")
    total_height = driver.execute_script("return document.body.scrollHeight")
    current_position = driver.execute_script("return window.pageYOffset")
    
    # Determine scroll parameters
    if distance is None:
        distance = int(viewport_height * 0.7)  # Default to 70% of viewport (less jumpy)
    else:
        # Ensure distance is an integer
        distance = int(distance)
    
    # Time delays between scroll steps - make scrolling slower for better visual effect
    delays = {
        'slow': 0.15,    # Very slow for dramatic effect and reading
        'medium': 0.08,  # Good for most scrolling
        'fast': 0.04     # Faster but still smooth
    }
    delay = delays.get(speed, 0.08)
    
    # Step size for each scroll increment - smaller steps for smoother scrolling
    step_sizes = {
        'slow': 15,      # Smaller steps for more granular movement
        'medium': 25,    # Balanced steps
        'fast': 40       # Larger steps but still smooth
    }
    step = step_sizes.get(speed, 25)
    
    # For scrolling to top, use a more reliable visual approach
    if direction == 'top':
        print(f"Scrolling to TOP from position {current_position}")
        # Create a visual indicator for scrolling up
        try:
            driver.execute_script("""
                var indicator = document.createElement('div');
                indicator.innerHTML = '⬆️ Scrolling to top...';
                indicator.style.position = 'fixed';
                indicator.style.right = '20px';
                indicator.style.top = '20px';
                indicator.style.backgroundColor = 'rgba(0,0,0,0.7)';
                indicator.style.color = 'white';
                indicator.style.padding = '8px 15px';
                indicator.style.borderRadius = '4px';
                indicator.style.zIndex = '9999';
                indicator.id = 'scroll-indicator';
                document.body.appendChild(indicator);
            """)
        except:
            pass
            
        # Scroll in smaller increments for smoother visual effect
        steps = 15
        for i in range(steps, 0, -1):
            pos = int(current_position * i / steps)
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(delay * 2)  # Slightly longer delay for top scrolling
        
        # Final scroll to top
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
        
        # Remove the indicator
        try:
            driver.execute_script("""
                var indicator = document.getElementById('scroll-indicator');
                if (indicator) document.body.removeChild(indicator);
            """)
        except:
            pass
        return
    
    # For scrolling to bottom, use a similar reliable approach
    if direction == 'bottom':
        print(f"Scrolling to BOTTOM")
        # Create a visual indicator for scrolling down
        try:
            driver.execute_script("""
                var indicator = document.createElement('div');
                indicator.innerHTML = '⬇️ Scrolling down...';
                indicator.style.position = 'fixed';
                indicator.style.right = '20px';
                indicator.style.top = '20px';
                indicator.style.backgroundColor = 'rgba(0,0,0,0.7)';
                indicator.style.color = 'white';
                indicator.style.padding = '8px 15px';
                indicator.style.borderRadius = '4px';
                indicator.style.zIndex = '9999';
                indicator.id = 'scroll-indicator';
                document.body.appendChild(indicator);
            """)
        except:
            pass
        
        bottom_position = total_height - viewport_height
        steps = 15  # More steps for smoother scrolling
        for i in range(1, steps + 1):
            pos = int(current_position + (bottom_position - current_position) * i / steps)
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(delay * 2)  # Longer delay for more dramatic effect
        
        # Final scroll to bottom
        driver.execute_script(f"window.scrollTo(0, {bottom_position});")
        time.sleep(0.5)
        
        # Remove the indicator
        try:
            driver.execute_script("""
                var indicator = document.getElementById('scroll-indicator');
                if (indicator) document.body.removeChild(indicator);
            """)
        except:
            pass
        return
    
    # For up/down scrolling by a specific distance
    if direction == 'down':
        # Create a visual indicator for scrolling down
        try:
            driver.execute_script("""
                var indicator = document.createElement('div');
                indicator.innerHTML = '⬇️ Scrolling...';
                indicator.style.position = 'fixed';
                indicator.style.right = '20px';
                indicator.style.top = '20px';
                indicator.style.backgroundColor = 'rgba(0,0,0,0.7)';
                indicator.style.color = 'white';
                indicator.style.padding = '8px 15px';
                indicator.style.borderRadius = '4px';
                indicator.style.zIndex = '9999';
                indicator.id = 'scroll-indicator';
                document.body.appendChild(indicator);
            """)
        except:
            pass
            
        target = min(current_position + distance, total_height - viewport_height)
        # Create a list of scroll positions with integer values
        scroll_positions = []
        steps_count = max(10, min(30, int(abs(target - current_position) / step)))
        for i in range(1, steps_count + 1):
            pos = int(current_position + (target - current_position) * (i / steps_count))
            scroll_positions.append(pos)
    elif direction == 'up':
        # Create a visual indicator for scrolling up
        try:
            driver.execute_script("""
                var indicator = document.createElement('div');
                indicator.innerHTML = '⬆️ Scrolling...';
                indicator.style.position = 'fixed';
                indicator.style.right = '20px';
                indicator.style.top = '20px';
                indicator.style.backgroundColor = 'rgba(0,0,0,0.7)';
                indicator.style.color = 'white';
                indicator.style.padding = '8px 15px';
                indicator.style.borderRadius = '4px';
                indicator.style.zIndex = '9999';
                indicator.id = 'scroll-indicator';
                document.body.appendChild(indicator);
            """)
        except:
            pass
            
        target = max(current_position - distance, 0)
        # Create a list of scroll positions with integer values
        scroll_positions = []
        steps_count = max(10, min(30, int(abs(current_position - target) / step)))
        for i in range(1, steps_count + 1):
            pos = int(current_position - (current_position - target) * (i / steps_count))
            scroll_positions.append(pos)
    
    # Perform the smooth scroll using the calculated positions
    for pos in scroll_positions:
        driver.execute_script(f"window.scrollTo(0, {pos});")
        time.sleep(delay)
    
    # Final scroll to exact target position
    driver.execute_script(f"window.scrollTo(0, {target});")
    time.sleep(0.5)  # Longer pause at destination for better visibility
    
    # Remove the indicator
    try:
        driver.execute_script("""
            var indicator = document.getElementById('scroll-indicator');
            if (indicator) document.body.removeChild(indicator);
        """)
    except:
        pass

def highlight_element(driver, element, style="info", duration=0.7):
    """
    Highlight an element on the page with animation effect for better visibility in videos
    
    Parameters:
    - driver: Selenium WebDriver instance
    - element: The element to highlight
    - style: "info", "success", "warning", or "error"
    - duration: How long to show the highlight in seconds
    """
    styles = {
        "info": {"color": "#2196F3", "text": "Info"},
        "success": {"color": "#4CAF50", "text": "Success"},
        "warning": {"color": "#FF9800", "text": "Warning"},
        "error": {"color": "#f44336", "text": "Error"}
    }
    
    style_info = styles.get(style, styles["info"])
    color = style_info["color"]
    
    # Get the original element style
    original_style = driver.execute_script("return arguments[0].getAttribute('style');", element) or ""
    
    # Scroll element into view first
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
    time.sleep(0.5)
    
    # Apply pulsating highlight effect
    driver.execute_script(f"""
        var originalStyle = arguments[0].getAttribute('style') || '';
        
        // Add pulsating animation
        var styleTag = document.createElement('style');
        styleTag.id = 'highlight-animation';
        styleTag.innerHTML = `
            @keyframes highlight-pulse {{
                0% {{ box-shadow: 0 0 0 0 {color}80; }}
                70% {{ box-shadow: 0 0 0 10px {color}00; }}
                100% {{ box-shadow: 0 0 0 0 {color}00; }}
            }}
        `;
        document.head.appendChild(styleTag);
        
        arguments[0].style.boxShadow = '0 0 5px {color}';
        arguments[0].style.border = '2px solid {color}';
        arguments[0].style.transition = 'all 0.3s';
        arguments[0].style.animation = 'highlight-pulse 1.5s infinite';
        arguments[0].style.position = 'relative';
        arguments[0].style.zIndex = '10';
    """, element)
    
    # Pause to show the highlight
    time.sleep(duration)
    
    # Remove the animation and restore original style
    driver.execute_script("""
        var styleTag = document.getElementById('highlight-animation');
        if (styleTag) document.head.removeChild(styleTag);
        
        arguments[0].setAttribute('style', arguments[1]);
    """, element, original_style)

def main():
    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    
    # Check if specified documents exist
    print("\n📄 Checking if specified documents exist...")
    create_demo_files()
    
    if not is_server_running():
        print("❌ Flask application is not running! Please start the server first.")
        server_confirm = input("Would you like to continue anyway? (y/n): ")
        if server_confirm.lower() != 'y':
            return False
    else:
        print("✅ Flask application is running and accessible")
    
    ganache_running = is_ganache_running()
    if not ganache_running:
        print("❌ Ganache not detected! Blockchain features may not work.")
        ganache_confirm = input("Would you like to continue without Ganache? (y/n): ")
        if ganache_confirm.lower() != 'y':
            return False
    
    print("✅ Prerequisites check completed")
    
    # Set up Chrome options for proper full screen mode
    print("\n🖥️ Launching Chrome in full screen mode...")
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-fullscreen")  # Most reliable fullscreen option
    chrome_options.add_argument("--kiosk")  # Additional fullscreen support for some platforms
    
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    
    # Ensure browser is in full screen mode with multiple approaches for reliability
    try:
        time.sleep(1)  # Wait for browser to initialize
        driver.maximize_window()  # First maximize
        driver.fullscreen_window()  # Then enter true fullscreen mode
        
        # Also try JavaScript fullscreen API as a backup method
        driver.execute_script("""
            if (document.documentElement.requestFullscreen) {
                document.documentElement.requestFullscreen();
            } else if (document.documentElement.mozRequestFullscreen) {
                document.documentElement.mozRequestFullscreen();
            } else if (document.documentElement.webkitRequestFullscreen) {
                document.documentElement.webkitRequestFullscreen();
            } else if (document.documentElement.msRequestFullscreen) {
                document.documentElement.msRequestFullscreen();
            }
        """)
    except Exception as e:
        print(f"Note: Could not force fullscreen: {e}")
    
    # Set implicit wait time after browser is configured
    driver.implicitly_wait(5)
    
    document_ids = []  # Store uploaded document IDs
    goto_step_3 = False
    
    try:
        print("\n🚀 Starting automated demo workflow...")
        
        # STEP 1: Sign up for a new account
        print("\n📝 STEP 1: Creating new account...")
        driver.get(AUTH_ROUTES['signup'])
        take_screenshot(driver, "signup_page")
        
        # Debug form fields to understand the actual structure
        debug_form_fields(driver)
        
        # Try to find the necessary input fields
        try:
            # Find name input - try multiple selectors
            name_selectors = [
                (By.NAME, "name"),
                (By.ID, "name"),
                (By.NAME, "fullname"),
                (By.ID, "fullname"),
                (By.CSS_SELECTOR, "input[placeholder*='name' i]")
            ]
            
            name_input = None
            for selector in name_selectors:
                try:
                    name_input = driver.find_element(*selector)
                    print(f"Found name input using selector: {selector}")
                    break
                except:
                    pass
                    
            if name_input:
                highlight_element(driver, name_input, "info", 0.7)
                type_naturally(name_input, DEMO_FULLNAME, 'fast')
                print(f"Entered name: {DEMO_FULLNAME}")
            else:
                print("⚠️ Could not find name input field")
            
            # Find email input - try multiple selectors
            email_selectors = [
                (By.NAME, "email"),
                (By.ID, "email"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='email' i]")
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = driver.find_element(*selector)
                    print(f"Found email input using selector: {selector}")
                    break
                except:
                    pass
                    
            if email_input:
                highlight_element(driver, email_input, "info", 0.7)
                type_naturally(email_input, DEMO_EMAIL, 'fast')
                print(f"Entered email: {DEMO_EMAIL}")
            else:
                print("⚠️ Could not find email input field")
            
            # Find password input - try multiple selectors
            password_selectors = [
                (By.NAME, "password"),
                (By.ID, "password"),
                (By.CSS_SELECTOR, "input[type='password']")
            ]
            
            password_inputs = []
            for selector in password_selectors:
                try:
                    inputs = driver.find_elements(*selector)
                    if inputs:
                        password_inputs.extend(inputs)
                        print(f"Found {len(inputs)} password input(s) using selector: {selector}")
                except:
                    pass
            
            # Handle password fields (typically 1 or 2 password fields)
            if len(password_inputs) >= 1:
                highlight_element(driver, password_inputs[0], "info", 0.7)
                type_naturally(password_inputs[0], DEMO_PASSWORD, 'fast')
                print(f"Entered password in first password field")
                
                # If there's a second password field (confirm password)
                if len(password_inputs) >= 2:
                    highlight_element(driver, password_inputs[1], "info", 0.7)
                    type_naturally(password_inputs[1], DEMO_PASSWORD, 'fast')
                    print(f"Entered password in second password field (confirm password)")
            else:
                print("⚠️ Could not find password input field(s)")
                
            # Try to find the signup button and click it
            signup_button_selectors = [
                (By.XPATH, "//button[contains(text(), 'Sign Up') or contains(text(), 'Signup') or contains(text(), 'Register')]"),
                (By.XPATH, "//input[@type='submit']"),
                (By.CSS_SELECTOR, "form button[type='submit']"),
                (By.CSS_SELECTOR, "button.btn-primary")
            ]
            
            signup_clicked = False
            for selector in signup_button_selectors:
                try:
                    button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable(selector)
                    )
                    highlight_element(driver, button, "success", 0.7)
                    button.click()
                    signup_clicked = True
                    print(f"Clicked signup button with selector: {selector}")
                    break
                except:
                    print(f"Could not find signup button with selector: {selector}")
            
            if not signup_clicked:
                # Try submitting the form directly
                try:
                    form = driver.find_element(By.TAG_NAME, "form")
                    driver.execute_script("arguments[0].submit();", form)
                    signup_clicked = True
                    print("Submitted signup form using JavaScript")
                except:
                    print("Could not submit signup form")
            
            time.sleep(3)
            take_screenshot(driver, "after_signup")
            print(f"✅ Account creation attempt completed with email: {DEMO_EMAIL}")
            
            # Check if we need to login (whether we're on login page or already logged in)
            current_url = driver.current_url
            if "login" in current_url or "signin" in current_url:
                print("Redirected to login page - signup successful, proceeding to login")
            elif "dashboard" in current_url:
                print("Redirected to dashboard - automatic login after signup")
                # Skip login step by jumping to step 3
                goto_step_3 = True
            else:
                print(f"Current URL after signup attempt: {current_url}")
                
        except Exception as e:
            print(f"⚠️ Error during signup process: {e}")
            take_screenshot(driver, "signup_error")
        
        # STEP 2: Login (unless already logged in after signup)
        if not goto_step_3:
            print("\n🔐 STEP 2: Logging in...")
            driver.get(AUTH_ROUTES['login'])
            take_screenshot(driver, "login_page")
            
            # Debug form fields for login page
            debug_form_fields(driver)
            
            # Try multiple selectors for email input
            email_selectors = [
                (By.NAME, "email"),
                (By.ID, "email"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='email' i]")
            ]
            
            # Try to find and fill email field
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = driver.find_element(*selector)
                    print(f"Found email input with selector: {selector}")
                    break
                except:
                    pass
                    
            if email_input:
                highlight_element(driver, email_input, "info", 0.7)
                type_naturally(email_input, DEMO_EMAIL, 'fast')
            else:
                print("⚠️ Could not find email input field on login page")
            
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
                    password_input = driver.find_element(*selector)
                    print(f"Found password input with selector: {selector}")
                    break
                except:
                    pass
                    
            if password_input:
                highlight_element(driver, password_input, "info", 0.7)
                type_naturally(password_input, DEMO_PASSWORD, 'fast')
            else:
                print("⚠️ Could not find password input field on login page")
            
            # Try to find login button and click it
            login_button_selectors = [
                (By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Sign In')]"),
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
                    highlight_element(driver, button, "success", 0.7)
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
                    print("Submitted login form using JavaScript")
                except:
                    print("Could not submit login form")
            
            time.sleep(3)
            take_screenshot(driver, "after_login")
            
            # Verify if we're on dashboard
            if "dashboard" in driver.current_url:
                print("✅ Login successful!")
            else:
                print("⚠️ Login may have failed. Current URL:", driver.current_url)
                # Take additional screenshot and continue anyway
                take_screenshot(driver, "login_result_page")

        # STEP 3: Upload multiple documents
        print("\n📄 STEP 3: Uploading documents...")
        
        for idx, document in enumerate(DEMO_DOCUMENTS):
            print(f"\nUploading document {idx+1}/{len(DEMO_DOCUMENTS)}: {document['name']}")
            print(f"📂 File: {document['path']}")
            
            # Try primary upload page URL first
            driver.get(USER_ROUTES['upload_page'])
            current_url = driver.current_url
            time.sleep(2)  # Give time to load
            
            # If first URL gives 404, try alternative route (direct without user prefix)
            if "404" in driver.title or "not found" in driver.title.lower():
                fallback_url = f"{BASE_URL}/upload-document"
                print(f"⚠️ Primary upload URL failed, trying fallback URL: {fallback_url}")
                driver.get(fallback_url)
                time.sleep(2)
            
            print(f"📄 Upload page URL: {driver.current_url}")
            take_screenshot(driver, f"upload_page_{idx+1}")
            
            # Debug the form structure to identify field names
            debug_form_fields(driver)
            
            try:
                # Check the form's action URL to see where it will submit to
                try:
                    form = driver.find_element(By.TAG_NAME, "form")
                    form_action = form.get_attribute("action") or UPLOAD_ROUTES['upload_submit']
                    print(f"Form will submit to: {form_action}")
                except:
                    print("Could not determine form action, will use default")
                    form_action = UPLOAD_ROUTES['upload_submit']
                
                # Try to find document name field with multiple selectors
                name_input = None
                name_selectors = [
                    (By.NAME, "document_name"),
                    (By.ID, "document_name"),
                    (By.CSS_SELECTOR, "input[placeholder*='name' i]"),
                    (By.CSS_SELECTOR, "input[type='text']"),
                ]
                
                for selector in name_selectors:
                    try:
                        name_input = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located(selector)
                        )
                        if name_input:
                            print(f"Found document name input with selector: {selector}")
                            highlight_element(driver, name_input, "info", 0.7)
                            type_naturally(name_input, document["name"], 'fast')
                            break
                    except:
                        continue
                
                if not name_input:
                    print("⚠️ Could not find document name field. Using JavaScript fallback.")
                    # Try JavaScript as last resort
                    driver.execute_script(
                        'Array.from(document.querySelectorAll("input[type=\'text\']")).filter(i => !i.value)[0].value = arguments[0]', 
                        document["name"]
                    )
                
                # Try to find description field with multiple selectors
                desc_input = None
                desc_selectors = [
                    (By.NAME, "document_description"),
                    (By.ID, "document_description"),
                    (By.TAG_NAME, "textarea"),
                    (By.CSS_SELECTOR, "textarea"),
                ]
                
                for selector in desc_selectors:
                    try:
                        desc_input = WebDriverWait(driver, 2).until(
                            EC.presence_of_element_located(selector)
                        )
                        if desc_input:
                            print(f"Found description input with selector: {selector}")
                            highlight_element(driver, desc_input, "info", 0.7)
                            type_naturally(desc_input, document["description"], 'fast')
                            break
                    except:
                        continue
                
                # Try to find tags field with multiple selectors
                tags_input = None
                tags_selectors = [
                    (By.NAME, "tags"),
                    (By.ID, "tags"),
                    (By.CSS_SELECTOR, "input[placeholder*='tag' i]"),
                ]
                
                for selector in tags_selectors:
                    try:
                        tags_input = WebDriverWait(driver, 2).until(
                            EC.presence_of_element_located(selector)
                        )
                        if tags_input:
                            print(f"Found tags input with selector: {selector}")
                            highlight_element(driver, tags_input, "info", 0.7)
                            type_naturally(tags_input, document["tags"], 'fast')
                            break
                    except:
                        continue
            
                # Upload file - try different selectors
                file_input = None
                file_selectors = [
                    (By.NAME, "file"),
                    (By.ID, "file"),
                    (By.CSS_SELECTOR, "input[type='file']"),
                    (By.XPATH, "//input[@type='file']")
                ]
                
                for selector in file_selectors:
                    try:
                        file_input = driver.find_element(*selector)
                        print(f"Found file input with selector: {selector}")
                        break
                    except:
                        continue
                        
                if file_input:
                    file_input.send_keys(document["path"])
                    print(f"Selected file: {document['path']}")
                else:
                    print("⚠️ Could not find file input field")
                    continue
                
                # Submit the form - try multiple approaches
                print("Submitting upload form...")
                submit_selectors = [
                    (By.XPATH, "//button[contains(text(), 'Upload')]"),
                    (By.XPATH, "//button[contains(text(), 'Submit')]"),
                    (By.XPATH, "//button[@type='submit']"),
                    (By.CSS_SELECTOR, "form button[type='submit']"),
                    (By.CSS_SELECTOR, "button.btn-primary"),
                    (By.CSS_SELECTOR, "form button")
                ]
                
                form_submitted = False
                for selector in submit_selectors:
                    try:
                        button = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable(selector)
                        )
                        highlight_element(driver, button, "success", 0.7)
                        button.click()
                        form_submitted = True
                        print(f"Clicked submit button with selector: {selector}")
                        break
                    except Exception as e:
                        print(f"Submit button not found or not clickable with selector: {selector}")
                
                if not form_submitted:
                    # Try submitting the form directly as a last resort
                    try:
                        form = driver.find_element(By.TAG_NAME, "form")
                        print("Found form, attempting direct submission...")
                        driver.execute_script("arguments[0].submit();", form)
                        form_submitted = True
                        print("Submitted form using JavaScript")
                    except Exception as e:
                        print(f"Could not submit form: {e}")
                
                # Wait longer for upload to complete
                time.sleep(8)
                take_screenshot(driver, f"after_upload_{idx+1}")
                
                # Check if we were redirected back to the upload page or to an error page
                current_url = driver.current_url
                print(f"Current URL after upload: {current_url}")
                
                # Check for success message or errors
                try:
                    alerts = driver.find_elements(By.CSS_SELECTOR, ".alert, .flash-message, .notification")
                    if alerts:
                        for alert in alerts:
                            alert_text = alert.text
                            alert_class = alert.get_attribute("class")
                            print(f"Alert found: [{alert_class}] {alert_text}")
                            
                            if "success" in alert_class.lower() and "upload" in alert_text.lower():
                                print(f"✅ Document '{document['name']}' uploaded successfully")
                                highlight_element(driver, alert, "success", 0.7)
                            elif "error" in alert_class.lower() or "danger" in alert_class.lower():
                                print(f"❌ Upload error: {alert_text}")
                                highlight_element(driver, alert, "error", 0.7)
                                # If there was an error, continue to next document
                                continue
                except:
                    print("No alert messages found")
                    
            except Exception as upload_error:
                print(f"⚠️ Error uploading document {idx+1}: {str(upload_error)}")
                take_screenshot(driver, f"upload_error_{idx+1}")
                continue  # Try the next document even if this one failed
                
        # STEP 4: Go to all documents page
        print("\n📚 STEP 4: Viewing all documents...")
        
        # First try the route with view prefix (based on blueprint registration)
        driver.get(VIEW_ROUTES['all_documents'])
        time.sleep(2)  # Reduced wait time
        
        # If URL redirected or page not found, try alternate URL
        if "404" in driver.title or "not found" in driver.title.lower():
            fallback_url = VIEW_ROUTES['documents_alt']
            print(f"⚠️ Primary URL failed. Trying fallback URL: {fallback_url}")
            driver.get(fallback_url)
            time.sleep(2)  # Reduced wait time
            
        print(f"📚 On documents page: {driver.current_url}")
        take_screenshot(driver, "all_documents")
        
        # STEP 4.1: Search for documents with keyword "blockchain"
        print("\n🔎 Searching for documents with keyword: 'blockchain'")
        
        # Look for search input with multiple selectors
        search_selectors = [
            (By.ID, "keyword-search"),
            (By.NAME, "keyword"),
            (By.NAME, "search"),
            (By.CSS_SELECTOR, "input[placeholder*='search' i]"),
            (By.CSS_SELECTOR, "input[placeholder*='keyword' i]"),
            (By.CSS_SELECTOR, "input[type='text']")
        ]
        
        search_input = None
        for selector in search_selectors:
            try:
                elements = driver.find_elements(*selector)
                for elem in elements:
                    if elem.is_displayed():
                        search_input = elem
                        print(f"Found search input with selector: {selector}")
                        break
                if search_input:
                    break
            except:
                continue
        
        if search_input:
            # Highlight and fill search field
            highlight_element(driver, search_input, "info", 0.5)
            search_keyword = "blockchain"
            type_naturally(search_input, search_keyword, 'fast')
            
            # Find and click search button or press Enter
            search_button = None
            search_button_selectors = [
                (By.XPATH, "//button[contains(text(), 'Search')]"),
                (By.CSS_SELECTOR, "button.search-button"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(@class, 'search')]"),
                (By.XPATH, "//i[contains(@class, 'fa-search')]/parent::button")
            ]
            
            for selector in search_button_selectors:
                try:
                    buttons = driver.find_elements(*selector)
                    for btn in buttons:
                        if btn.is_displayed():
                            search_button = btn
                            break
                    if search_button:
                        break
                except:
                    continue
            
            if search_button:
                highlight_element(driver, search_button, "success", 0.5)
                search_button.click()
                print("Clicked search button")
            else:
                # Press Enter if button not found
                print("No search button found, pressing Enter")
                from selenium.webdriver.common.keys import Keys
                search_input.send_keys(Keys.ENTER)
            
            # Wait for search results
            time.sleep(1.5)
            take_screenshot(driver, "search_results")
            print("✅ Search completed. Showing documents with 'blockchain' keyword.")
        else:
            print("⚠️ Could not find search input, proceeding without keyword search.")
        
        # STEP 5: View document details and verify document integrity
        print("\n🔍 STEP 5: Viewing and verifying documents...")
        
        try:
            # Get document cards after search
            cards = driver.find_elements(By.CSS_SELECTOR, ".document-card")
            if cards:
                # Specifically look for "View" buttons (NOT "Open")
                view_buttons = []
                
                # First highlight the target card
                if len(cards) > 0:
                    highlight_element(driver, cards[0], "info", 0.5)
                
                for card in cards[:3]:
                    try:
                        view_button_selectors = [
                            ".//a[contains(text(), 'View') and not(contains(text(), 'Open'))]",
                            ".//button[contains(text(), 'View') and not(contains(text(), 'Open'))]",
                            ".//a[contains(@class, 'btn')][contains(text(), 'View')]",
                            ".//a[contains(@href, 'view/document') or contains(@href, 'document/')]"
                        ]
                        
                        for selector in view_button_selectors:
                            buttons = card.find_elements(By.XPATH, selector)
                            for button in buttons:
                                if button.is_displayed():
                                    view_buttons.append(button)
                                    print(f"Found View button with text: '{button.text}'")
                                    highlight_element(driver, button, "success", 0.5)
                                    break
                            if view_buttons:
                                break
                    except Exception as e:
                        print(f"Error finding view button: {e}")
                
                if view_buttons:
                    print(f"Found {len(view_buttons)} 'View' buttons (excluding 'Open' buttons)")
                    view_url = view_buttons[0].get_attribute('href')
                    print(f"Navigating to document details view: {view_url}")
                    
                    # Navigate to document details
                    driver.get(view_url)
                    time.sleep(1.5)
                    take_screenshot(driver, "document_detail_view")
                    
                    # Extract document ID for later
                    document_id = None
                    try:
                        # Try different selectors for document ID
                        id_selectors = [
                            ".document-id", 
                            "[data-document-id]", 
                            ".meta-value"
                        ]
                        for selector in id_selectors:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            for elem in elements:
                                text = elem.text.strip()
                                if "-" in text and len(text) > 8:
                                    document_id = text
                                    print(f"Found document ID: {document_id}")
                                    break
                            if document_id:
                                break
                        
                        # Extract from URL if not found elsewhere
                        if not document_id and "/document/" in driver.current_url:
                            parts = driver.current_url.split("/document/")
                            if len(parts) > 1:
                                document_id = parts[1].split("/")[0].strip()
                                print(f"Extracted document ID from URL: {document_id}")
                    except Exception as e:
                        print(f"Error extracting document ID: {e}")
                    
                    # Scroll down to view document content
                    print("Scrolling down to view document content...")
                    scroll_smoothly(driver, 'down', 'fast')
                    time.sleep(0.5)
                    
                    # Scroll back up to find verification options
                    print("Scrolling up to find verification options...")
                    scroll_smoothly(driver, 'top', 'fast')
                    time.sleep(0.5)
                    
                    # Look for verify button
                    verify_selectors = [
                        "//a[contains(text(), 'Verify')]",
                        "//button[contains(text(), 'Verify')]",
                        "//a[contains(@href, 'verif')]",
                        "//a[contains(@class, 'verify')]"
                    ]
                    
                    verify_element = None
                    for selector in verify_selectors:
                        try:
                            elements = driver.find_elements(By.XPATH, selector)
                            for elem in elements:
                                if elem.is_displayed():
                                    verify_element = elem
                                    print(f"Found verify button: {elem.text}")
                                    break
                            if verify_element:
                                break
                        except:
                            continue
                    
                    if verify_element:
                        # Highlight and click the verification link
                        highlight_element(driver, verify_element, "success", 0.5)
                        verify_url = verify_element.get_attribute('href')
                        if verify_url:
                            driver.get(verify_url)
                        else:
                            verify_element.click()
                        
                        time.sleep(1.5)
                        take_screenshot(driver, "verification_page")
                        
                        # Find and click verify document button on verification page
                        verify_document_selectors = [
                            "//button[contains(text(), 'Verify')]",
                            "//button[@id='verify-btn']",
                            "//button[contains(@class, 'primary')]"
                        ]
                        
                        for selector in verify_document_selectors:
                            try:
                                verify_btn = WebDriverWait(driver, 2).until(
                                    EC.element_to_be_clickable((By.XPATH, selector))
                                )
                                highlight_element(driver, verify_btn, "success", 0.5)
                                verify_btn.click()
                                print("Clicked verify document button")
                                break
                            except:
                                continue
                        
                        # Wait for verification results
                        time.sleep(3)
                        take_screenshot(driver, "verification_results")
                        
                        # Scroll down slightly to show full results
                        scroll_smoothly(driver, 'down', 'fast', 200)
                        time.sleep(2)
                        take_screenshot(driver, "verification_results_scrolled")
                        
                        # STEP 6: Logout
                        print("\n🚪 STEP 6: Logging out...")
                        
                        # Find logout button in navbar
                        logout_selectors = [
                            "//a[contains(text(), 'Logout')]",
                            "//button[contains(text(), 'Logout')]",
                            "//a[contains(@href, 'logout')]",
                            "//a[contains(text(), 'Sign Out')]"
                        ]
                        
                        for selector in logout_selectors:
                            try:
                                logout_btn = driver.find_element(By.XPATH, selector)
                                if logout_btn.is_displayed():
                                    highlight_element(driver, logout_btn, "warning", 0.5)
                                    logout_btn.click()
                                    print("Clicked logout button")
                                    time.sleep(1)
                                    take_screenshot(driver, "after_logout")
                                    break
                            except:
                                continue
                    else:
                        print("⚠️ Could not find verification button")
                else:
                    print("⚠️ No View buttons found")
            else:
                print("⚠️ No document cards found")
                
        except Exception as e:
            print(f"⚠️ Error during document viewing/verification: {e}")
            take_screenshot(driver, "error_in_verification")
    
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        take_screenshot(driver, "error_state")
        return False
        
    finally:
        # Keep browser open for a moment to show final state
        time.sleep(5)
        driver.quit()
        
        print("\n📋 Demo Summary:")
        print(f"- Account created: {DEMO_EMAIL}")
        print(f"- Documents uploaded: {len(DEMO_DOCUMENTS)}")
        print(f"- All screenshots saved to: {SCREENSHOTS_DIR}")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Demo completed successfully!")
    else:
        print("\n❌ Demo failed to complete.")
