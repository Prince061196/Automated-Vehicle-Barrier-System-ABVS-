# 🚧 Automated Vehicle Barrier System (AI + IoT)

An AI-powered access control system that combines Computer Vision and IoT to automate vehicle entry using real-time license plate recognition and Arduino-based barrier control.

---
## 🚀 Why This Project Matters

This system demonstrates the integration of:

- Real-time object detection
- Optical character recognition
- Backend server architecture
- Database management
- Embedded systems communication
- Physical hardware automation
  
---

## 📌 Overview

The Automated Vehicle Barrier System (AVBS) is an intelligent infrastructure solution designed to automate vehicle access in gated environments. 

The system integrates:
- YOLO-based vehicle detection
- OCR-based license plate recognition
- Flask backend server
- MySQL database logging
- Arduino-controlled physical barrier

This project demonstrates full-stack AI integration with embedded systems.

---

## 🧠 Key Capabilities

✔ Real-time vehicle detection  
✔ License plate extraction and recognition  
✔ Entry logging with timestamps  
✔ Decision-based barrier activation  
✔ Serial communication with Arduino  
✔ Live dashboard monitoring  

---

## 🔌 IoT Integration

The backend communicates with an Arduino microcontroller via serial communication.

Workflow:
1. License plate is detected and processed
2. Access decision is made
3. Python sends control signal via serial port
4. Arduino activates servo/motor to lift barrier

---

## 🏗 System Architecture

Camera  
↓  
YOLO Detection  
↓  
Plate Cropping  
↓  
PaddleOCR Recognition  
↓  
MySQL Logging  
↓  
Access Decision  
↓  
Serial Signal  
↓  
Arduino  
↓  
Barrier Motor  

---

## 🛠 Tech Stack

### Software
- Python
- Flask
- YOLO
- PaddleOCR
- MySQL (XAMPP)

### Hardware
- Arduino
- Servo / Motor Driver
- Serial Communication

---

## 📂 Project Structure
---

## ⚙ Installation

1. Clone the repository
2. Install dependencies:
   pip install -r requirements.txt
3. Start MySQL via XAMPP
4. Configure database credentials
5. Connect Arduino via USB
6. Run:
   python app.py

---

## 🔮 Future Improvements

- Cloud deployment
- Mobile app monitoring
- Multi-camera support
- RFID + AI hybrid authentication
- Edge AI performance optimization

---

## 🎯 Engineering Focus

This project demonstrates:
- AI model integration
- Backend API development
- Real-time system architecture
- Embedded systems communication
- IoT automation

---
## 🧠 Engineering Challenges Solved

- Handling real-time video processing efficiently
- Optimizing OCR performance for accuracy
- Managing serial communication reliability
- Designing clean backend architecture
---

## 📷 Screenshots & Hardware Setup


<img width="1600" height="758" alt="Screenshot (13)" src="https://github.com/user-attachments/assets/1ac8b814-9fd8-4e87-9464-7298141e7e15" />
<img width="1600" height="763" alt="Screenshot (24)" src="https://github.com/user-attachments/assets/0dd4cc7a-f685-40f7-b933-5b4e433922af" />
<img width="1600" height="763" alt="Screenshot (22)" src="https://github.com/user-attachments/assets/5233aac8-28c4-4ee8-9dbb-459606fada74" />
<img width="1600" height="763" alt="Screenshot (20)" src="https://github.com/user-attachments/assets/ec049314-887e-4d6a-aabd-542038a75740" />
<img width="1600" height="763" alt="Screenshot (19)" src="https://github.com/user-attachments/assets/5ef8021f-ebdb-427a-9777-7140f02a8d72" />
<img width="1600" height="754" alt="Screenshot (16)" src="https://github.com/user-attachments/assets/90f1e0fc-4246-40df-8545-d00f6b5570a5" />
<img width="1600" height="754" alt="Screenshot (15)" src="https://github.com/user-attachments/assets/cde931be-d1eb-4636-b9f2-37987f197ee4" />
![IMG_20250625_121536](https://github.com/user-attachments/assets/2119ea6b-24d3-4950-b0fa-1285b36f2997)
