# Standard library imports
import json
import os
import math
import time
import datetime
import threading 
import logging
import serial
import pprint
from queue import Queue
from threading import Thread
from collections import deque
from collections import Counter
from datetime import timezone
from datetime import timedelta

# PDF generation imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from flask import send_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Third-party imports
import cv2
import numpy as np
from ultralytics import YOLO
from paddleocr import PaddleOCR
import mysql.connector
from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session, flash
from flask import Response, stream_with_context
from werkzeug.security import generate_password_hash, check_password_hash


CAMERA_CONFIG = {
    'entrance': 0,  # First USB camera index for entrance
    'exit': 2,      # Second USB camera index for exit
    'single_camera_mode': False  # Set to False to use two separate cameras
}

# MySQL configuration
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''  
MYSQL_DATABASE = 'avbs' 

# Arduino configuration
ARDUINO_PORT = 'COM5'  # Change this to match your Arduino's COM port
ARDUINO_BAUD_RATE = 9600
arduino_connected = False
arduino_serial = None

YOLO_CONF_THRESHOLD = 0.25  # Confidence threshold for YOLO detection
PADDLE_OCR_CONF_THRESHOLD = 0.65  # Confidence threshold for OCR
SAVE_INTERVAL_SECONDS = 60  # Interval for saving JSON data
JSON_OUTPUT_DIR = "output_json"  # Directory for JSON output

# Create output directory if it doesn't exist
if not os.path.exists(JSON_OUTPUT_DIR):
    os.makedirs(JSON_OUTPUT_DIR)


# Other global variables
entrance_log_data = []
exit_log_data = []
current_detected_license_plate = {"entrance": None, "exit": None}
vehicle_status = {}  # Dictionary to track if vehicles are inside or outside the premises

notification_queues = set()
notification_lock = threading.Lock()

# Initialize Flask application
app = Flask(__name__)
app.secret_key = 'naledi08$'  #key for sessions

# Initialize Paddle OCR globally
try:
    ocr = PaddleOCR(use_angle_cls=True, use_gpu=False)
except Exception as e:
    logging.error(f"Error initializing PaddleOCR: {e}")
    exit()

# Initialize YOLO model globally
try:
    model = YOLO("C:/Users/ZIKLAGOTE/Desktop/AVBS-System/weights/yolov9.pt")
except Exception as e:
    logging.error(f"Error loading YOLO model: {e}")
    exit()

# Initialize camera captures
cap_entrance = None
cap_exit = None
try:
    if CAMERA_CONFIG['single_camera_mode']:
        cap_entrance = cv2.VideoCapture(CAMERA_CONFIG['entrance'])
        if not cap_entrance.isOpened():
            logging.warning(f"Failed to open entrance camera at index {CAMERA_CONFIG['entrance']}. Trying alternatives...")
            for i in range(4): # Try indices 0-3
                if i != CAMERA_CONFIG['entrance']:
                    cap_entrance_alt = cv2.VideoCapture(i)
                    if cap_entrance_alt.isOpened():
                        cap_entrance = cap_entrance_alt
                        logging.info(f"Successfully opened entrance camera on alternative index {i}")
                        CAMERA_CONFIG['entrance'] = i # Update config if successful
                        break
            if not cap_entrance.isOpened():
                logging.error("Could not open entrance camera on any available index.")
                exit()
        cap_exit = cap_entrance
        logging.info(f"Initialized single camera mode using camera index {CAMERA_CONFIG['entrance']}")
    else:
        cap_entrance = cv2.VideoCapture(CAMERA_CONFIG['entrance'])
        if not cap_entrance.isOpened():
            logging.warning(f"Failed to open entrance camera at index {CAMERA_CONFIG['entrance']}. Trying alternatives...")
            for i in range(4): # Try indices 0-3
                if i != CAMERA_CONFIG['entrance']: # Check against original config
                    cap_entrance_alt = cv2.VideoCapture(i)
                    if cap_entrance_alt.isOpened():
                        cap_entrance = cap_entrance_alt
                        logging.info(f"Successfully opened entrance camera on alternative index {i}")
                        CAMERA_CONFIG['entrance'] = i # Update config
                        break
            if not cap_entrance.isOpened():
                logging.error("Could not open entrance camera on any available index.")
                exit()

        cap_exit = cv2.VideoCapture(CAMERA_CONFIG['exit'])
        if not cap_exit.isOpened():
            logging.warning(f"Failed to open exit camera at index {CAMERA_CONFIG['exit']}. Trying alternatives...")
            current_entrance_idx = CAMERA_CONFIG['entrance']
            for i in range(4): # Try indices 0-3
                # Check against original exit config and current entrance index
                if i != current_entrance_idx and i != CAMERA_CONFIG['exit']:
                    cap_exit_alt = cv2.VideoCapture(i)
                    if cap_exit_alt.isOpened():
                        cap_exit = cap_exit_alt
                        logging.info(f"Successfully opened exit camera on alternative index {i}")
                        CAMERA_CONFIG['exit'] = i # Update config
                        break
            if not cap_exit.isOpened():
                logging.error("Could not open exit camera on any available index.")
                if cap_entrance: cap_entrance.release()
                exit()
        logging.info(f"Initialized dual camera mode: Entrance Cam Index {CAMERA_CONFIG['entrance']}, Exit Cam Index {CAMERA_CONFIG['exit']}")

    # Set camera properties
    for cam_obj, cam_name in [(cap_entrance, "entrance"), (cap_exit, "exit")]:
        if cam_obj and cam_obj.isOpened():
            # Skip setting properties for cap_exit if it's the same object as cap_entrance in single_camera_mode
            if CAMERA_CONFIG['single_camera_mode'] and cam_name == "exit" and cap_exit == cap_entrance:
                continue
            cam_obj.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cam_obj.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            logging.info(f"Set properties for {cam_name} camera.")

except Exception as e:
    logging.error(f"Critical error during camera initialization: {e}")
    if cap_entrance and cap_entrance.isOpened(): cap_entrance.release()
    if cap_exit and cap_exit.isOpened() and cap_exit != cap_entrance: cap_exit.release()
    cv2.destroyAllWindows()
    exit()

# Try to connect to Arduino
try:
    arduino_serial = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD_RATE, timeout=1)
    time.sleep(2)  # Wait for Arduino to reset
    arduino_connected = True
    logging.info(f"Connected to Arduino on {ARDUINO_PORT}")
except Exception as e:
    logging.error(f"Failed to connect to Arduino: {e}")
    arduino_connected = False

# Function to check and maintain Arduino connection
def check_arduino_connection():
    global arduino_connected, arduino_serial
    
    if not arduino_connected or arduino_serial is None:
        try:
            arduino_serial = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD_RATE, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset
            arduino_connected = True
            logging.info(f"Reconnected to Arduino on {ARDUINO_PORT}")
        except Exception as e:
            logging.error(f"Failed to reconnect to Arduino: {e}")
            arduino_connected = False
    
    return arduino_connected

# Add this function to periodically check Arduino connection
def arduino_watchdog():
    while True:
        check_arduino_connection()
        time.sleep(30)  # Check every 30 seconds

def paddle_ocr_process(frame, x1, y1, x2, y2):
    try:
        roi = frame[y1:y2, x1:x2]
        result = ocr.ocr(roi, det=False, rec=True, cls=False)
        text = ""
        for r in result:
            score = r[0][1] if not np.isnan(r[0][1]) else 0
            if score > PADDLE_OCR_CONF_THRESHOLD:
                extracted_text = r[0][0]
                text = ''.join(char for char in extracted_text if char.isupper() or char.isdigit())
                break
        return text
    except Exception as e:
        logging.error(f"Error during PaddleOCR: {e}")
        return ""

def save_json(license_plates, startTime, endTime, feed_type):
    try:
        # Use the provided startTime and endTime (which are local naive datetimes)
        # and the current local naive datetime for the filename.
        interval_data = {
            "Start Time": startTime.isoformat(),
            "End Time": endTime.isoformat(),
            "License Plate": list(license_plates),
            "Feed Type": feed_type
        }
        interval_file_path = os.path.join(JSON_OUTPUT_DIR, f"output_{feed_type}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.json")
        with open(interval_file_path, 'w') as f:
            json.dump(interval_data, f, indent=2)
        logging.info(f"Saved {feed_type} interval data to: {interval_file_path}")
    except Exception as e:
        logging.error(f"Error saving JSON data: {e}")

def save_vehicle_owner(license_plate, owner_name, owner_contact, owner_address):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS avbs (
                license_plate VARCHAR(255) PRIMARY KEY,
                owner_name VARCHAR(255) NOT NULL,
                owner_contact VARCHAR(255),
                owner_address TEXT,
                registration_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        sql = "INSERT INTO avbs (license_plate, owner_name, owner_contact, owner_address) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE owner_name=%s, owner_contact=%s, owner_address=%s, registration_timestamp=CURRENT_TIMESTAMP"
        val = (license_plate, owner_name, owner_contact, owner_address, owner_name, owner_contact, owner_address)
        cursor.execute(sql, val)
        conn.commit()
        logging.info(f"Saved/Updated owner details for license plate: {license_plate}")
        return True
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error saving owner details: {err}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/add_owner', methods=['GET'])
def add_owner_form():
    license_plate = request.args.get('license_plate', '')
    return render_template('add_owner_form.html', license_plate=license_plate)


@app.route('/add_owner_success/<license_plate>')
def add_owner_success(license_plate):
    return render_template('add_owner_success.html', license_plate=license_plate)

@app.route('/add_owner_failure')
def add_owner_failure():
    error = request.args.get('error', 'Unknown error occurred')
    return render_template('add_owner_failure.html', error=error)

@app.route('/owners')
def view_owners():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM avbs ORDER BY registration_timestamp DESC")
        owners = cursor.fetchall()
        return render_template('owners.html', owners=owners)
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error fetching owners: {err}")
        return "Error fetching owners", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- User Authentication Routes ---

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash('Username and password are required.')
            return render_template('signup.html')
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", 
                           (username, generate_password_hash(password)))
            conn.commit()
            flash('Account created! Please log in.')
            return redirect(url_for('login'))
        except mysql.connector.Error:
            flash('Username already exists.')
            return render_template('signup.html')
        finally:
            cursor.close()
            conn.close()
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username') # Or 'email' if your form uses that
        new_password = request.form.get('new_password')

        if not username or not new_password:
            flash('Username and new password are required.')
            return render_template('forgot_password.html')

        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE
            )
            cursor = conn.cursor(dictionary=True)

            # Check if the user exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user:
                # User exists, update the password
                hashed_password = generate_password_hash(new_password)
                cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed_password, username))
                conn.commit()
                flash('Password has been reset successfully. Please log in with your new password.')
                return redirect(url_for('login'))
            else:
                flash('Username not found.')
                return render_template('forgot_password.html')

        except mysql.connector.Error as err:
            logging.error(f"MySQL Error during password reset: {err}")
            flash('An error occurred while resetting the password. Please try again.')
            return render_template('forgot_password.html')
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return render_template('forgot_password.html')

@app.route('/admin/users')
def admin_users():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, is_admin, created_at FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/delete_owner/<license_plate>', methods=['DELETE'])
def delete_owner(license_plate):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        cursor.execute("DELETE FROM avbs WHERE license_plate = %s", (license_plate,))
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Owner deleted successfully'})
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error deleting owner: {err}")
        return jsonify({'status': 'error', 'message': 'Failed to delete owner'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/update_owner/<license_plate>', methods=['POST'])
def update_owner(license_plate):
    conn = None
    cursor = None
    try:
        owner_name = request.form['owner_name'].strip()
        owner_contact = request.form['owner_contact'].strip()
        owner_address = request.form['owner_address'].strip()
        
        if not owner_name:
            return jsonify({'status': 'error', 'message': 'Owner Name is required'}), 400
            
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE avbs 
            SET owner_name = %s, owner_contact = %s, owner_address = %s 
            WHERE license_plate = %s
        """, (owner_name, owner_contact, owner_address, license_plate))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': 'Owner details updated successfully'})
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error updating owner: {err}")
        return jsonify({'status': 'error', 'message': 'Failed to update owner details'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/save_owner', methods=['POST'])
def save_owner():
    license_plate = request.form['license_plate'].strip().upper()
    owner_name = request.form['owner_name'].strip()
    owner_contact = request.form['owner_contact'].strip()
    owner_address = request.form['owner_address'].strip()
    
    if not license_plate or not owner_name:
        return jsonify({
            'status': 'error',
            'message': 'License Plate and Owner Name are required'
        }), 400
    
    # Check if the license plate already exists
    if check_license_plate(license_plate):
        return jsonify({
            'status': 'duplicate',
            'message': 'This owner has already been saved in the database'
        }), 409
    
    if save_vehicle_owner(license_plate, owner_name, owner_contact, owner_address):
        return jsonify({
            'status': 'success',
            'message': 'Owner details saved successfully!'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to save owner details'
        }), 500


def check_license_plate(license_plate):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM avbs WHERE license_plate = %s", (license_plate,))
        result = cursor.fetchone()
        return bool(result)
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error checking license plate: {err}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def send_to_arduino(status):
    """Send status command to Arduino"""
    if not check_arduino_connection():
        logging.warning("Arduino not connected, cannot send command")
        return False
    
    try:
        command = f"STATUS:{status}\n"
        arduino_serial.write(command.encode())
        arduino_serial.flush()  
        logging.info(f"Sent to Arduino: {command.strip()}")
        
        time.sleep(0.1)  # Give Arduino time to respond
        if arduino_serial.in_waiting:
            response = arduino_serial.readline().decode().strip()
            logging.info(f"Arduino response: {response}")
        
        return True
    except Exception as e:
        logging.error(f"Error sending command to Arduino: {e}")
        arduino_connected = False  # Mark as disconnected to trigger reconnection
        return False

def control_servo(feed_type, action):
    """Control the servo motor via Arduino
    feed_type: 'entrance' or 'exit'
    action: 'open' or 'close'
    """
    if not check_arduino_connection():
        logging.error("Arduino not connected. Cannot control servo.")
        return False
    
    try:
        # Add debug logging
        logging.info(f"Sending command to Arduino: {feed_type.upper()}_{action.upper()}")
        
        # Send command to Arduino
        command = f"{feed_type.upper()}_{action.upper()}\n"
        arduino_serial.write(command.encode())
        arduino_serial.flush()  # Ensure data is sent immediately
        
        # Wait for response with timeout
        start_time = time.time()
        while time.time() - start_time < 2:  # 2 second timeout
            if arduino_serial.in_waiting:
                response = arduino_serial.readline().decode().strip()
                logging.info(f"Arduino response: {response}")
                return "OK" in response
            time.sleep(0.1)
        
        logging.error("No response from Arduino")
        return False
    except Exception as e:
        logging.error(f"Error controlling servo: {e}")
        arduino_connected = False  # Mark as disconnected to trigger reconnection
        return False


def update_vehicle_status(license_plate, feed_type):
    """
    Track vehicle entry/exit status and determine if entry/exit should be allowed
    Returns: (allow_action, status_message)
    """
    global vehicle_status
    
    # Default to allowing action
    allow_action = True
    status_message = "Access granted"
    
    if feed_type == "entrance":
        # Check if vehicle is already inside
        if license_plate in vehicle_status and vehicle_status[license_plate] == "inside":
            allow_action = False
            status_message = "Vehicle already inside - must exit first"
            logging.warning(f"Denied entry to {license_plate} - already inside")
        else:
            # Only allow entry if vehicle is not inside or was previously outside
            if license_plate not in vehicle_status or vehicle_status[license_plate] == "outside":
                vehicle_status[license_plate] = "inside"
                logging.info(f"Vehicle {license_plate} marked as inside")
            else:
                allow_action = False
                status_message = "Invalid vehicle state for entry"
    
    elif feed_type == "exit":
        # Check if vehicle is inside (can only exit if inside)
        if license_plate not in vehicle_status or vehicle_status[license_plate] != "inside":
            allow_action = False
            status_message = "Vehicle not inside - must enter first"
            logging.warning(f"Denied exit to {license_plate} - not inside")
        else:
            # Mark vehicle as outside
            vehicle_status[license_plate] = "outside"
            logging.info(f"Vehicle {license_plate} marked as outside")
    
    # Debug the current vehicle status after update
    debug_vehicle_status()
    
    return allow_action, status_message

def debug_vehicle_status():
    """Print the current vehicle status for debugging"""
    logging.info("Current vehicle status:")
    logging.info(pprint.pformat(vehicle_status))


def notify_plate_status(plate, is_registered):
    message = {
        "type": "plate_status",
        "plate": plate,
        "is_registered": is_registered,
        "message": f"License plate {plate} is {'registered' if is_registered else 'not registered'} in the system"
    }
    with notification_lock:
        for q in notification_queues:
            try:
                q.put(json.dumps(message))
            except Exception as e:
                logging.error(f"Error sending notification: {e}")

# In the generate_frames function, update the notification part:
def generate_frames(feed_type):
    global current_detected_license_plate
    cap = cap_entrance if feed_type == "entrance" else cap_exit
    startTime = time.time()
    license_plates = set()
    frame_count = 0
    process_every_n_frames = 3
    last_check_time = {}  # Track when we last checked each plate

    #variables to track last known positions and status
    last_detection = {
        'coords': None,
        'plate': None,
        'is_registered': None,
        'last_seen': 0
    }

    while True:
        ret, frame = cap.read()
        if not ret:
            logging.error(f"Failed to capture {feed_type} frame. Exiting.")
            break

        frame_count += 1
        currentTime = time.time()
        detected_plate_this_frame = None

        if frame_count % process_every_n_frames == 0:
            results = model.predict(frame, conf=YOLO_CONF_THRESHOLD)

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    coords = box.xyxy[0].cpu().numpy().astype(int)
                    x1, y1, x2, y2 = coords
                    label_text = paddle_ocr_process(frame, x1, y1, x2, y2)
                    if label_text:
                        detected_plate_this_frame = label_text
                        license_plates.add(label_text)

                        # Update last known position and check database
                        last_detection['coords'] = coords
                        last_detection['plate'] = label_text
                        last_detection['last_seen'] = currentTime

                        # Check if we need to verify this plate in the database
                        if (label_text not in last_check_time or 
                            currentTime - last_check_time[label_text] > 60):

                            is_registered = check_license_plate(label_text)
                            last_check_time[label_text] = currentTime
                            last_detection['is_registered'] = is_registered

                            # Send notification about plate status
                            try:
                                notify_plate_status(label_text, is_registered)
                                logging.info(f"Notification sent for plate {label_text} (registered: {is_registered})")
                            except Exception as e:
                                logging.error(f"Failed to send notification: {e}")
                                
                            # Control the barrier based on registration status
                            if is_registered:
                                # For registered vehicles
                                if feed_type == "entrance":
                                    # Check if vehicle is allowed to enter
                                    allow_entry, status_message = update_vehicle_status(label_text, feed_type)
                                    
                                    if allow_entry:
                                        # Open barrier for entrance
                                        send_to_arduino("REGISTERED")
                                        logging.info(f"Opening barrier for registered vehicle: {label_text}")
                                        
                                        # Update notification message
                                        message = {
                                            "type": "plate_status",
                                            "plate": label_text,
                                            "is_registered": True,
                                            "message": f"License plate {label_text} is registered. Access granted."
                                        }
                                        with notification_lock:
                                            for q in notification_queues:
                                                try:
                                                    q.put(json.dumps(message))
                                                except Exception as e:
                                                    logging.error(f"Error sending notification: {e}")
                                    else:
                                        # Keep barrier closed - vehicle already inside
                                        send_to_arduino("UNREGISTERED")
                                        logging.info(f"Keeping barrier closed for {label_text}: {status_message}")
                                        
                                        # Update notification message
                                        message = {
                                            "type": "plate_status",
                                            "plate": label_text,
                                            "is_registered": True,
                                            "message": f"License plate {label_text} is registered but {status_message.lower()}."
                                        }
                                        with notification_lock:
                                            for q in notification_queues:
                                                try:
                                                    q.put(json.dumps(message))
                                                except Exception as e:
                                                    logging.error(f"Error sending notification: {e}")
                                
                                elif feed_type == "exit":
                                    # Update vehicle status and open barrier for exit
                                    update_vehicle_status(label_text, feed_type)
                                    send_to_arduino("REGISTERED")
                                    logging.info(f"Opening barrier for exiting vehicle: {label_text}")
                            else:
                                # For unregistered vehicles
                                if feed_type == "entrance":
                                    # Keep barrier closed
                                    send_to_arduino("UNREGISTERED")
                                    logging.info(f"Keeping barrier closed for unregistered vehicle: {label_text}")

                            # Automatically log registered plates in the database
                            if is_registered:
                                try:
                                    conn = mysql.connector.connect(
                                        host=MYSQL_HOST,
                                        user=MYSQL_USER,
                                        password=MYSQL_PASSWORD,
                                        database=MYSQL_DATABASE
                                    )
                                    cursor = conn.cursor()
                                    cursor.execute('''
                                        CREATE TABLE IF NOT EXISTS access_logs (
                                            id INT AUTO_INCREMENT PRIMARY KEY,
                                            license_plate VARCHAR(255) NOT NULL,
                                            feed_type VARCHAR(50) NOT NULL,
                                            action VARCHAR(50) NOT NULL,
                                            timestamp DATETIME NOT NULL
                                        )
                                    ''')
                                    # Only log if not already logged recently (e.g., in the last 5 minutes), using Python's time
                                    five_minutes_ago_python_time = datetime.datetime.now() - datetime.timedelta(minutes=5)
                                    cursor.execute('''
                                        SELECT id FROM access_logs WHERE license_plate=%s AND feed_type=%s AND action=%s AND timestamp >= %s
                                    ''', (label_text, feed_type, "Auto", five_minutes_ago_python_time.strftime('%Y-%m-%d %H:%M:%S')))
                                    already_logged = cursor.fetchone()
                                    if not already_logged:
                                        # Use a fresh current time for the insert
                                        current_python_time_str_for_insert = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        cursor.execute('''
                                            INSERT INTO access_logs (license_plate, feed_type, action, timestamp)
                                            VALUES (%s, %s, %s, %s)
                                        ''', (label_text, feed_type, "Auto", current_python_time_str_for_insert))
                                        conn.commit()
                                    cursor.close()
                                    conn.close()
                                except Exception as e:
                                    logging.error(f"Failed to log access for plate {label_text}: {e}")

            current_detected_license_plate[feed_type] = detected_plate_this_frame

        # Draw the rectangle and text if we have a recent detection
        if last_detection['coords'] is not None and currentTime - last_detection['last_seen'] < 5:  # Show for 5 seconds
            x1, y1, x2, y2 = last_detection['coords']
            plate = last_detection['plate']
            is_registered = last_detection['is_registered']
            
            # Draw rectangle around the plate
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0) if is_registered else (0, 0, 255), 2)
            
            # Prepare status text based on registration status and feed type
            if is_registered:
                if feed_type == "exit":
                    status_text = "Now Exiting"
                    status_color = (255, 0, 0)  # Green for exiting
                else:
                    status_text = "Registered"
                    status_color = (0, 255, 0)  # Green for registered
            else:
                status_text = "Not Registered"
                status_color = (0, 0, 255)  # Red for not registered
            
            # Draw text for plate number and status
            cv2.putText(frame, plate, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, status_color, 2)
            cv2.putText(frame, status_text, (x1, y2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, status_color, 2)

        if (currentTime - startTime) >= SAVE_INTERVAL_SECONDS:
            endTime = datetime.datetime.now()
            # Pass the accumulated plates since the last save
            save_json(license_plates, datetime.datetime.fromtimestamp(startTime), endTime, feed_type) 
            startTime = time.time() # Reset timer
            license_plates.clear() # Clear plates for the next interval

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', entrance_log=entrance_log_data, exit_log=exit_log_data, current_plate=current_detected_license_plate)

# Update the video feed route to match the feed parameter
@app.route('/video_feed/<feed>')
def video_feed(feed):
    if feed == 'entrance':
        return Response(generate_frames('entrance'), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif feed == 'exit':
        return Response(generate_frames('exit'), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return "Invalid feed", 400

@app.route('/access/<feed_type>/<action>', methods=['POST'])
def handle_access_request(feed_type, action):
    global current_detected_license_plate, vehicle_status
    license_plate = current_detected_license_plate.get(feed_type)
    vehicle_id = license_plate if license_plate else "UNKNOWN"
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Log the current vehicle status for debugging
    logging.info(f"Current vehicle status before {action} at {feed_type}:")
    debug_vehicle_status()
    
    # Update vehicle status based on action
    if license_plate and action == "grant":
        if feed_type == "entrance":
            vehicle_status[license_plate] = "inside"
            logging.info(f"Manually marked vehicle {license_plate} as inside")
        elif feed_type == "exit":
            vehicle_status[license_plate] = "outside"
            logging.info(f"Manually marked vehicle {license_plate} as outside")
    
    # Only log if the license plate is registered
    if license_plate and check_license_plate(license_plate):
        # Insert into access_logs table only if not already logged for this plate, feed, and action
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                license_plate VARCHAR(255) NOT NULL,
                feed_type VARCHAR(50) NOT NULL,
                action VARCHAR(50) NOT NULL,
                timestamp DATETIME NOT NULL,
                UNIQUE KEY unique_log (license_plate, feed_type, action)
            )
        ''')
        # Check if already logged
        cursor.execute('''
            SELECT id FROM access_logs WHERE license_plate=%s AND feed_type=%s AND action=%s
        ''', (license_plate, feed_type, action))
        already_logged = cursor.fetchone()
        if not already_logged:
            cursor.execute('''
                INSERT INTO access_logs (license_plate, feed_type, action, timestamp)
                VALUES (%s, %s, %s, %s)
            ''', (license_plate, feed_type, action, timestamp))
            conn.commit()
        cursor.close()
        conn.close()
        log_entry = {"id": vehicle_id, "type": f"Access {action.capitalize()} ({feed_type})", "time": timestamp}
        if feed_type == 'entrance':
            entrance_log_data.append(log_entry)
        elif feed_type == 'exit':
            exit_log_data.append(log_entry)
        logging.info(f"Access {action} for {vehicle_id} at {timestamp} on {feed_type} feed.")
        
        # Log the updated vehicle status
        logging.info(f"Vehicle status after {action} at {feed_type}:")
        debug_vehicle_status()
        
        return jsonify({"message": f"Access {action.capitalize()} for {feed_type} feed, plate: {vehicle_id}"}), 200
    else:
        return jsonify({"message": "License plate not registered. Entry not logged."}), 403

@app.route('/logs')
def get_logs():
    return jsonify({"entrance_log": entrance_log_data, "exit_log": exit_log_data})

@app.route('/access_logs')
def access_logs():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, license_plate, feed_type, action, timestamp FROM access_logs ORDER BY timestamp DESC")
        logs = cursor.fetchall()
        # Separate logs by feed_type for entrance and exit
        entrance_log = [log for log in logs if log['feed_type'] == 'entrance']
        exit_log = [log for log in logs if log['feed_type'] == 'exit']
        return render_template('access_logs.html', entrance_log=entrance_log, exit_log=exit_log)
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error fetching access logs: {err}")
        return "Error fetching access logs", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/access_logs_data')
def access_logs_data():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        
        # Create access_logs table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                license_plate VARCHAR(255) NOT NULL,
                feed_type VARCHAR(50) NOT NULL,
                action VARCHAR(50) NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        
        # Fetch all logs
        cursor.execute("SELECT * FROM access_logs ORDER BY timestamp DESC")
        logs = cursor.fetchall()
        
        # Process logs for all_time_stats
        entrances = [log for log in logs if log['feed_type'].lower() == 'entrance']
        exits = [log for log in logs if log['feed_type'].lower() == 'exit']
        granted = [log for log in logs if log['action'].lower() in ['auto', 'manual-grant']]
        denied = [log for log in logs if log['action'].lower() in ['denied', 'manual-deny']]
        
        # Get unique plates
        registered_plates = set(log['license_plate'] for log in granted)
        unregistered_plates = set(log['license_plate'] for log in denied)
        
        # Find peak hour
        hour_counts = Counter()
        for log in logs:
            timestamp = log['timestamp']
            if hasattr(timestamp, 'hour'):
                hour = timestamp.hour
            else:
                # Handle string timestamps if needed
                try:
                    hour = datetime.datetime.fromisoformat(str(timestamp)).hour
                except:
                    hour = 0
            hour_counts[hour] += 1
        
        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 0
        
        # Calculate average daily traffic
        if logs:
            # Get unique dates from logs
            dates = set()
            for log in logs:
                timestamp = log['timestamp']
                if hasattr(timestamp, 'date'):
                    dates.add(timestamp.date())
                else:
                    try:
                        dates.add(datetime.datetime.fromisoformat(str(timestamp)).date())
                    except:
                        pass
            
            avg_traffic = round(len(logs) / max(1, len(dates)))
        else:
            avg_traffic = 0
        
        # Create all_time_stats dictionary
        all_time_stats = {
            'total_entrances': len(entrances),
            'total_exits': len(exits),
            'granted_access': len(granted),
            'denied_access': len(denied),
            'registered_vehicles': len(registered_plates),
            'unregistered_vehicles': len(unregistered_plates),
            'peak_hour': f"{peak_hour:02d}:00",
            'avg_traffic': avg_traffic
        }
        
        # Process data for charts (daily, weekly, monthly)
        now = datetime.datetime.now()
        
        # Create reportData structure
        report_data = {
            'day': process_period_data(logs, now, 'day'),
            'week': process_period_data(logs, now, 'week'),
            'month': process_period_data(logs, now, 'month')
        }
        
        return jsonify({
            'all_time_stats': all_time_stats,
            'report_data': report_data
        })
    
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error fetching reports data: {err}")
        return jsonify({'error': 'Error fetching reports data'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def process_period_data(logs, now, period_type):
    """Process logs for a specific time period (day, week, month)"""
    result = {
        'traffic': {
            'labels': [],
            'entrances': [],
            'exits': []
        },
        'access': {
            'granted': 0,
            'denied': 0
        }
    }
    
    # Define time ranges based on period type
    if period_type == 'day':
        # Last 24 hours in hourly intervals
        intervals = 24
        labels = [f"{h:02d}:00" for h in range(24)]
        
        # Initialize counters
        entrance_counts = [0] * intervals
        exit_counts = [0] * intervals
        
        # Count logs by hour
        for log in logs:
            timestamp = log['timestamp']
            if not hasattr(timestamp, 'hour'):
                try:
                    timestamp = datetime.datetime.fromisoformat(str(timestamp))
                except:
                    continue
                
            # Only count logs from today
            if timestamp.date() == now.date():
                hour = timestamp.hour
                if log['feed_type'].lower() == 'entrance':
                    entrance_counts[hour] += 1
                elif log['feed_type'].lower() == 'exit':
                    exit_counts[hour] += 1
                
                action_lower = log['action'].lower()
                if action_lower in ['auto', 'grant', 'manual-grant']:
                    result['access']['granted'] += 1
                elif action_lower in ['deny', 'manual-deny']:
                    result['access']['denied'] += 1
                # Other actions, if any, are not counted towards granted/denied in the pie chart
        
        result['traffic']['labels'] = labels
        result['traffic']['entrances'] = entrance_counts
        result['traffic']['exits'] = exit_counts
        
    elif period_type == 'week':
        # Last 7 days
        days = []
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Get the date for the past 7 days
        for i in range(6, -1, -1):
            days.append(now - datetime.timedelta(days=i))
        
        # Initialize counters
        entrance_counts = [0] * 7
        exit_counts = [0] * 7
        
        # Count logs by day
        for log in logs:
            timestamp = log['timestamp']
            if not hasattr(timestamp, 'date'):
                try:
                    timestamp = datetime.datetime.fromisoformat(str(timestamp))
                except:
                    continue
            
            # Check if log is within the last 7 days
            for i, day in enumerate(days):
                if timestamp.date() == day.date():
                    if log['feed_type'].lower() == 'entrance':
                        entrance_counts[i] += 1
                    elif log['feed_type'].lower() == 'exit':
                        exit_counts[i] += 1
                    
                    action_lower = log['action'].lower()
                    if action_lower in ['auto', 'grant', 'manual-grant']:
                        result['access']['granted'] += 1
                    elif action_lower in ['deny', 'manual-deny']:
                        result['access']['denied'] += 1
                    # Other actions, if any, are not counted
                    break
        
        # Use day names as labels
        result['traffic']['labels'] = [day_names[d.weekday()] for d in days]
        result['traffic']['entrances'] = entrance_counts
        result['traffic']['exits'] = exit_counts
        
    elif period_type == 'month':
        # Last 30 days in 6 intervals (5 days each)
        intervals = 6
        days_per_interval = 5
        
        # Create date ranges for labels
        date_ranges = []
        for i in range(intervals):
            start_day = now - datetime.timedelta(days=(intervals-i)*days_per_interval)
            end_day = start_day + datetime.timedelta(days=days_per_interval-1)
            date_ranges.append((start_day, end_day))
            
        # Create labels
        labels = [f"{start.strftime('%d/%m')}-{end.strftime('%d/%m')}" for start, end in date_ranges]
        
        # Initialize counters
        entrance_counts = [0] * intervals
        exit_counts = [0] * intervals
        
        # Count logs by interval
        for log in logs:
            timestamp = log['timestamp']
            if not hasattr(timestamp, 'date'):
                try:
                    timestamp = datetime.datetime.fromisoformat(str(timestamp))
                except:
                    continue
            
            # Check which interval this log belongs to
            for i, (start, end) in enumerate(date_ranges):
                if start.date() <= timestamp.date() <= end.date():
                    if log['feed_type'].lower() == 'entrance':
                        entrance_counts[i] += 1
                    elif log['feed_type'].lower() == 'exit':
                        exit_counts[i] += 1
                    
                    action_lower = log['action'].lower()
                    if action_lower in ['auto', 'grant', 'manual-grant']:
                        result['access']['granted'] += 1
                    elif action_lower in ['deny', 'manual-deny']:
                        result['access']['denied'] += 1
                    # Other actions, if any, are not counted
                    break
        
        result['traffic']['labels'] = labels
        result['traffic']['entrances'] = entrance_counts
        result['traffic']['exits'] = exit_counts
    
    return result

@app.route('/reports')
def reports():
    # Create a dictionary with all the stats needed by the template
    all_time_stats = {
        'total_entrances': 0,
        'total_exits': 0,
        'granted_access': 0,
        'denied_access': 0,
        'registered_vehicles': 0,
        'unregistered_vehicles': 0,
        'peak_hour': "00:00",
        'avg_traffic': 0
    }
    
    # You can populate these values from your database if needed
    # For example:
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        
        # Count total entrances
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE feed_type='entrance'")
        result = cursor.fetchone()
        if result:
            all_time_stats['total_entrances'] = result['count']
            
        # Count total exits
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE feed_type='exit'")
        result = cursor.fetchone()
        if result:
            all_time_stats['total_exits'] = result['count']
            
        # Count registered vehicles
        cursor.execute("SELECT COUNT(*) as count FROM avbs")
        result = cursor.fetchone()
        if result:
            all_time_stats['registered_vehicles'] = result['count']
            
        # You can add more database queries to populate other statistics
        
        cursor.close()
        conn.close()
    except Exception as e:
        logging.error(f"Error fetching report statistics: {e}")
    
    return render_template('reports.html', all_time_stats=all_time_stats)

def generate_pdf_report(report_type='all'):
    """
    Generate a PDF report of vehicle access logs
    report_type: 'all', 'entrance', 'exit', 'registered'
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # Add title
    title_style = styles['Heading1']
    title = Paragraph("AVBS System Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.25*inch))
    
    # Add date
    date_style = styles['Normal']
    date_text = Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
    elements.append(date_text)
    elements.append(Spacer(1, 0.25*inch))
    
    # Connect to database
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        
        # Add system statistics
        stats_style = styles['Heading2']
        stats_title = Paragraph("System Statistics", stats_style)
        elements.append(stats_title)
        elements.append(Spacer(1, 0.15*inch))
        
        # Get statistics
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE feed_type='entrance'")
        entrances = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE feed_type='exit'")
        exits = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM avbs")
        registered = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE action='Auto'")
        granted = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE action!='Auto'")
        denied = cursor.fetchone()['count']
        
        # Create statistics table
        stats_data = [
            ["Metric", "Value"],
            ["Total Entrances", entrances],
            ["Total Exits", exits],
            ["Registered Vehicles", registered],
            ["Access Granted", granted],
            ["Access Denied", denied]
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 1.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (1, 0), 12),
            ('BACKGROUND', (0, 1), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.25*inch))
        
        # Add access logs
        logs_style = styles['Heading2']
        logs_title = Paragraph("Recent Access Logs", logs_style)
        elements.append(logs_title)
        elements.append(Spacer(1, 0.15*inch))
        
        # Get logs based on report type
        if report_type == 'entrance':
            cursor.execute("SELECT * FROM access_logs WHERE feed_type='entrance' ORDER BY timestamp DESC LIMIT 50")
            logs_subtitle = Paragraph("Entrance Logs (Last 50 entries)", styles['Heading3'])
        elif report_type == 'exit':
            cursor.execute("SELECT * FROM access_logs WHERE feed_type='exit' ORDER BY timestamp DESC LIMIT 50")
            logs_subtitle = Paragraph("Exit Logs (Last 50 entries)", styles['Heading3'])
        elif report_type == 'registered':
            cursor.execute("""
                SELECT al.* FROM access_logs al
                JOIN avbs av ON al.license_plate = av.license_plate
                ORDER BY al.timestamp DESC LIMIT 50
            """)
            logs_subtitle = Paragraph("Registered Vehicle Logs (Last 50 entries)", styles['Heading3'])
        else:
            cursor.execute("SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT 50")
            logs_subtitle = Paragraph("All Access Logs (Last 50 entries)", styles['Heading3'])
        
        elements.append(logs_subtitle)
        elements.append(Spacer(1, 0.15*inch))
        
        logs = cursor.fetchall()
        
        if logs:
            # Create logs table
            logs_data = [["ID", "License Plate", "Type", "Action", "Timestamp"]]
            
            for log in logs:
                logs_data.append([
                    log['id'],
                    log['license_plate'],
                    log['feed_type'],
                    log['action'],
                    log['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(log['timestamp'], 'strftime') else str(log['timestamp'])
                ])
            
            logs_table = Table(logs_data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 1*inch, 2*inch])
            logs_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (4, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (4, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (4, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (4, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (4, 0), 12),
                ('BOTTOMPADDING', (0, 0), (4, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ]))
            elements.append(logs_table)
        else:
            no_logs = Paragraph("No logs found for the selected criteria.", styles['Normal'])
            elements.append(no_logs)
        
        # Add registered vehicles if report type is 'registered' or 'all'
        if report_type in ['registered', 'all']:
            elements.append(Spacer(1, 0.25*inch))
            vehicles_style = styles['Heading2']
            vehicles_title = Paragraph("Registered Vehicles", vehicles_style)
            elements.append(vehicles_title)
            elements.append(Spacer(1, 0.15*inch))
            
            cursor.execute("SELECT * FROM avbs ORDER BY registration_timestamp DESC LIMIT 50")
            vehicles = cursor.fetchall()
            
            if vehicles:
                # Create vehicles table
                vehicles_data = [["License Plate", "Owner Name", "Contact", "Registration Date"]]
                
                for vehicle in vehicles:
                    vehicles_data.append([
                        vehicle['license_plate'],
                        vehicle['owner_name'],
                        vehicle['owner_contact'] or 'N/A',
                        vehicle['registration_timestamp'].strftime('%Y-%m-%d') if hasattr(vehicle['registration_timestamp'], 'strftime') else str(vehicle['registration_timestamp'])
                    ])
                
                vehicles_table = Table(vehicles_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 1.5*inch])
                vehicles_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (3, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (3, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (3, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (3, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (3, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(vehicles_table)
            else:
                no_vehicles = Paragraph("No registered vehicles found.", styles['Normal'])
                elements.append(no_vehicles)
        
        # Build the PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error generating PDF report: {err}")
        return None
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn and conn.is_connected():
            conn.close()

@app.route('/generate_pdf/<report_type>')
def generate_pdf(report_type='all'):
    """Generate PDF report and send it to the client"""
    if report_type not in ['all', 'entrance', 'exit', 'registered']:
        report_type = 'all'
    
    pdf_buffer = generate_pdf_report(report_type)
    if pdf_buffer:
        return send_file(
            pdf_buffer,
            download_name=f'avbs_report_{report_type}_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
    else:
        return "Error generating PDF report", 500

# Add notification stream route
@app.route('/notifications/stream')
def stream_notifications():
    def event_stream():
        q = Queue()
        with notification_lock:
            notification_queues.add(q)
        try:
            while True:
                message = q.get()
                yield f"data: {message}\n\n"
        finally:
            with notification_lock:
                notification_queues.remove(q)

    return Response(stream_with_context(event_stream()),
                   mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache',
                           'Connection': 'keep-alive'})

# Add this route for manual testing
@app.route('/simulate_vehicle/<action>/<license_plate>', methods=['GET'])
def simulate_vehicle(action, license_plate):
    """
    Manually simulate vehicle entry/exit for testing
    action: 'enter' or 'exit'
    """
    if action == 'enter':
        feed_type = 'entrance'
    elif action == 'exit':
        feed_type = 'exit'
    else:
        return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
    
    # Simulate detection
    is_registered = check_license_plate(license_plate)
    if not is_registered:
        return jsonify({
            'status': 'error', 
            'message': f'License plate {license_plate} is not registered'
        }), 404
    
    # Update vehicle status
    allow_action, status_message = update_vehicle_status(license_plate, feed_type)
    
    # Control barrier based on status
    if allow_action:
        send_to_arduino("REGISTERED")
        message = f"Simulated {action} for {license_plate}: Barrier opened"
    else:
        send_to_arduino("UNREGISTERED")
        message = f"Simulated {action} for {license_plate}: {status_message}"
    
    # Debug current status
    debug_vehicle_status()
    
    return jsonify({
        'status': 'success',
        'message': message,
        'is_registered': is_registered,
        'allow_action': allow_action,
        'status_message': status_message,
        'vehicle_status': vehicle_status
    })

@app.route('/test_vehicle/<action>/<license_plate>', methods=['GET'])
def test_vehicle(action, license_plate):
    """
    Test vehicle entry/exit tracking
    action: 'enter' or 'exit'
    """
    if action not in ['enter', 'exit']:
        return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
    
    # Check if plate is registered
    is_registered = check_license_plate(license_plate)
    if not is_registered:
        return jsonify({
            'status': 'error', 
            'message': f'License plate {license_plate} is not registered'
        }), 404
    
    # Update vehicle status
    feed_type = 'entrance' if action == 'enter' else 'exit'
    allow_action, status_message = update_vehicle_status(license_plate, feed_type)
    
    # Control barrier based on status
    if allow_action:
        send_to_arduino("REGISTERED")
        message = f"Simulated {action} for {license_plate}: Barrier opened"
    else:
        send_to_arduino("UNREGISTERED")
        message = f"Simulated {action} for {license_plate}: {status_message}"
    
    # Debug current status
    debug_vehicle_status()
    
    return jsonify({
        'status': 'success' if allow_action else 'denied',
        'message': message,
        'is_registered': is_registered,
        'allow_action': allow_action,
        'status_message': status_message,
        'vehicle_status': vehicle_status
    })

@app.route('/test_arduino/<status>', methods=['GET'])
def test_arduino(status):
    """
    Test Arduino communication with a specific status
    status: 'REGISTERED' or 'UNREGISTERED'
    """
    if status not in ['REGISTERED', 'UNREGISTERED']:
        return jsonify({'status': 'error', 'message': 'Invalid status'}), 400
    
    result = send_to_arduino(status)
    
    if result:
        return jsonify({
            'status': 'success',
            'message': f'Sent {status} command to Arduino'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to send command to Arduino'
        }), 500

@app.route('/test_arduino')
def test_arduino_connection():
    """Test Arduino connection and servo control"""
    if send_to_arduino("TEST"):
        return "Arduino communication successful"
    else:
        return "Arduino communication failed"

@app.route('/manual_access', methods=['POST'])
def manual_access():
    try:
        data = request.get_json()
        license_plate = data['license_plate'].strip().upper()
        access_type = data['access_type']
        feed_type = data['feed_type']
        
        logging.info(f"Manual access request: {license_plate}, {access_type}, {feed_type}")
        
        if access_type == 'grant':
            # Log the manual access grant
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE
            )
            cursor = conn.cursor()
            
            # Log the manual access
            cursor.execute(
                "INSERT INTO access_logs (license_plate, feed_type, action, timestamp) VALUES (%s, %s, 'Manual-Grant', NOW())",
                (license_plate, feed_type)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            # Open the barrier
            if feed_type == 'entrance':
                allow_entry, status_message = update_vehicle_status(license_plate, feed_type)
                if allow_entry:
                    success = control_servo(feed_type, 'open')
                    if not success:
                        return jsonify({'status': 'error', 'message': 'Failed to open barrier'})
                    # Schedule gate closing after 5 seconds
                    def close_gate():
                        time.sleep(5)
                        control_servo(feed_type, 'close')
                    threading.Thread(target=close_gate, daemon=True).start()
                    return jsonify({'status': 'success', 'message': 'Access granted'})
                else:
                    return jsonify({'status': 'error', 'message': status_message})
            else:  # exit
                success = control_servo(feed_type, 'open')
                if not success:
                    return jsonify({'status': 'error', 'message': 'Failed to open barrier'})
                # Schedule gate closing
                def close_gate():
                    time.sleep(5)
                    control_servo(feed_type, 'close')
                threading.Thread(target=close_gate, daemon=True).start()
                return jsonify({'status': 'success', 'message': 'Access granted'})
        
        elif access_type == 'deny':
            # Log the manual access denial
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE
            )
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO access_logs (license_plate, feed_type, action, timestamp) VALUES (%s, %s, 'Manual-Deny', NOW())",
                (license_plate, feed_type)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            # Keep barrier closed
            return jsonify({'status': 'success', 'message': 'Access denied'})
        
        else:
            return jsonify({'status': 'error', 'message': 'Invalid access type'}), 400
            
    except Exception as e:
        logging.error(f"Error in manual access control: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def notify_unregistered_plate(plate):
    with notification_lock:
        for q in notification_queues:
            q.put(json.dumps({
                "type": "unregistered_plate",
                "plate": plate
            }))

# Add initialization function for the app
# Use before_request with a first-request flag
_first_request = True

@app.before_request
def initialize_app():
    """Initialize application state before first request"""
    global _first_request, vehicle_status
    
    if _first_request:
        _first_request = False
        vehicle_status = {}  # Reset vehicle status
        logging.info("Vehicle status tracking initialized")
        debug_vehicle_status()

if __name__ == '__main__':
    try:
        # Initialize camera captures
        try:
            if CAMERA_CONFIG['single_camera_mode']:
                # Single camera mode - use the same camera for both feeds
                cap_entrance = cv2.VideoCapture(CAMERA_CONFIG['entrance'])
                cap_exit = cap_entrance
                logging.info("Initialized single camera mode")
            else:
                # Dual camera mode - use separate cameras for entrance and exit
                cap_entrance = cv2.VideoCapture(CAMERA_CONFIG['entrance'])
                cap_exit = cv2.VideoCapture(CAMERA_CONFIG['exit'])
                logging.info("Initialized dual camera mode")
            
            # Check if cameras opened successfully
            if not cap_entrance.isOpened():
                logging.error(f"Failed to open entrance camera at index {CAMERA_CONFIG['entrance']}")
                # Try alternative indices
                for i in range(4):  # Try indices 0-3
                    if i != CAMERA_CONFIG['entrance']:
                        cap_entrance = cv2.VideoCapture(i)
                        if cap_entrance.isOpened():
                            logging.info(f"Successfully opened entrance camera on alternative index {i}")
                            break
                if not cap_entrance.isOpened():
                    raise Exception("Could not open entrance camera on any available index")
            
            if not CAMERA_CONFIG['single_camera_mode'] and not cap_exit.isOpened():
                logging.error(f"Failed to open exit camera at index {CAMERA_CONFIG['exit']}")
                # Try alternative indices
                for i in range(4):  # Try indices 0-3
                    if i != CAMERA_CONFIG['entrance'] and i != CAMERA_CONFIG['entrance']:
                        cap_exit = cv2.VideoCapture(i)
                        if cap_exit.isOpened():
                            logging.info(f"Successfully opened exit camera on alternative index {i}")
                            break
                if not cap_exit.isOpened():
                    cap_entrance.release()
                    raise Exception("Could not open exit camera on any available index")
            
            # Set camera properties (optional)
            for cap in [cap_entrance, cap_exit] if not CAMERA_CONFIG['single_camera_mode'] else [cap_entrance]:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
            logging.info("Camera initialization successful")
            
        except Exception as e:
            logging.error(f"Error initializing cameras: {e}")
            raise e
        app.run(debug=True, host='0.0.0.0')
    except Exception as e:
        logging.error(f"Camera initialization error: {e}")
        processing_active = False
        if plate_processing_thread and plate_processing_thread.is_alive():
            plate_processing_thread.join(timeout=1)
        print(f"Error: {e}")
        exit(1)
    finally:
        processing_active = False
        if plate_processing_thread and plate_processing_thread.is_alive():
            plate_processing_thread.join(timeout=1)
        if 'cap_entrance' in locals() and cap_entrance is not None:
            cap_entrance.release()
        if 'cap_exit' in locals() and cap_exit is not None and not CAMERA_CONFIG['single_camera_mode']:
            cap_exit.release()
        cv2.destroyAllWindows()

def send_to_arduino(status):
    """Send status command to Arduino"""
    if not check_arduino_connection():
        logging.warning("Arduino not connected, cannot send command")
        return False
    
    try:
        command = f"STATUS:{status}\n"
        arduino_serial.write(command.encode())
        arduino_serial.flush()  # Ensure data is sent immediately
        logging.info(f"Sent to Arduino: {command.strip()}")
        
        # Wait for and read the response from Arduino
        time.sleep(0.1)  # Give Arduino time to respond
        if arduino_serial.in_waiting:
            response = arduino_serial.readline().decode().strip()
            logging.info(f"Arduino response: {response}")
        
        return True
    except Exception as e:
        logging.error(f"Error sending command to Arduino: {e}")
        arduino_connected = False  # Mark as disconnected to trigger reconnection
        return False

def control_servo(feed_type, action):
    """Control the servo motor via Arduino
    feed_type: 'entrance' or 'exit'
    action: 'open' or 'close'
    """
    if not check_arduino_connection():
        logging.error("Arduino not connected. Cannot control servo.")
        return False
    
    try:
        # Add debug logging
        logging.info(f"Sending command to Arduino: {feed_type.upper()}_{action.upper()}")
        
        # Send command to Arduino
        command = f"{feed_type.upper()}_{action.upper()}\n"
        arduino_serial.write(command.encode())
        arduino_serial.flush()  # Ensure data is sent immediately
        
        # Wait for response with timeout
        start_time = time.time()
        while time.time() - start_time < 2:  # 2 second timeout
            if arduino_serial.in_waiting:
                response = arduino_serial.readline().decode().strip()
                logging.info(f"Arduino response: {response}")
                return "OK" in response
            time.sleep(0.1)
        
        logging.error("No response from Arduino")
        return False
    except Exception as e:
        logging.error(f"Error controlling servo: {e}")
        arduino_connected = False  # Mark as disconnected to trigger reconnection
        return False


def update_vehicle_status(license_plate, feed_type):
    """
    Track vehicle entry/exit status and determine if entry/exit should be allowed
    Returns: (allow_action, status_message)
    """
    global vehicle_status
    
    # Default to allowing action
    allow_action = True
    status_message = "Access granted"
    
    if feed_type == "entrance":
        # Check if vehicle is already inside
        if license_plate in vehicle_status and vehicle_status[license_plate] == "inside":
            allow_action = False
            status_message = "Vehicle already inside - must exit first"
            logging.warning(f"Denied entry to {license_plate} - already inside")
        else:
            # Only allow entry if vehicle is not inside or was previously outside
            if license_plate not in vehicle_status or vehicle_status[license_plate] == "outside":
                vehicle_status[license_plate] = "inside"
                logging.info(f"Vehicle {license_plate} marked as inside")
            else:
                allow_action = False
                status_message = "Invalid vehicle state for entry"
    
    elif feed_type == "exit":
        # Check if vehicle is inside (can only exit if inside)
        if license_plate not in vehicle_status or vehicle_status[license_plate] != "inside":
            allow_action = False
            status_message = "Vehicle not inside - must enter first"
            logging.warning(f"Denied exit to {license_plate} - not inside")
        else:
            # Mark vehicle as outside
            vehicle_status[license_plate] = "outside"
            logging.info(f"Vehicle {license_plate} marked as outside")
    
    # Debug the current vehicle status after update
    debug_vehicle_status()
    
    return allow_action, status_message

def debug_vehicle_status():
    """Print the current vehicle status for debugging"""
    logging.info("Current vehicle status:")
    logging.info(pprint.pformat(vehicle_status))

# Update the generate_frames function to include barrier control
def generate_frames(feed_type):
    global current_detected_license_plate
    cap = cap_entrance if feed_type == "entrance" else cap_exit
    startTime = time.time()
    license_plates = set()
    frame_count = 0
    process_every_n_frames = 3
    last_check_time = {}  # Track when we last checked each plate
    
    # Add these variables to track last known positions and status
    last_detection = {
        'coords': None,
        'plate': None,
        'is_registered': None,
        'last_seen': 0
    }

    while True:
        ret, frame = cap.read()
        if not ret:
            logging.error(f"Failed to capture {feed_type} frame. Exiting.")
            break
        
        frame_count += 1
        currentTime = time.time()
        detected_plate_this_frame = None

        if frame_count % process_every_n_frames == 0:
            results = model.predict(frame, conf=YOLO_CONF_THRESHOLD)

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    coords = box.xyxy[0].cpu().numpy().astype(int)
                    x1, y1, x2, y2 = coords
                    label_text = paddle_ocr_process(frame, x1, y1, x2, y2)
                    if label_text:
                        detected_plate_this_frame = label_text
                        license_plates.add(label_text)
                        
                        # Update last known position and check database
                        last_detection['coords'] = coords
                        last_detection['plate'] = label_text
                        last_detection['last_seen'] = currentTime
                        
                        # Check if we need to verify this plate in the database
                        if (label_text not in last_check_time or 
                            currentTime - last_check_time[label_text] > 60):
                            
                            is_registered = check_license_plate(label_text)
                            last_check_time[label_text] = currentTime
                            last_detection['is_registered'] = is_registered
                            
                            # Send notification about plate status
                            try:
                                notify_plate_status(label_text, is_registered)
                                logging.info(f"Notification sent for plate {label_text} (registered: {is_registered})")
                            except Exception as e:
                                logging.error(f"Failed to send notification: {e}")
                            
                            # After checking if plate is registered
                            if (label_text not in last_check_time or 
                                currentTime - last_check_time[label_text] > 60):
                                
                                is_registered = check_license_plate(label_text)
                                last_check_time[label_text] = currentTime
                                last_detection['is_registered'] = is_registered
                                
                                # Control the barrier based on registration status
                                if is_registered:
                                    # For registered vehicles
                                    if feed_type == "entrance":
                                        # Check if vehicle is allowed to enter
                                        allow_entry, status_message = update_vehicle_status(label_text, feed_type)
                                        
                                        if allow_entry:
                                            # Open barrier for entrance
                                            send_to_arduino("REGISTERED")
                                            logging.info(f"Opening barrier for registered vehicle: {label_text}")
                                            
                                            # Update notification message
                                            message = {
                                                "type": "plate_status",
                                                "plate": label_text,
                                                "is_registered": True,
                                                "message": f"License plate {label_text} is registered. Access granted."
                                            }
                                            with notification_lock:
                                                for q in notification_queues:
                                                    try:
                                                        q.put(json.dumps(message))
                                                    except Exception as e:
                                                        logging.error(f"Error sending notification: {e}")
                                        else:
                                            # Keep barrier closed - vehicle already inside
                                            send_to_arduino("UNREGISTERED")
                                            logging.info(f"Keeping barrier closed for {label_text}: {status_message}")
                                            
                                            # Update notification message
                                            message = {
                                                "type": "plate_status",
                                                "plate": label_text,
                                                "is_registered": True,
                                                "message": f"License plate {label_text} is registered but {status_message.lower()}."
                                            }
                                            with notification_lock:
                                                for q in notification_queues:
                                                    try:
                                                        q.put(json.dumps(message))
                                                    except Exception as e:
                                                        logging.error(f"Error sending notification: {e}")
                                    
                                    elif feed_type == "exit":
                                        # Check if vehicle is allowed to exit
                                        allow_exit, status_message = update_vehicle_status(label_text, feed_type)
                                        
                                        if allow_exit:
                                            # Open barrier for exit
                                            send_to_arduino("REGISTERED")
                                            logging.info(f"Opening barrier for exiting vehicle: {label_text}")
                                            
                                            # Update notification message
                                            message = {
                                                "type": "plate_status",
                                                "plate": label_text,
                                                "is_registered": True,
                                                "message": f"License plate {label_text} is registered. Now exiting."
                                            }
                                            with notification_lock:
                                                for q in notification_queues:
                                                    try:
                                                        q.put(json.dumps(message))
                                                    except Exception as e:
                                                        logging.error(f"Error sending notification: {e}")
                                        else:
                                            # Keep barrier closed - vehicle not inside
                                            send_to_arduino("UNREGISTERED")
                                            logging.info(f"Keeping barrier closed for {label_text}: {status_message}")
                                            
                                            # Update notification message
                                            message = {
                                                "type": "plate_status",
                                                "plate": label_text,
                                                "is_registered": True,
                                                "message": f"License plate {label_text} is registered but {status_message.lower()}."
                                            }
                                            with notification_lock:
                                                for q in notification_queues:
                                                    try:
                                                        q.put(json.dumps(message))
                                                    except Exception as e:
                                                        logging.error(f"Error sending notification: {e}")
                                else:
                                    # For unregistered vehicles
                                    if feed_type == "entrance":
                                        # Keep barrier closed
                                        send_to_arduino("UNREGISTERED")
                                        logging.info(f"Keeping barrier closed for unregistered vehicle: {label_text}")
                                        
                                        # Send notification about plate status
                                        try:
                                            notify_plate_status(label_text, is_registered)
                                            logging.info(f"Notification sent for plate {label_text} (registered: {is_registered})")
                                        except Exception as e:
                                            logging.error(f"Failed to send notification: {e}")
            
            current_detected_license_plate[feed_type] = detected_plate_this_frame

        # Draw the rectangle and text if we have a recent detection (within last 20 seconds)
        if last_detection['coords'] is not None and (currentTime - last_detection['last_seen']) < 20:  # Changed from 2 to 20
            x1, y1, x2, y2 = last_detection['coords']
            color = (0, 255, 0) if last_detection['is_registered'] else (0, 0, 255)
            status_text = "Registered" if last_detection['is_registered'] else "Not Registered"
            
            # Draw rectangle and text
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{last_detection['plate']} - {status_text}", 
                      (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 
                      0.7, color, 2)

        if (currentTime - startTime) >= SAVE_INTERVAL_SECONDS:
            endTime = datetime.datetime.now()
            # Pass the accumulated plates since the last save
            save_json(license_plates, datetime.datetime.fromtimestamp(startTime), endTime, feed_type) 
            startTime = time.time() # Reset timer
            license_plates.clear() # Clear plates for the next interval

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', entrance_log=entrance_log_data, exit_log=exit_log_data, current_plate=current_detected_license_plate)

# Update the video feed route to match the feed parameter
@app.route('/video_feed/<feed>')
def video_feed(feed):
    if feed == 'entrance':
        return Response(generate_frames('entrance'), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif feed == 'exit':
        return Response(generate_frames('exit'), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return "Invalid feed", 400

@app.route('/access/<feed_type>/<action>', methods=['POST'])
def handle_access_request(feed_type, action):
    global current_detected_license_plate, vehicle_status
    license_plate = current_detected_license_plate.get(feed_type)
    vehicle_id = license_plate if license_plate else "UNKNOWN"
    current_python_time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Log the current vehicle status for debugging
    logging.info(f"Current vehicle status before {action} at {feed_type}:")
    debug_vehicle_status()
    
    # Update vehicle status based on action
    if license_plate and action == "grant":
        if feed_type == "entrance":
            vehicle_status[license_plate] = "inside"
            logging.info(f"Manually marked vehicle {license_plate} as inside")
        elif feed_type == "exit":
            vehicle_status[license_plate] = "outside"
            logging.info(f"Manually marked vehicle {license_plate} as outside")
    
    # Only log if the license plate is registered
    if license_plate and check_license_plate(license_plate):
        # Insert into access_logs table only if not already logged for this plate, feed, and action
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                license_plate VARCHAR(255) NOT NULL,
                feed_type VARCHAR(50) NOT NULL,
                action VARCHAR(50) NOT NULL,
                timestamp DATETIME NOT NULL,
                UNIQUE KEY unique_log (license_plate, feed_type, action)
            )
        ''')
        # Check if already logged
        cursor.execute('''
            SELECT id FROM access_logs WHERE license_plate=%s AND feed_type=%s AND action=%s
        ''', (license_plate, feed_type, action))
        already_logged = cursor.fetchone()
        if not already_logged:
            cursor.execute('''
                INSERT INTO access_logs (license_plate, feed_type, action, timestamp)
                VALUES (%s, %s, %s, %s)
            ''', (license_plate, feed_type, action, current_python_time_str))
            conn.commit()
        cursor.close()
        conn.close()
        log_entry = {"id": vehicle_id, "type": f"Access {action.capitalize()} ({feed_type})", "time": current_python_time_str}
        if feed_type == 'entrance':
            entrance_log_data.append(log_entry)
        elif feed_type == 'exit':
            exit_log_data.append(log_entry)
        logging.info(f"Access {action} for {vehicle_id} at {current_python_time_str} on {feed_type} feed.")
        
        # Log the updated vehicle status
        logging.info(f"Vehicle status after {action} at {feed_type} (Python time: {current_python_time_str}):")
        debug_vehicle_status()
        
        return jsonify({"message": f"Access {action.capitalize()} for {feed_type} feed, plate: {vehicle_id}"}), 200
    else:
        return jsonify({"message": "License plate not registered. Entry not logged."}), 403

@app.route('/logs')
def get_logs():
    return jsonify({"entrance_log": entrance_log_data, "exit_log": exit_log_data})

@app.route('/access_logs')
def access_logs():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, license_plate, feed_type, action, timestamp FROM access_logs ORDER BY timestamp DESC")
        logs = cursor.fetchall()
        # Separate logs by feed_type for entrance and exit
        entrance_log = [log for log in logs if log['feed_type'] == 'entrance']
        exit_log = [log for log in logs if log['feed_type'] == 'exit']
        return render_template('access_logs.html', entrance_log=entrance_log, exit_log=exit_log)
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error fetching access logs: {err}")
        return "Error fetching access logs", 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

from collections import Counter

@app.route('/access_logs_data')
def access_logs_data():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        
        # Create access_logs table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                license_plate VARCHAR(255) NOT NULL,
                feed_type VARCHAR(50) NOT NULL,
                action VARCHAR(50) NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        
        # Fetch all logs
        cursor.execute("SELECT * FROM access_logs ORDER BY timestamp DESC")
        logs = cursor.fetchall()
        
        # Process logs for all_time_stats
        entrances = [log for log in logs if log['feed_type'].lower() == 'entrance']
        exits = [log for log in logs if log['feed_type'].lower() == 'exit']
        granted = [log for log in logs if log['action'].lower() in ['auto', 'manual-grant']]
        denied = [log for log in logs if log['action'].lower() in ['denied', 'manual-deny']]
        
        # Get unique plates
        registered_plates = set(log['license_plate'] for log in granted)
        unregistered_plates = set(log['license_plate'] for log in denied)
        
        # Find peak hour
        hour_counts = Counter()
        for log in logs:
            timestamp = log['timestamp']
            if hasattr(timestamp, 'hour'):
                hour = timestamp.hour
            else:
                # Handle string timestamps if needed
                try:
                    hour = datetime.datetime.fromisoformat(str(timestamp)).hour
                except:
                    hour = 0
            hour_counts[hour] += 1
        
        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 0
        
        # Calculate average daily traffic
        if logs:
            # Get unique dates from logs
            dates = set()
            for log in logs:
                timestamp = log['timestamp']
                if hasattr(timestamp, 'date'):
                    dates.add(timestamp.date())
                else:
                    try:
                        dates.add(datetime.datetime.fromisoformat(str(timestamp)).date())
                    except:
                        pass
            
            avg_traffic = round(len(logs) / max(1, len(dates)))
        else:
            avg_traffic = 0
        
        # Create all_time_stats dictionary
        all_time_stats = {
            'total_entrances': len(entrances),
            'total_exits': len(exits),
            'granted_access': len(granted),
            'denied_access': len(denied),
            'registered_vehicles': len(registered_plates),
            'unregistered_vehicles': len(unregistered_plates),
            'peak_hour': f"{peak_hour:02d}:00",
            'avg_traffic': avg_traffic
        }
        
        # Process data for charts (daily, weekly, monthly)
        now = datetime.datetime.now()
        
        # Create reportData structure
        report_data = {
            'day': process_period_data(logs, now, 'day'),
            'week': process_period_data(logs, now, 'week'),
            'month': process_period_data(logs, now, 'month')
        }
        
        return jsonify({
            'all_time_stats': all_time_stats,
            'report_data': report_data
        })
    
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error fetching reports data: {err}")
        return jsonify({'error': 'Error fetching reports data'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/reports')
def reports():
    # Create a dictionary with all the stats needed by the template
    all_time_stats = {
        'total_entrances': 0,
        'total_exits': 0,
        'granted_access': 0,
        'denied_access': 0,
        'registered_vehicles': 0,
        'unregistered_vehicles': 0,
        'peak_hour': "00:00",
        'avg_traffic': 0
    }
    
    # You can populate these values from your database if needed
    # For example:
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        
        # Count total entrances
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE feed_type='entrance'")
        result = cursor.fetchone()
        if result:
            all_time_stats['total_entrances'] = result['count']
            
        # Count total exits
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE feed_type='exit'")
        result = cursor.fetchone()
        if result:
            all_time_stats['total_exits'] = result['count']
            
        # Count registered vehicles
        cursor.execute("SELECT COUNT(*) as count FROM avbs")
        result = cursor.fetchone()
        if result:
            all_time_stats['registered_vehicles'] = result['count']
            
        # You can add more database queries to populate other statistics
        
        cursor.close()
        conn.close()
    except Exception as e:
        logging.error(f"Error fetching report statistics: {e}")
    
    return render_template('reports.html', all_time_stats=all_time_stats)

def generate_pdf_report(report_type='all'):
    """
    Generate a PDF report of vehicle access logs
    report_type: 'all', 'entrance', 'exit', 'registered'
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # Add title
    title_style = styles['Heading1']
    title = Paragraph("AVBS System Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.25*inch))
    
    # Add date
    date_style = styles['Normal']
    date_text = Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
    elements.append(date_text)
    elements.append(Spacer(1, 0.25*inch))
    
    # Connect to database
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        
        # Add system statistics
        stats_style = styles['Heading2']
        stats_title = Paragraph("System Statistics", stats_style)
        elements.append(stats_title)
        elements.append(Spacer(1, 0.15*inch))
        
        # Get statistics
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE feed_type='entrance'")
        entrances = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE feed_type='exit'")
        exits = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM avbs")
        registered = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE action='Auto'")
        granted = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM access_logs WHERE action!='Auto'")
        denied = cursor.fetchone()['count']
        
        # Create statistics table
        stats_data = [
            ["Metric", "Value"],
            ["Total Entrances", entrances],
            ["Total Exits", exits],
            ["Registered Vehicles", registered],
            ["Access Granted", granted],
            ["Access Denied", denied]
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 1.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (1, 0), 12),
            ('BACKGROUND', (0, 1), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.25*inch))
        
        # Add access logs
        logs_style = styles['Heading2']
        logs_title = Paragraph("Recent Access Logs", logs_style)
        elements.append(logs_title)
        elements.append(Spacer(1, 0.15*inch))
        
        # Get logs based on report type
        if report_type == 'entrance':
            cursor.execute("SELECT * FROM access_logs WHERE feed_type='entrance' ORDER BY timestamp DESC LIMIT 50")
            logs_subtitle = Paragraph("Entrance Logs (Last 50 entries)", styles['Heading3'])
        elif report_type == 'exit':
            cursor.execute("SELECT * FROM access_logs WHERE feed_type='exit' ORDER BY timestamp DESC LIMIT 50")
            logs_subtitle = Paragraph("Exit Logs (Last 50 entries)", styles['Heading3'])
        elif report_type == 'registered':
            cursor.execute("""
                SELECT al.* FROM access_logs al
                JOIN avbs av ON al.license_plate = av.license_plate
                ORDER BY al.timestamp DESC LIMIT 50
            """)
            logs_subtitle = Paragraph("Registered Vehicle Logs (Last 50 entries)", styles['Heading3'])
        else:
            cursor.execute("SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT 50")
            logs_subtitle = Paragraph("All Access Logs (Last 50 entries)", styles['Heading3'])
        
        elements.append(logs_subtitle)
        elements.append(Spacer(1, 0.15*inch))
        
        logs = cursor.fetchall()
        
        if logs:
            # Create logs table
            logs_data = [["ID", "License Plate", "Type", "Action", "Timestamp"]]
            
            for log in logs:
                logs_data.append([
                    log['id'],
                    log['license_plate'],
                    log['feed_type'],
                    log['action'],
                    log['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(log['timestamp'], 'strftime') else str(log['timestamp'])
                ])
            
            logs_table = Table(logs_data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 1*inch, 2*inch])
            logs_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (4, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (4, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (4, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (4, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (4, 0), 12),
                ('BOTTOMPADDING', (0, 0), (4, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ]))
            elements.append(logs_table)
        else:
            no_logs = Paragraph("No logs found for the selected criteria.", styles['Normal'])
            elements.append(no_logs)
        
        # Add registered vehicles if report type is 'registered' or 'all'
        if report_type in ['registered', 'all']:
            elements.append(Spacer(1, 0.25*inch))
            vehicles_style = styles['Heading2']
            vehicles_title = Paragraph("Registered Vehicles", vehicles_style)
            elements.append(vehicles_title)
            elements.append(Spacer(1, 0.15*inch))
            
            cursor.execute("SELECT * FROM avbs ORDER BY registration_timestamp DESC LIMIT 50")
            vehicles = cursor.fetchall()
            
            if vehicles:
                # Create vehicles table
                vehicles_data = [["License Plate", "Owner Name", "Contact", "Registration Date"]]
                
                for vehicle in vehicles:
                    vehicles_data.append([
                        vehicle['license_plate'],
                        vehicle['owner_name'],
                        vehicle['owner_contact'] or 'N/A',
                        vehicle['registration_timestamp'].strftime('%Y-%m-%d') if hasattr(vehicle['registration_timestamp'], 'strftime') else str(vehicle['registration_timestamp'])
                    ])
                
                vehicles_table = Table(vehicles_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 1.5*inch])
                vehicles_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (3, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (3, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (3, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (3, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (3, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(vehicles_table)
            else:
                no_vehicles = Paragraph("No registered vehicles found.", styles['Normal'])
                elements.append(no_vehicles)
        
        # Build the PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error generating PDF report: {err}")
        return None
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn and conn.is_connected():
            conn.close()

@app.route('/generate_pdf/<report_type>')
def generate_pdf(report_type='all'):
    """Generate PDF report and send it to the client"""
    if report_type not in ['all', 'entrance', 'exit', 'registered']:
        report_type = 'all'
    
    pdf_buffer = generate_pdf_report(report_type)
    if pdf_buffer:
        return send_file(
            pdf_buffer,
            download_name=f'avbs_report_{report_type}_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
    else:
        return "Error generating PDF report", 500

# Add notification stream route
@app.route('/notifications/stream')
def stream_notifications():
    def event_stream():
        q = Queue()
        with notification_lock:
            notification_queues.add(q)
        try:
            while True:
                message = q.get()
                yield f"data: {message}\n\n"
        finally:
            with notification_lock:
                notification_queues.remove(q)

    return Response(stream_with_context(event_stream()),
                   mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache',
                           'Connection': 'keep-alive'})

# Add this route for manual testing
@app.route('/simulate_vehicle/<action>/<license_plate>', methods=['GET'])
def simulate_vehicle(action, license_plate):
    """
    Manually simulate vehicle entry/exit for testing
    action: 'enter' or 'exit'
    """
    if action == 'enter':
        feed_type = 'entrance'
    elif action == 'exit':
        feed_type = 'exit'
    else:
        return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
    
    # Simulate detection
    is_registered = check_license_plate(license_plate)
    if not is_registered:
        return jsonify({
            'status': 'error', 
            'message': f'License plate {license_plate} is not registered'
        }), 404
    
    # Update vehicle status
    allow_action, status_message = update_vehicle_status(license_plate, feed_type)
    
    # Control barrier based on status
    if allow_action:
        send_to_arduino("REGISTERED")
        message = f"Simulated {action} for {license_plate}: Barrier opened"
    else:
        send_to_arduino("UNREGISTERED")
        message = f"Simulated {action} for {license_plate}: {status_message}"
    
    # Debug current status
    debug_vehicle_status()
    
    return jsonify({
        'status': 'success',
        'message': message,
        'is_registered': is_registered,
        'allow_action': allow_action,
        'status_message': status_message,
        'vehicle_status': vehicle_status
    })

@app.route('/test_vehicle/<action>/<license_plate>', methods=['GET'])
def test_vehicle(action, license_plate):
    """
    Test vehicle entry/exit tracking
    action: 'enter' or 'exit'
    """
    if action not in ['enter', 'exit']:
        return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
    
    # Check if plate is registered
    is_registered = check_license_plate(license_plate)
    if not is_registered:
        return jsonify({
            'status': 'error', 
            'message': f'License plate {license_plate} is not registered'
        }), 404
    
    # Update vehicle status
    feed_type = 'entrance' if action == 'enter' else 'exit'
    allow_action, status_message = update_vehicle_status(license_plate, feed_type)
    
    # Control barrier based on status
    if allow_action:
        send_to_arduino("REGISTERED")
        message = f"Simulated {action} for {license_plate}: Barrier opened"
    else:
        send_to_arduino("UNREGISTERED")
        message = f"Simulated {action} for {license_plate}: {status_message}"
    
    # Debug current status
    debug_vehicle_status()
    
    return jsonify({
        'status': 'success' if allow_action else 'denied',
        'message': message,
        'is_registered': is_registered,
        'allow_action': allow_action,
        'status_message': status_message,
        'vehicle_status': vehicle_status
    })

@app.route('/test_arduino/<status>', methods=['GET'])
def test_arduino(status):
    """
    Test Arduino communication with a specific status
    status: 'REGISTERED' or 'UNREGISTERED'
    """
    if status not in ['REGISTERED', 'UNREGISTERED']:
        return jsonify({'status': 'error', 'message': 'Invalid status'}), 400
    
    result = send_to_arduino(status)
    
    if result:
        return jsonify({
            'status': 'success',
            'message': f'Sent {status} command to Arduino'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to send command to Arduino'
        }), 500

@app.route('/test_arduino')
def test_arduino_connection():
    """Test Arduino connection and servo control"""
    if send_to_arduino("TEST"):
        return "Arduino communication successful"
    else:
        return "Arduino communication failed"

@app.route('/manual_access', methods=['POST'])
def manual_access():
    try:
        data = request.get_json()
        license_plate = data['license_plate'].strip().upper()
        access_type = data['access_type']
        feed_type = data['feed_type']
        
        current_python_time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"Manual access request: {license_plate}, {access_type}, {feed_type}")
        
        if access_type == 'grant':
            # Log the manual access grant
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE
            )
            cursor = conn.cursor()
            
            # Log the manual access
            cursor.execute(
                "INSERT INTO access_logs (license_plate, feed_type, action, timestamp) VALUES (%s, %s, 'Manual-Grant', %s)",
                (license_plate, feed_type, current_python_time_str)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            # Open the barrier
            if feed_type == 'entrance':
                allow_entry, status_message = update_vehicle_status(license_plate, feed_type)
                if allow_entry:
                    success = control_servo(feed_type, 'open')
                    if not success:
                        return jsonify({'status': 'error', 'message': 'Failed to open barrier'})
                    # Schedule gate closing after 5 seconds
                    def close_gate():
                        time.sleep(5)
                        control_servo(feed_type, 'close')
                    threading.Thread(target=close_gate, daemon=True).start()
                    return jsonify({'status': 'success', 'message': 'Access granted'})
                else:
                    return jsonify({'status': 'error', 'message': status_message})
            else:  # exit
                success = control_servo(feed_type, 'open')
                if not success:
                    return jsonify({'status': 'error', 'message': 'Failed to open barrier'})
                # Schedule gate closing
                def close_gate():
                    time.sleep(5)
                    control_servo(feed_type, 'close')
                threading.Thread(target=close_gate, daemon=True).start()
                return jsonify({'status': 'success', 'message': 'Access granted'})
        
        elif access_type == 'deny':
            # Log the manual access denial
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE
            )
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO access_logs (license_plate, feed_type, action, timestamp) VALUES (%s, %s, 'Manual-Deny', %s)",
                (license_plate, feed_type, current_python_time_str)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            # Keep barrier closed
            return jsonify({'status': 'success', 'message': 'Access denied'})
        
        else:
            return jsonify({'status': 'error', 'message': 'Invalid access type'}), 400
            
    except Exception as e:
        logging.error(f"Error in manual access control: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def notify_unregistered_plate(plate):
    with notification_lock:
        for q in notification_queues:
            q.put(json.dumps({
                "type": "unregistered_plate",
                "plate": plate
            }))

def process_period_data(logs, now, period_type):
    """Process logs for a specific time period (day, week, month)"""
    result = {
        'traffic': {
            'labels': [],
            'entrances': [],
            'exits': []
        },
        'access': {
            'granted': 0,
            'denied': 0
        }
    }
    
    # Define time ranges based on period type
    if period_type == 'day':
        # Last 24 hours in hourly intervals
        intervals = 24
        labels = [f"{h:02d}:00" for h in range(24)]
        
        # Initialize counters
        entrance_counts = [0] * intervals
        exit_counts = [0] * intervals
        
        # Count logs by hour
        for log in logs:
            timestamp = log['timestamp']
            if not hasattr(timestamp, 'hour'):
                try:
                    timestamp = datetime.datetime.fromisoformat(str(timestamp))
                except:
                    continue
                
            # Only count logs from today
            if timestamp.date() == now.date():
                hour = timestamp.hour
                if log['feed_type'].lower() == 'entrance':
                    entrance_counts[hour] += 1
                elif log['feed_type'].lower() == 'exit':
                    exit_counts[hour] += 1
                
                action_lower = log['action'].lower()
                if action_lower in ['auto', 'grant', 'manual-grant']:
                    result['access']['granted'] += 1
                elif action_lower in ['deny', 'manual-deny']:
                    result['access']['denied'] += 1
                # Other actions, if any, are not counted
        
        result['traffic']['labels'] = labels
        result['traffic']['entrances'] = entrance_counts
        result['traffic']['exits'] = exit_counts
        
    elif period_type == 'week':
        # Last 7 days
        days = []
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Get the date for the past 7 days
        for i in range(6, -1, -1):
            days.append(now - datetime.timedelta(days=i))
        
        # Initialize counters
        entrance_counts = [0] * 7
        exit_counts = [0] * 7
        
        # Count logs by day
        for log in logs:
            timestamp = log['timestamp']
            if not hasattr(timestamp, 'date'):
                try:
                    timestamp = datetime.datetime.fromisoformat(str(timestamp))
                except:
                    continue
            
            # Check if log is within the last 7 days
            for i, day in enumerate(days):
                if timestamp.date() == day.date():
                    if log['feed_type'].lower() == 'entrance':
                        entrance_counts[i] += 1
                    elif log['feed_type'].lower() == 'exit':
                        exit_counts[i] += 1
                    
                    action_lower = log['action'].lower()
                    if action_lower in ['auto', 'grant', 'manual-grant']:
                        result['access']['granted'] += 1
                    elif action_lower in ['deny', 'manual-deny']:
                        result['access']['denied'] += 1
                    # Other actions, if any, are not counted
                    break
        
        # Use day names as labels
        result['traffic']['labels'] = [day_names[d.weekday()] for d in days]
        result['traffic']['entrances'] = entrance_counts
        result['traffic']['exits'] = exit_counts
        
    elif period_type == 'month':
        # Last 30 days in 6 intervals (5 days each)
        intervals = 6
        days_per_interval = 5
        
        # Create date ranges for labels
        date_ranges = []
        for i in range(intervals):
            start_day = now - datetime.timedelta(days=(intervals-i)*days_per_interval)
            end_day = start_day + datetime.timedelta(days=days_per_interval-1)
            date_ranges.append((start_day, end_day))
            
        # Create labels
        labels = [f"{start.strftime('%d/%m')}-{end.strftime('%d/%m')}" for start, end in date_ranges]
        
        # Initialize counters
        entrance_counts = [0] * intervals
        exit_counts = [0] * intervals
        
        # Count logs by interval
        for log in logs:
            timestamp = log['timestamp']
            if not hasattr(timestamp, 'date'):
                try:
                    timestamp = datetime.datetime.fromisoformat(str(timestamp))
                except:
                    continue
            
            # Check which interval this log belongs to
            for i, (start, end) in enumerate(date_ranges):
                if start.date() <= timestamp.date() <= end.date():
                    if log['feed_type'].lower() == 'entrance':
                        entrance_counts[i] += 1
                    elif log['feed_type'].lower() == 'exit':
                        exit_counts[i] += 1
                    
                    action_lower = log['action'].lower()
                    if action_lower in ['auto', 'grant', 'manual-grant']:
                        result['access']['granted'] += 1
                    elif action_lower in ['deny', 'manual-deny']:
                        result['access']['denied'] += 1
                    # Other actions, if any, are not counted
                    break
        
        result['traffic']['labels'] = labels
        result['traffic']['entrances'] = entrance_counts
        result['traffic']['exits'] = exit_counts
    
    return result




def send_to_arduino(status):
    """Send status command to Arduino"""
    if not check_arduino_connection():
        logging.warning("Arduino not connected, cannot send command")
        return False
    
    try:
        command = f"STATUS:{status}\n"
        arduino_serial.write(command.encode())
        arduino_serial.flush()  # Ensure data is sent immediately
        logging.info(f"Sent to Arduino: {command.strip()}")
        
        # Wait for and read the response from Arduino
        time.sleep(0.1)  # Give Arduino time to respond
        if arduino_serial.in_waiting:
            response = arduino_serial.readline().decode().strip()
            logging.info(f"Arduino response: {response}")
        
        return True
    except Exception as e:
        logging.error(f"Error sending command to Arduino: {e}")
        arduino_connected = False  # Mark as disconnected to trigger reconnection
        return False

def control_servo(feed_type, action):
    """Control the servo motor via Arduino
    feed_type: 'entrance' or 'exit'
    action: 'open' or 'close'
    """
    if not check_arduino_connection():
        logging.error("Arduino not connected. Cannot control servo.")
        return False
    
    try:
        # Add debug logging
        logging.info(f"Sending command to Arduino: {feed_type.upper()}_{action.upper()}")
        
        # Send command to Arduino
        command = f"{feed_type.upper()}_{action.upper()}\n"
        arduino_serial.write(command.encode())
        arduino_serial.flush()  # Ensure data is sent immediately
        
        # Wait for response with timeout
        start_time = time.time()
        while time.time() - start_time < 2:  # 2 second timeout
            if arduino_serial.in_waiting:
                response = arduino_serial.readline().decode().strip()
                logging.info(f"Arduino response: {response}")
                return "OK" in response
            time.sleep(0.1)
        
        logging.error("No response from Arduino")
        return False
    except Exception as e:
        logging.error(f"Error controlling servo: {e}")
        arduino_connected = False  # Mark as disconnected to trigger reconnection
        return False


def update_vehicle_status(license_plate, feed_type):
    """
    Track vehicle entry/exit status and determine if entry/exit should be allowed
    Returns: (allow_action, status_message)
    """
    global vehicle_status
    
    # Default to allowing action
    allow_action = True
    status_message = "Access granted"
    
    if feed_type == "entrance":
        # Check if vehicle is already inside
        if license_plate in vehicle_status and vehicle_status[license_plate] == "inside":
            allow_action = False
            status_message = "Vehicle already inside - must exit first"
            logging.warning(f"Denied entry to {license_plate} - already inside")
        else:
            # Only allow entry if vehicle is not inside or was previously outside
            if license_plate not in vehicle_status or vehicle_status[license_plate] == "outside":
                vehicle_status[license_plate] = "inside"
                logging.info(f"Vehicle {license_plate} marked as inside")
            else:
                allow_action = False
                status_message = "Invalid vehicle state for entry"
    
    elif feed_type == "exit":
        # Check if vehicle is inside (can only exit if inside)
        if license_plate not in vehicle_status or vehicle_status[license_plate] != "inside":
            allow_action = False
            status_message = "Vehicle not inside - must enter first"
            logging.warning(f"Denied exit to {license_plate} - not inside")
        else:
            # Mark vehicle as outside
            vehicle_status[license_plate] = "outside"
            logging.info(f"Vehicle {license_plate} marked as outside")
    
    # Debug the current vehicle status after update
    debug_vehicle_status()
    
    return allow_action, status_message

def debug_vehicle_status():
    """Print the current vehicle status for debugging"""
    logging.info("Current vehicle status:")
    logging.info(pprint.pformat(vehicle_status))

# Add initialization function for the app
# Use before_request with a first-request flag
_first_request = True

@app.before_request
def initialize_app():
    """Initialize application state before first request"""
    global _first_request, vehicle_status
    
    if _first_request:
        _first_request = False
        vehicle_status = {}  # Reset vehicle status
        logging.info("Vehicle status tracking initialized")
        debug_vehicle_status()

if __name__ == '__main__':
    try:
        # Start Arduino watchdog thread
        arduino_watchdog_thread = threading.Thread(target=arduino_watchdog, daemon=True)
        arduino_watchdog_thread.start()
        logging.info("Arduino watchdog thread started.")

        # Cameras, OCR, YOLO, Arduino connection are initialized globally.
        logging.info("Starting Flask application...")
        app.run(debug=True, host='0.0.0.0', use_reloader=False)

    except KeyboardInterrupt:
        logging.info("Application shutting down due to KeyboardInterrupt...")
    except Exception as e:
        logging.error(f"An error occurred while running the Flask application: {e}")
    finally:
        logging.info("Cleaning up resources...")
        # Ensure global cap_entrance and cap_exit are released
        if 'cap_entrance' in globals() and cap_entrance is not None:
            if cap_entrance.isOpened():
                cap_entrance.release()
                logging.info("Entrance camera released.")
        
        if 'cap_exit' in globals() and cap_exit is not None:
            # Only release cap_exit if it's a different object or if in dual camera mode
            is_single_mode = CAMERA_CONFIG.get('single_camera_mode', False)
            if (not is_single_mode) or (is_single_mode and cap_exit != cap_entrance):
                if cap_exit.isOpened():
                    cap_exit.release()
                    logging.info("Exit camera released.")
            elif is_single_mode and cap_exit == cap_entrance:
                logging.info("Exit camera is same as entrance, already handled by entrance release.")

        if 'arduino_serial' in globals() and arduino_serial is not None and arduino_serial.is_open:
            arduino_serial.close()
            logging.info("Arduino serial connection closed.")
            
        cv2.destroyAllWindows()
        logging.info("OpenCV windows destroyed.")
        logging.info("Application shutdown complete.")