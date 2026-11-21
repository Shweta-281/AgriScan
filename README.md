# 🌱 AgriScan | Smart Farming & Crop Disease Detection

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Django](https://img.shields.io/badge/Django-5.0-green)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-orange)
![License](https://img.shields.io/badge/License-MIT-brightgreen)

**AgriScan** is a comprehensive, AI-powered agricultural companion designed to help farmers instantly detect crop diseases, receive verified expert agronomic advice, and monitor regional outbreak trends.

Built as a Major Project, this platform bridges the gap between advanced Machine Learning and practical, real-world farming.

---

## ✨ Key Features

*   📸 **Instant Disease Detection:** Upload a photo or use the built-in webcam to scan crop leaves.
*   🧠 **Explainable AI (Grad-CAM):** Generates a heatmap overlay on the leaf to show *exactly* where the AI detected the disease symptoms.
*   👨‍⚕️ **Expert Triage System:** Low-confidence AI scans are escalated to an Agronomist Dashboard. Experts can review the scan and send a verified, digital prescription (Organic & Chemical cures) back to the farmer.
*   🗺️ **Regional Outbreak Map:** Interactive map (Leaflet.js) with heatmaps and live feeds showing disease spread across different states.
*   ☁️ **Weather & Disease Risk Alerts:** Integrates local weather data to warn farmers about high-risk conditions for fungal outbreaks.
*   📊 **Yield & Revenue Forecasting:** Estimates crop yield and potential revenue based on the farm's health score and active crop cycles.
*   🌾 **Farmer Community Forum:** A social space for farmers to ask questions, share experiences, and help each other.
*   🌙 **Modern UI & Dark Mode:** A fully responsive, professional dashboard with native Dark Mode support.

---

## 🛠️ Tech Stack

**Backend:**
*   **Framework:** Django (Python)
*   **Database:** SQLite (Development)
*   **Authentication:** Django Auth with custom User Roles (Farmer, Agronomist, Admin)

**Machine Learning:**
*   **Model:** TensorFlow / Keras (Transfer Learning using MobileNetV2/ResNet)
*   **Libraries:** OpenCV, NumPy, Grad-CAM
*   **Dataset:** PlantVillage (38 classes of healthy and diseased crops)

**Frontend:**
*   HTML5, CSS3 (Custom variables for theming), JavaScript
*   Bootstrap Icons
*   Leaflet.js (Interactive Maps & Heatmaps)

---

## 🚀 Getting Started

Follow these steps to run the project locally on your machine.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/AgriScan.git
cd AgriScan
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Make sure your `requirements.txt` includes `django`, `tensorflow`, `opencv-python`, `pillow`, `reportlab`, and `requests`)*

### 4. Add the AI Model
Ensure your trained model file (`crop_disease_model.h5`) and `class_names.txt` are placed in the root directory of the project.

### 5. Apply Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create an Admin Account
```bash
python manage.py createsuperuser
```

### 7. Run the Server
```bash
python manage.py runserver
```
Open your browser and navigate to http://127.0.0.1:8000/.

---

## 📂 Project Structure

```text
AgriScan/
│
├── accounts/          # User authentication, roles, and profiles (Farmer, Expert)
├── detector/          # Core ML app (AI prediction, Grad-CAM, History)
├── community/         # Forum, Expert Consultation, Triage Inbox
├── analytics/         # Weather APIs, SMS alerts, Market Prices
├── static/            # CSS, JS, Images
├── media/             # Uploaded leaf images & generated heatmaps
├── templates/         # HTML files
├── manage.py
└── crop_disease_model.h5  # Trained AI Model
```

---

## 🧪 How to Demo the Project

1. **Register a Farmer Account** and go to the Dashboard.
2. **Upload an image** of a diseased leaf (or use the webcam). Watch the AI generate a diagnosis and Grad-CAM heatmap.
3. **Request an Expert Review** on the result page.
4. **Log out** and Register/Login as an **Agronomist**.
5. Go to the **Triage Inbox**, review the case, and write a digital prescription.
6. **Log back in as the Farmer** to see the verified prescription on your dashboard.
7. Check the **Outbreak Map** to see diseases spreading across India.

---

## 🤝 Contributing

This project was built as a Major Project for academic purposes. Feel free to fork the repository and enhance the AI model or UI.

---

## 📝 License

This project is licensed under the MIT License.