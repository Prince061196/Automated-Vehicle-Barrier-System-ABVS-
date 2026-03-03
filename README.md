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

(Add UI screenshots + Arduino setup photos here)
