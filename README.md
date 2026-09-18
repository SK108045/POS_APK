# POS_2 — Multi-Profile Business Point of Sale System

A powerful, lightweight Point of Sale (POS) system built with **Python 3**, **SQLite**, **HTML5**, **CSS3**, and **Vanilla JavaScript**. Designed to support multiple business types from a single unified codebase with zero heavy dependencies or external frameworks.

---

## 🏢 Supported Business Profiles

Switch instantly between 6 specialized business profiles via a 1-click setting or directly from the login screen:

1. **🛒 Retail / Mini-Mart**: Barcodes, stock inventory, supplier receiving, low-stock & reorder alerts.
2. **💊 Pharmacy**: Batch tracking, expiry countdown & alerts, drug strengths, manufacturer notes.
3. **🍽️ Restaurant / Café**: Table/Tab management, waiter assignment, KOT kitchen printing, dine-in vs takeaway.
4. **🔨 Hardware**: Decimal quantities (e.g. 2.5 kg, 3.2 m), extended units, quotations, wholesale & retail pricing tiers.
5. **👗 Boutique / Cosmetics**: Product variants (sizes, colors, shades) with variant-level stock pickers.
6. **🍸 Bar / Nightclub**: Open tabs, server assignment, nightclub ticket receipts, hospitality flow.

---

## ✨ Features

- **Multi-Profile Architecture**: Unified codebase supporting 6 distinct shop profiles with pre-seeded sample catalogs.
- **📷 Barcode Scanning & Adding**:
  - **POS Page**: Dedicated barcode scan button and direct search bar scanning. Instantly verifies and adds matching items to the cart with cash-register audio chimes.
  - **Products Page**: Barcode button to scan physical barcodes, auto-detecting existing items or auto-filling new product forms.
  - **Hardware & Camera Support**: Real-time camera video viewfinder (`BarcodeDetector` API) plus auto-detection for handheld USB/Bluetooth barcode guns.
- **🔍 1-Click Online Image Search**: Built-in product photo search automatically optimized and resized using Pillow (`static/uploads/`).
- **🎨 Modern Neutral Monochrome Theme**: Crisp black, white, and shades of grey with 1-click **Light/Dark Mode toggle** (`☀️ / 🌙`).
- **Comprehensive Back-Office**:
  - Inventory management & stock adjustment
  - Supplier purchases and accounts
  - Sales history, receipt reprinting & payment logs
  - Staff management with role-based access (Cashier, Manager, Admin)
  - Daily & monthly sales analytics dashboard

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone git@github.com:SK108045/POS_2.git
cd POS_2
```

### 2. Install Requirements
```bash
pip install pillow
```

### 3. Run the Application
```bash
python3 app.py
```

The application will start at:
```
http://127.0.0.1:3000
```

To run on a custom port:
```bash
POS_PORT=8080 python3 app.py
```

---

## 🔑 Default Credentials

| Portal | URL | Default Credentials |
| :--- | :--- | :--- |
| **POS Terminal** | `/login` or `/pos` | Staff PIN: `1234` |
| **Admin Portal** | `/admin` | Username: `admin`<br>Password: `admin123` |
| **Cashier Portal** | `/cashier` | Username: `admin`<br>Password: `admin123` |

---

## 📂 Project Structure

```text
.
├── app.py                # Main backend server & HTTP API routes
├── profiles.py           # Multi-profile definitions, capabilities & seeding
├── README.md             # Project documentation
├── start-pos.bat         # Windows quick-launch script
├── data/
│   └── pos.sqlite3       # SQLite database with pre-configured catalogs
└── static/
    ├── app.js            # Frontend POS application logic & barcode scanner
    ├── admin.js          # Admin dashboard & reporting logic
    ├── styles.css        # POS styling & light/dark monochrome theme
    ├── admin.css         # Admin portal styling
    └── uploads/          # Pillow-optimized product images
```

---

## 📄 License

MIT License. Open for personal and commercial point of sale deployments.


## Android APK architecture

The Android build is offline-first. The Capacitor WebView bundles the POS UI locally and stores operational data on-device using native SQLite (`@capacitor-community/sqlite`) with an IndexedDB fallback for browser testing. Core sales do not require a Python server or internet connection. Network-only integrations such as SMS, cloud sync, remote image search and future M-Pesa integrations should call a remote HTTPS backend so API secrets are never bundled in the APK.
