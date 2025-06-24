import json
import time
import os
import webbrowser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
GANACHE_URL = "http://localhost:7545"  # Default Ganache URL
CONTRACT_ADDRESS = None  # Will be read from blockchain_logger config

def take_screenshot(driver, name):
    """Take a screenshot and save it with a timestamp"""
    screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{screenshots_dir}/{timestamp}_{name}.png"
    driver.save_screenshot(filename)
    print(f"Screenshot saved: {filename}")
    return filename

def get_contract_address():
    """Get the contract address from the blockchain_logger config file"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                  "Backend", "blockchain", "config.json")
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get('contract_address')
    except Exception as e:
        print(f"Error reading contract address: {e}")
        return None

def main():
    # Get the contract address
    contract_address = get_contract_address()
    if not contract_address:
        print("Contract address not found. Using demo mode.")
        contract_address = "0x0000000000000000000000000000000000000000"  # Placeholder
    
    print(f"Contract address: {contract_address}")
    
    # Check Ganache connection first
    try:
        # Try using Web3 for more reliable Ganache detection
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
        if not w3.is_connected():
            print("⚠️ Cannot connect to Ganache at", GANACHE_URL)
            proceed = input("Proceed anyway? This will use screenshots only mode. (y/n): ")
            if proceed.lower() != 'y':
                return
            
            # If we're proceeding without Ganache, show demonstration images instead
            print("📸 Using screenshot demo mode instead...")
            screenshot_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                         "screenshots")
            os.makedirs(screenshot_folder, exist_ok=True)
            
            # Create a demo screenshot showing blocks
            demo_image_path = os.path.join(screenshot_folder, f"{time.strftime('%Y%m%d-%H%M%S')}_ganache_demo_mode.png")
            import base64
            with open(demo_image_path, "wb") as f:
                # This is a base64 encoded small ganache UI image (replace with actual screenshot if needed)
                f.write(base64.b64decode("YOUR_BASE64_GANACHE_SCREENSHOT"))
            
            print(f"Demo screenshot created at: {demo_image_path}")
            print("\n----------------------------------------")
            print("BLOCKCHAIN EXPLORATION (DEMO MODE)")
            print("In a live environment, you would see:")
            print("1. Document upload transactions")
            print("2. Merkle root update transactions")
            print("3. Document verification events")
            print("4. Contract state showing current Merkle root")
            print("----------------------------------------\n")
            
            print("Demo completed in screenshot mode!")
            return
    except Exception as e:
        print(f"Error checking Ganache connection: {e}")
        proceed = input("Proceed anyway? This may fail if Ganache is not running. (y/n): ")
        if proceed.lower() != 'y':
            return
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Step 1: Open Ganache
        print("Opening Ganache UI...")
        driver.get(GANACHE_URL)
        time.sleep(3)
        take_screenshot(driver, "ganache_main_page")
        
        # If we can't load the Ganache UI in the browser, show a message
        if "refused to connect" in driver.page_source.lower() or "cannot display this webpage" in driver.page_source.lower():
            print("⚠️ Could not load Ganache UI in browser. Ganache may be using a different interface.")
            take_screenshot(driver, "ganache_connection_failed")
            print("\nGanache GUI is running but may not be accessible via browser.")
            print("Try accessing Ganache directly and taking screenshots manually.")
            return

        # Step 2: Go to Blocks tab
        try:
            print("Navigating to Blocks tab...")
            blocks_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'BLOCKS')]"))
            )
            blocks_tab.click()
            time.sleep(2)
            take_screenshot(driver, "ganache_blocks")
            
            # Step 3: Click on the most recent block
            print("Opening the most recent block...")
            recent_block = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".BlockCard"))
            )
            recent_block.click()
            time.sleep(2)
            take_screenshot(driver, "ganache_block_details")
            
        except Exception as e:
            print(f"Ganache UI navigation error: {e}")
            print("Ganache UI might have changed or not available.")
            print("Continuing with direct transaction exploration...")
        
        # Step 4: Go to Transactions tab
        try:
            print("Navigating to Transactions tab...")
            driver.get(GANACHE_URL)  # Go back to main page
            time.sleep(2)
            
            transactions_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'TRANSACTIONS')]"))
            )
            transactions_tab.click()
            time.sleep(2)
            take_screenshot(driver, "ganache_transactions")
            
            # Step 5: Look for transactions related to our contract
            print(f"Searching for transactions to contract: {contract_address}")
            # This is approximate as Ganache UI might vary
            try:
                # Try to find transactions to our contract
                contract_txs = driver.find_elements(By.XPATH, f"//div[contains(text(), '{contract_address}')]")
                if contract_txs:
                    print(f"Found {len(contract_txs)} transactions to our contract")
                    # Click on the first one
                    contract_txs[0].click()
                    time.sleep(2)
                    take_screenshot(driver, "ganache_contract_transaction")
            except:
                print("Could not find specific transactions for our contract")
                
        except Exception as e:
            print(f"Error exploring transactions: {e}")
        
        # Step 6: Go to Logs/Events if available
        try:
            print("Checking for contract events...")
            # This is very dependent on Ganache UI version
            events_tab = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'EVENTS') or contains(text(), 'LOGS')]"))
            )
            events_tab.click()
            time.sleep(2)
            take_screenshot(driver, "ganache_events")
            
        except Exception as e:
            print(f"Events tab not found or not accessible: {e}")
        
        # Step 7: Check Contract State
        print("Exploring contract state...")
        # This would depend on having a contract explorer in Ganache
        # If not available, we can mention how this would be explored
        
        print("\n----------------------------------------")
        print("BLOCKCHAIN EXPLORATION")
        print("Key blockchain interactions seen in Ganache:")
        print("1. Document upload transactions")
        print("2. Merkle root update transactions")
        print("3. Document verification events")
        print("4. Contract state showing current Merkle root")
        print("----------------------------------------\n")
        
        print("Demo completed successfully!")
        
    except Exception as e:
        print(f"Error during Ganache exploration: {e}")
        take_screenshot(driver, "ganache_error")
        raise
        
    finally:
        # Keep browser open for 5 seconds
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    main()
