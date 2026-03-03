# 🚧 Automated Vehicle Barrier System (AVBS)

An AI + IoT powered gate automation system that detects vehicles, recognizes license plates, and physically controls a barrier using Arduino.

---

## 📌 Project Overview

The Automated Vehicle Barrier System (AVBS) is an intelligent access control solution that integrates Computer Vision, OCR, and IoT hardware to automate vehicle entry management in gated communities, institutions, and private facilities.

The system detects vehicles in real time, reads license plates, logs entry data into a database, and sends control signals to an Arduino microcontroller to operate a physical barrier.

---

## 🧠 Core Technologies Used

### 💻 Software
- Python
- Flask
- YOLO (Object Detection)
- PaddleOCR
- MySQL (XAMPP)
- HTML / CSS

### 🔌 Hardware / IoT
- Arduino (Microcontroller)
- Barrier control mechanism (servo/motor)
- Serial communication (Python ↔ Arduino)

---

## 🚀 Features

- Real-time vehicle detection using YOLO
- License plate recognition using PaddleOCR
- Live video streaming via Flask dashboard
- MySQL database logging with timestamps
- Automated barrier control using Arduino
- Serial communication between backend and microcontroller
- Intelligent decision-based gate opening

---

## 🏗 System Architecture

Camera → YOLO Detection → Plate Extraction → OCR Recognition →  
Database Logging → Access Decision →  
Serial Signal → Arduino → Barrier Motor Control

---

## ⚙ How It Works

1. Camera captures vehicle feed
2. YOLO detects vehicle and license plate
3. OCR extracts plate number
4. Plate is checked/logged in database
5. If access is granted:
   - Python sends signal via serial communication
   - Arduino receives signal
   - Barrier motor activates

---

## 🔮 Future Improvements

- Cloud-based remote monitoring
- Mobile app integration
- Multi-camera scalability
- RFID + AI hybrid access control
- Edge AI optimization

---

## 🎯 Impact

This project demonstrates integration of:

- Artificial Intelligence
- Backend Web Development
- Database Systems
- IoT Hardware Control
- Embedded Systems Communication

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
