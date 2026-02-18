# Nutrition Scanner – Barcode-Based Food Analysis Web App

A real-time barcode scanning web application that fetches and analyzes detailed nutritional information for food products using computer vision and external APIs.

This project integrates computer vision, REST APIs, and backend logic to deliver a complete end-to-end food nutrition analysis system.

---

## Features

- Real-time barcode scanning using device camera
- Barcode detection using OpenCV + Pyzbar
- Fetch product data from:
  - Open Food Facts API
  - Nutritionix API (fallback)
- Display:
  - Calories
  - Fat, Saturated Fat, Trans Fat
  - Sugar & Added Sugar
  - Sodium
  - Protein
- Nutri-Score grading system
- Processing Level (NOVA Classification)
- Additives detection
- Visual health indicators & daily intake percentages
- Product not found handling with contribution option

---

## System Architecture

User Camera → Frontend (JavaScript) → Flask Backend  
→ OpenCV Barcode Detection →  
→ External Nutrition APIs →  
→ Structured Nutritional Analysis →  
→ Dynamic HTML Rendering

---

## Tech Stack

### Backend
- Python
- Flask
- OpenCV
- Pyzbar
- Requests

### Frontend
- HTML5
- CSS3
- Vanilla JavaScript
- Canvas API

### APIs Used
- Open Food Facts API
- Nutritionix API

---

## Project Structure

---

## How It Works

### 1. Camera Initialization
- Uses browser `getUserMedia()` to access device camera
- Captures frames every 500ms

### 2️. Barcode Detection
- Frame sent to backend as Base64 image
- OpenCV decodes image
- Pyzbar extracts barcode data

### 3️. Product Lookup
- First queries Open Food Facts
- If not found → Nutritionix API fallback

### 4️. Nutritional Analysis
- Calculates:
  - Daily sugar percentage
  - Trans fat percentage
  - Health scoring
  - Processing classification
- Displays results with visual indicators

---

## Health Intelligence Logic

- Nutri-Score A–E classification
- NOVA processing level mapping
- Additive count detection
- Daily intake percentage calculations
- Custom nutrition scoring logic (fallback case)

---

## Installation & Setup

### 1️. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/nutrition-scanner.git
cd nutrition-scanner
```

### 2️. Create Virtual Environment
       
       python -m venv venv
       

### 3️. Install Dependencies

       pip install flask opencv-python pyzbar numpy requests

### 4️. Add Nutritionix API Keys (Optional)

Inside app.py:

      NUTRITIONIX_APP_ID = "your_app_id"
      NUTRITIONIX_API_KEY = "your_api_key"

### 5️. Run the Application
      python app.py


Open in browser:

http://127.0.0.1:5000/

