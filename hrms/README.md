# 🏨 Hotel Room Management System (HRMS)

A complete full-stack hotel management application built with Python Flask + SQLite backend and a modern dark-themed HTML/CSS/JS frontend.

---

## 📁 Project Structure

```
hrms/
├── backend/
│   └── server.py          # Flask API server + SQLite DB
├── frontend/
│   └── index.html         # Complete SPA frontend
├── start.sh               # Linux/macOS startup script
├── start.bat              # Windows startup script
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip

### Installation & Run

**Linux / macOS:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```
Double-click start.bat
```

**Manual:**
```bash
cd backend
pip install flask pyjwt
python3 server.py
```

Then open **http://localhost:5000** in your browser.

---

## 🔑 Default Login

| Username | Password | Role  |
|----------|----------|-------|
| admin    | admin123 | Admin |

---

## 👥 User Roles

| Role          | Permissions                                      |
|---------------|--------------------------------------------------|
| Admin         | Full access — all modules + staff management     |
| Receptionist  | Bookings, rooms, guests, check-in/out            |
| Housekeeping  | View rooms, update cleaning/maintenance status   |
| Accountant    | View payments and financial reports              |

---

## ✨ Features

### 📊 Dashboard
- Live stats: rooms, guests, revenue, occupancy
- 7-day revenue bar chart
- Room status overview
- Quick action buttons

### 🚪 Room Management
- Add/edit/delete rooms
- Room types: Standard Single, Standard Double, Deluxe, Suite, Penthouse
- Status: Available / Occupied / Cleaning / Maintenance
- Visual room grid with color-coded status

### 📋 Booking Management
- Create, modify, cancel bookings
- Automatic room availability check
- Overlap detection (no double-booking)
- Auto total calculation (nights × price)
- Booking history per guest

### ✅ Check-In / Check-Out
- Dedicated check-in panel for confirmed bookings
- Check-out with auto room status → Cleaning
- Invoice generation on checkout

### 👥 Guest Management
- Full guest profiles with ID proof
- Stay history
- Quick guest creation during booking

### 💳 Payments & Billing
- Invoice generation per booking
- Payment methods: Cash, UPI, Card
- Payment status tracking
- Revenue reports

### 🧹 Housekeeping
- View rooms needing cleaning or maintenance
- One-click status updates
- Housekeeping summary stats

### 👔 Staff Management (Admin only)
- Create staff accounts
- Assign roles and permissions
- Enable/disable accounts

### 📈 Reports (Admin only)
- Monthly revenue trend
- Room type distribution
- Booking status overview
- Occupancy analytics

### 🗒️ System Logs (Admin only)
- Login history
- Booking changes
- Payment updates
- Staff actions

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | /api/auth/login | Authenticate user |
| GET    | /api/rooms | List all rooms |
| POST   | /api/rooms | Create room |
| PUT    | /api/rooms/:id | Update room |
| DELETE | /api/rooms/:id | Delete room |
| GET    | /api/guests | List guests |
| POST   | /api/guests | Create guest |
| GET    | /api/bookings | List bookings |
| POST   | /api/bookings | Create booking |
| POST   | /api/bookings/:id/checkin | Check in |
| POST   | /api/bookings/:id/checkout | Check out |
| POST   | /api/bookings/:id/cancel | Cancel booking |
| GET    | /api/payments | List payments |
| GET    | /api/housekeeping | Housekeeping rooms |
| PUT    | /api/housekeeping/:id | Update room status |
| GET    | /api/staff | List staff (admin) |
| POST   | /api/staff | Create staff (admin) |
| GET    | /api/reports/dashboard | Dashboard data |
| GET    | /api/reports/revenue | Revenue reports |
| GET    | /api/logs | System logs (admin) |

---

## 🏗️ Architecture

```
Browser (Frontend SPA)
        │
        │ REST API (JSON)
        ▼
Flask Application Server (Python)
        │
        │ SQL Queries
        ▼
SQLite Database (hrms.db)
```

### Tech Stack
- **Backend:** Python 3, Flask, SQLite (via built-in `sqlite3`)
- **Auth:** JWT tokens (PyJWT), SHA-256 password hashing
- **Frontend:** Vanilla HTML/CSS/JavaScript (no framework dependencies)
- **Database:** SQLite (auto-created on first run)

---

## 🔒 Security
- JWT-based authentication (12-hour expiry)
- Role-based access control (RBAC)
- SHA-256 password hashing
- Session-based auth tokens
- API endpoint protection

---

## 📦 Sample Data (Pre-loaded)
- 10 rooms across 3 floors
- 5 sample guests
- 1 admin account

---

## 🔧 Configuration

Edit `backend/server.py` to change:
- `SECRET_KEY` — JWT signing key (change in production!)
- `DB_PATH` — Database file location
- Port: change `port=5000` in the last line

---

## 🚀 Production Notes

For production deployment:
1. Change `SECRET_KEY` to a random secure string
2. Use PostgreSQL or MySQL instead of SQLite
3. Enable HTTPS
4. Use gunicorn: `gunicorn -w 4 server:app`
5. Set `debug=False`

---

## 📄 License
MIT — Free to use and modify.
