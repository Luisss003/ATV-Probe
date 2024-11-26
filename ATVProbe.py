import subprocess
import socket
import os
import json
import re
import time

#Stores last used IP address; if doesnt exist, creates file and appends address
ADDR_FILE = "tv_ip.txt"

#opens file to save most recently used IP address
def save_ip_address(ip_address):
    with open(ADDR_FILE, 'w') as file:
        file.write(ip_address)

#Opens file, and reads first line containing last used IP address and returns it; if file empty, then return None
def load_last_ip():
    if os.path.exists(ADDR_FILE):
        with open(ADDR_FILE, 'r') as file:
            return file.read().strip()
    return None

#Opens application by sending API request to Television
def launch_application(ip_address, psk, app_list):
    #Prompt user for name of application
    app_name = input("Enter the name of the application to launch: ").strip()
    #This looks for the app supplied by the user in the parameter app_list, which contains a list of ASCII formatted app names
    #if it is found, return it and assign it to the local variable; otherwise return none, meaning app not found
    app = next((app for app in app_list if app['title'].lower() == app_name.lower()), None)

    #if the app was found
    if app:
        #Set API endpoint
        url = f"http://{ip_address}/sony/appControl"
        #Set REST headers
        headers = [
            "-H", "Content-Type: application/json; charset=UTF-8",
            "-H", f"X-Auth-PSK: {psk}"
        ]
        #Set REST API request
        data = json.dumps({"method": "setActiveApp", "id": 601, "params": [{"uri": app["uri"]}], "version": "1.0"})
        #Construct curl command
        curl_command = ["curl", "-s", "-X", "POST", url] + headers + ["-d", data]
        #Attempt to run curl command via subprocess on terminal
        try: #If successful should activate app and display success result
            result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
            response = json.loads(result.stdout)
            if "result" in response:
                print(f"Application '{app_name}' launched successfully.")
            else: #otherwise send error message
                print(f"Failed to launch application '{app_name}'. Error:", response)
        except Exception as e:
            print("Error while launching application:", e)
    else: #App not found
        print(f"Application '{app_name}' not found.")

#Retrieve list of applications on users' televisions and return in formatted list
def get_application_list(ip_address, psk):
    #Set endpoint
    url = f"http://{ip_address}/sony/appControl"
    headers = [
        "-H", "Content-Type: application/json; charset=UTF-8",
        "-H", f"X-Auth-PSK: {psk}"
    ]
    data = json.dumps({"method": "getApplicationList", "id": 60, "params": [], "version": "1.0"})
    curl_command = ["curl", "-s", "-X", "POST", url] + headers + ["-d", data]

    try: #Run command via subprocess; if successful will return unformatted list of applications
        result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
        app_list_response = json.loads(result.stdout)
        app_list = app_list_response.get("result", [[]])[0] #formats response
        return app_list
    except Exception as e:
        print("Failed to retrieve application list:", e)
        return None

#Will call upon function to read file that stores IP address; if something is read, will prompt user to know
# if they want to reuse address
def get_tv_ip_address():
    last_ip = load_last_ip()
    
    if last_ip: #if address is read
        use_last = input(f"Use the last-used IP address {last_ip}? (y/n): ").strip().lower()
        if use_last == 'y':
            return last_ip
    #if no address read, implying first time running program, prompt user for new one and save it
    new_ip = input("Enter the IP address of the TV: ").strip()
    save_ip_address(new_ip)  
    return new_ip

#Control television via API calls
def control_television():
    ip_address = get_tv_ip_address()
    psk = input("Enter the Pre-Shared Key (PSK) for authentication: ")
    command = input("Enter the command (power_on/power_off/mute/unmute/volume/get_app_list/launch_app): ").lower()

    headers = [
        "-H", "Content-Type: application/json; charset=UTF-8",
        "-H", f"X-Auth-PSK: {psk}"
    ]
    #Check for every command user input's and set local variables to fit as such
    if command == "power_on":
        data = json.dumps({"method": "setPowerStatus", "params": [{"status": True}], "id": 1, "version": "1.0"})
        url = f"http://{ip_address}/sony/system"
    elif command == "power_off":
        data = json.dumps({"method": "setPowerStatus", "params": [{"status": False}], "id": 1, "version": "1.0"})
        url = f"http://{ip_address}/sony/system"
    elif command == "mute":
        data = json.dumps({"method": "setAudioMute", "params": [{"status": True}], "id": 1, "version": "1.0"})
        url = f"http://{ip_address}/sony/audio"
    elif command == "unmute":
        data = json.dumps({"method": "setAudioMute", "params": [{"status": False}], "id": 1, "version": "1.0"})
        url = f"http://{ip_address}/sony/audio"
    elif command == "volume":
        volume_change = input("Enter volume change amount (e.g., -1 for down, +1 for up): ")
        data = json.dumps({"method": "setAudioVolume", "params": [{"target": "speaker", "volume": volume_change}], "id": 1, "version": "1.0"})
        url = f"http://{ip_address}/sony/audio"
    elif command == "get_app_list":
        app_list = get_application_list(ip_address, psk)
        if app_list:
            print("Available applications:")
            for app in app_list:
                print(f" - {app['title']}")
        else:
            print("Failed to retrieve application list.")
        return
    elif command == "launch_app":
        app_list = get_application_list(ip_address, psk)
        if app_list:
            launch_application(ip_address, psk, app_list)
        else:
            print("Failed to retrieve application list.")
        return
    else:
        print("Invalid command. Please choose power_on, power_off, mute, unmute, volume, get_app_list, or launch_app.")
        return
    #Construct curl command
    curl_command = ["curl", "-X", "POST", url] + headers + ["-d", data]

    try: #Attempt to run curl command via subprocess
        result = subprocess.run(curl_command, check=True, capture_output=True, text=True)
        print("Response from TV:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Failed to send command:", e)


# Function to send IRCC command
def send_ircc_command(ip_address, psk, ircc_code):
    #set endpoint
    url = f"http://{ip_address}/sony/ircc"
    headers = [
        "-H", "Content-Type: text/xml; charset=UTF-8",
        "-H", f"SOAPACTION: \"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC\"",
        "-H", f"X-Auth-PSK: {psk}"
    ]

    #formats XML message via SOAP formatting so that ircc endpoint can understand request
    xml_data = f"""
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
        <s:Body>
            <u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1">
                <IRCCCode>{ircc_code}</IRCCCode>
            </u:X_SendIRCC>
        </s:Body>
    </s:Envelope>
    """
    #construct curl command
    curl_command = ["curl", "-X", "POST", url] + headers + ["-d", xml_data.strip()]
    try: #attempt to run command
        result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
        print("Response from TV:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Failed to send IRCC command:", e)

# Virtual Remote Function
def virtual_remote():
    ip_address = get_tv_ip_address()
    psk = input("Enter the Pre-Shared Key (PSK) for authentication: ")
    #These codes are interpreted by TV via IR waves but we are sending direct binary/codes for TV to interpret
    ircc_codes = {
        "up": "AAAAAQAAAAEAAAB0Aw==",
        "down": "AAAAAQAAAAEAAAB1Aw==",
        "left": "AAAAAQAAAAEAAAA0Aw==",
        "right": "AAAAAQAAAAEAAAAzAw==",
        "confirm": "AAAAAQAAAAEAAABlAw==",
        "home": "AAAAAQAAAAEAAABgAw=="
    }
    #Basic menu option
    print("\nVirtual Remote Options: up, down, left, right, confirm, home, exit")
    while True:
        command = input("Enter a command: ").strip().lower()
        if command in ircc_codes:
            send_ircc_command(ip_address, psk, ircc_codes[command])
        elif command == "exit":
            break
        else:
            print("Invalid command. Please choose from: up, down, left, right, confirm, home, or exit.")

# Main menu function
def main_menu():
    #print logo coz y not ? ? ! >:))))
    print("""             ##                ##
              ##     ####     ##
               ################
            ######################
           #########################
         ######  ############  ######
        ##############################
        ##############################
        ###############################
 #####  ##############################  #####
##############################################
##############################################
##############################################
##############################################
##############################################
##############################################
##############################################
 ####  ################################  ####
       ################################
        ##############################
           ########################
              #######    ########
              #######    ########
              #######    ########
              #######    #######
              ######      ######              """)
    while True:
        print("\nSelect an option:")
        print("1. Control Television")
        print("2. Virtual Remote")
        print("3. Discover Android TVs on Network")
        print("4. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            # Call your existing control_television() function
            control_television()
        elif choice == "2":
            virtual_remote()
        elif choice == "3":
            try: #will run basic avahi-tools scan to identify all devices on network for 30 seconds
                print("Discovering devices on the network... (this will take up to 30 seconds)")
                subprocess.run(["avahi-browse", "-a", "--resolve"], timeout=30)
            except subprocess.TimeoutExpired:
                print("Discovery timed out after 30 seconds.")
            except Exception as e:
                print("Error running avahi-browse:", e)
        elif choice == "4":
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please select 1, 2, 3, or 4.")

if __name__ == "__main__":
    main_menu()
