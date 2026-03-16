"""
Hotel Room Management System - Backend API
Flask + SQLite
"""
from flask import Flask, request, jsonify, send_from_directory
import sqlite3, hashlib, jwt, datetime, os, json
from functools import wraps

app = Flask(__name__, static_folder='../frontend', static_url_path='')

SECRET_KEY = "hrms_secret_key_2024"
DB_PATH = os.path.join(os.path.dirname(__file__), "hrms.db")

# ─── DB INIT ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        username  TEXT UNIQUE NOT NULL,
        password  TEXT NOT NULL,
        role      TEXT NOT NULL DEFAULT 'receptionist',
        status    INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS rooms (
        room_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT UNIQUE NOT NULL,
        room_type   TEXT NOT NULL,
        price       REAL NOT NULL,
        status      TEXT DEFAULT 'available',
        floor       INTEGER DEFAULT 1,
        description TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS guests (
        guest_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL,
        phone      TEXT NOT NULL,
        email      TEXT DEFAULT '',
        address    TEXT DEFAULT '',
        id_proof   TEXT DEFAULT '',
        id_number  TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS bookings (
        booking_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        guest_id    INTEGER NOT NULL,
        room_id     INTEGER NOT NULL,
        check_in    TEXT NOT NULL,
        check_out   TEXT NOT NULL,
        status      TEXT DEFAULT 'confirmed',
        total_amount REAL DEFAULT 0,
        notes       TEXT DEFAULT '',
        created_at  TEXT DEFAULT (datetime('now')),
        created_by  INTEGER,
        FOREIGN KEY (guest_id) REFERENCES guests(guest_id),
        FOREIGN KEY (room_id)  REFERENCES rooms(room_id)
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id     INTEGER NOT NULL,
        amount         REAL NOT NULL,
        payment_method TEXT DEFAULT 'cash',
        payment_status TEXT DEFAULT 'pending',
        paid_at        TEXT,
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
    );

    CREATE TABLE IF NOT EXISTS system_logs (
        log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER,
        action     TEXT NOT NULL,
        details    TEXT DEFAULT '',
        ip_address TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)

    # Default admin
    pw = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username,password,role) VALUES (?,?,?)",
              ("admin", pw, "admin"))

    # Sample rooms
    sample_rooms = [
        ("101", "Standard Single",  1500, "available", 1, "Cozy single room with city view"),
        ("102", "Standard Double",  2200, "available", 1, "Comfortable double room"),
        ("103", "Deluxe Double",    3500, "occupied",  1, "Spacious deluxe room with balcony"),
        ("201", "Suite",            6000, "available", 2, "Luxury suite with lounge area"),
        ("202", "Standard Single",  1500, "cleaning",  2, "Single room near elevator"),
        ("203", "Standard Double",  2200, "available", 2, "Double room with garden view"),
        ("301", "Penthouse Suite", 12000, "available", 3, "Top-floor penthouse with panoramic view"),
        ("302", "Deluxe Double",    3500, "maintenance",3,"Deluxe room - under maintenance"),
        ("303", "Standard Single",  1500, "available", 3, "Standard single room"),
        ("304", "Standard Double",  2200, "available", 3, "Double room with pool view"),
    ]
    for r in sample_rooms:
        c.execute("INSERT OR IGNORE INTO rooms (room_number,room_type,price,status,floor,description) VALUES (?,?,?,?,?,?)", r)

    # Sample guests
    sample_guests = [
        ("Rajesh Kumar",    "9876543210", "rajesh@email.com",  "Mumbai, Maharashtra", "Aadhaar", "1234-5678-9012"),
        ("Priya Sharma",    "8765432109", "priya@email.com",   "Delhi, NCR",          "Passport","P1234567"),
        ("Amit Singh",      "7654321098", "amit@email.com",    "Bangalore, Karnataka","Aadhaar", "9876-5432-1098"),
        ("Sunita Patel",    "6543210987", "sunita@email.com",  "Ahmedabad, Gujarat",  "PAN",     "ABCDE1234F"),
        ("Vikram Nair",     "9988776655", "vikram@email.com",  "Kochi, Kerala",       "Aadhaar", "4567-8901-2345"),
    ]
    for g in sample_guests:
        c.execute("INSERT OR IGNORE INTO guests (name,phone,email,address,id_proof,id_number) VALUES (?,?,?,?,?,?)", g)

    conn.commit()
    conn.close()

# ─── AUTH ────────────────────────────────────────────────────────────────────

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"error": "Missing token"}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.user.get("role") not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def log_action(user_id, action, details=""):
    conn = get_db()
    conn.execute("INSERT INTO system_logs (user_id,action,details,ip_address) VALUES (?,?,?,?)",
                 (user_id, action, details, request.remote_addr))
    conn.commit()
    conn.close()

# ─── CORS HEADERS ────────────────────────────────────────────────────────────

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

@app.route("/api/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return jsonify({}), 200

# ─── AUTH ROUTES ─────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username","").strip()
    password = data.get("password","").strip()
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=? AND password=? AND status=1",
                        (username, pw_hash)).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    token = jwt.encode({
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
    }, SECRET_KEY, algorithm="HS256")

    log_action(user["user_id"], "LOGIN", f"User {username} logged in")
    return jsonify({"token": token, "user": {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"]
    }})

@app.route("/api/auth/me", methods=["GET"])
@require_auth
def me():
    return jsonify(request.user)

# ─── ROOMS ───────────────────────────────────────────────────────────────────

@app.route("/api/rooms", methods=["GET"])
@require_auth
def get_rooms():
    status = request.args.get("status")
    conn = get_db()
    if status:
        rooms = conn.execute("SELECT * FROM rooms WHERE status=? ORDER BY room_number", (status,)).fetchall()
    else:
        rooms = conn.execute("SELECT * FROM rooms ORDER BY room_number").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rooms])

@app.route("/api/rooms/<int:room_id>", methods=["GET"])
@require_auth
def get_room(room_id):
    conn = get_db()
    room = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
    conn.close()
    if not room: return jsonify({"error": "Room not found"}), 404
    return jsonify(dict(room))

@app.route("/api/rooms", methods=["POST"])
@require_auth
@require_role("admin")
def create_room():
    data = request.get_json()
    conn = get_db()
    try:
        c = conn.execute(
            "INSERT INTO rooms (room_number,room_type,price,status,floor,description) VALUES (?,?,?,?,?,?)",
            (data["room_number"], data["room_type"], data["price"],
             data.get("status","available"), data.get("floor",1), data.get("description",""))
        )
        conn.commit()
        room_id = c.lastrowid
        log_action(request.user["user_id"], "CREATE_ROOM", f"Room {data['room_number']} created")
    except sqlite3.IntegrityError:
        return jsonify({"error": "Room number already exists"}), 400
    finally:
        conn.close()
    return jsonify({"room_id": room_id, "message": "Room created"}), 201

@app.route("/api/rooms/<int:room_id>", methods=["PUT"])
@require_auth
@require_role("admin","receptionist")
def update_room(room_id):
    data = request.get_json()
    conn = get_db()
    fields = []
    values = []
    for f in ["room_type","price","status","floor","description","room_number"]:
        if f in data:
            fields.append(f"{f}=?")
            values.append(data[f])
    if not fields:
        return jsonify({"error": "Nothing to update"}), 400
    values.append(room_id)
    conn.execute(f"UPDATE rooms SET {', '.join(fields)} WHERE room_id=?", values)
    conn.commit()
    conn.close()
    log_action(request.user["user_id"], "UPDATE_ROOM", f"Room {room_id} updated")
    return jsonify({"message": "Room updated"})

@app.route("/api/rooms/<int:room_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def delete_room(room_id):
    conn = get_db()
    conn.execute("DELETE FROM rooms WHERE room_id=?", (room_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Room deleted"})

# ─── GUESTS ──────────────────────────────────────────────────────────────────

@app.route("/api/guests", methods=["GET"])
@require_auth
def get_guests():
    search = request.args.get("search","")
    conn = get_db()
    if search:
        guests = conn.execute(
            "SELECT * FROM guests WHERE name LIKE ? OR phone LIKE ? ORDER BY created_at DESC",
            (f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        guests = conn.execute("SELECT * FROM guests ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(g) for g in guests])

@app.route("/api/guests/<int:guest_id>", methods=["GET"])
@require_auth
def get_guest(guest_id):
    conn = get_db()
    guest = conn.execute("SELECT * FROM guests WHERE guest_id=?", (guest_id,)).fetchone()
    bookings = conn.execute("""
        SELECT b.*, r.room_number, r.room_type FROM bookings b
        JOIN rooms r ON b.room_id = r.room_id
        WHERE b.guest_id=? ORDER BY b.created_at DESC
    """, (guest_id,)).fetchall()
    conn.close()
    if not guest: return jsonify({"error": "Guest not found"}), 404
    return jsonify({"guest": dict(guest), "bookings": [dict(b) for b in bookings]})

@app.route("/api/guests", methods=["POST"])
@require_auth
def create_guest():
    data = request.get_json()
    conn = get_db()
    c = conn.execute(
        "INSERT INTO guests (name,phone,email,address,id_proof,id_number) VALUES (?,?,?,?,?,?)",
        (data["name"], data["phone"], data.get("email",""),
         data.get("address",""), data.get("id_proof",""), data.get("id_number",""))
    )
    conn.commit()
    guest_id = c.lastrowid
    conn.close()
    return jsonify({"guest_id": guest_id, "message": "Guest created"}), 201

@app.route("/api/guests/<int:guest_id>", methods=["PUT"])
@require_auth
def update_guest(guest_id):
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "UPDATE guests SET name=?,phone=?,email=?,address=?,id_proof=?,id_number=? WHERE guest_id=?",
        (data["name"], data["phone"], data.get("email",""),
         data.get("address",""), data.get("id_proof",""), data.get("id_number",""), guest_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Guest updated"})

# ─── BOOKINGS ────────────────────────────────────────────────────────────────

@app.route("/api/bookings", methods=["GET"])
@require_auth
def get_bookings():
    status = request.args.get("status")
    date   = request.args.get("date")
    conn = get_db()
    query = """
        SELECT b.*, g.name as guest_name, g.phone as guest_phone,
               r.room_number, r.room_type, r.price as room_price
        FROM bookings b
        JOIN guests g ON b.guest_id = g.guest_id
        JOIN rooms  r ON b.room_id  = r.room_id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND b.status=?"; params.append(status)
    if date:
        query += " AND (b.check_in <= ? AND b.check_out >= ?)"; params += [date, date]
    query += " ORDER BY b.created_at DESC"
    bookings = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(b) for b in bookings])

@app.route("/api/bookings/<int:booking_id>", methods=["GET"])
@require_auth
def get_booking(booking_id):
    conn = get_db()
    booking = conn.execute("""
        SELECT b.*, g.name as guest_name, g.phone as guest_phone, g.email as guest_email,
               g.address as guest_address, g.id_proof, g.id_number,
               r.room_number, r.room_type, r.price as room_price
        FROM bookings b
        JOIN guests g ON b.guest_id = g.guest_id
        JOIN rooms  r ON b.room_id  = r.room_id
        WHERE b.booking_id=?
    """, (booking_id,)).fetchone()
    payment = conn.execute("SELECT * FROM payments WHERE booking_id=?", (booking_id,)).fetchone()
    conn.close()
    if not booking: return jsonify({"error": "Booking not found"}), 404
    return jsonify({"booking": dict(booking), "payment": dict(payment) if payment else None})

@app.route("/api/bookings", methods=["POST"])
@require_auth
def create_booking():
    data = request.get_json()
    conn = get_db()

    # Check room availability
    room = conn.execute("SELECT * FROM rooms WHERE room_id=?", (data["room_id"],)).fetchone()
    if not room:
        conn.close()
        return jsonify({"error": "Room not found"}), 404
    if room["status"] not in ("available",):
        conn.close()
        return jsonify({"error": f"Room is {room['status']}"}), 400

    # Check for overlapping bookings
    overlap = conn.execute("""
        SELECT 1 FROM bookings
        WHERE room_id=? AND status IN ('confirmed','checked_in')
        AND NOT (check_out <= ? OR check_in >= ?)
    """, (data["room_id"], data["check_in"], data["check_out"])).fetchone()
    if overlap:
        conn.close()
        return jsonify({"error": "Room already booked for these dates"}), 400

    # Calculate total
    ci = datetime.date.fromisoformat(data["check_in"])
    co = datetime.date.fromisoformat(data["check_out"])
    nights = (co - ci).days
    total = nights * room["price"]

    c = conn.execute(
        "INSERT INTO bookings (guest_id,room_id,check_in,check_out,status,total_amount,notes,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (data["guest_id"], data["room_id"], data["check_in"], data["check_out"],
         "confirmed", total, data.get("notes",""), request.user["user_id"])
    )
    booking_id = c.lastrowid

    # Update room status
    conn.execute("UPDATE rooms SET status='occupied' WHERE room_id=?", (data["room_id"],))

    # Create payment record
    conn.execute(
        "INSERT INTO payments (booking_id,amount,payment_method,payment_status) VALUES (?,?,?,?)",
        (booking_id, total, data.get("payment_method","cash"), "pending")
    )

    conn.commit()
    conn.close()
    log_action(request.user["user_id"], "CREATE_BOOKING", f"Booking {booking_id} created")
    return jsonify({"booking_id": booking_id, "total_amount": total, "nights": nights}), 201

@app.route("/api/bookings/<int:booking_id>/checkin", methods=["POST"])
@require_auth
def checkin(booking_id):
    conn = get_db()
    booking = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
    if not booking: return jsonify({"error": "Booking not found"}), 404
    if booking["status"] != "confirmed":
        return jsonify({"error": "Booking is not in confirmed state"}), 400
    conn.execute("UPDATE bookings SET status='checked_in' WHERE booking_id=?", (booking_id,))
    conn.execute("UPDATE rooms SET status='occupied' WHERE room_id=?", (booking["room_id"],))
    conn.commit()
    conn.close()
    log_action(request.user["user_id"], "CHECK_IN", f"Booking {booking_id} checked in")
    return jsonify({"message": "Checked in successfully"})

@app.route("/api/bookings/<int:booking_id>/checkout", methods=["POST"])
@require_auth
def checkout(booking_id):
    conn = get_db()
    booking = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
    if not booking: return jsonify({"error": "Booking not found"}), 404
    if booking["status"] != "checked_in":
        return jsonify({"error": "Guest is not checked in"}), 400
    conn.execute("UPDATE bookings SET status='checked_out' WHERE booking_id=?", (booking_id,))
    conn.execute("UPDATE rooms SET status='cleaning' WHERE room_id=?", (booking["room_id"],))
    conn.execute("UPDATE payments SET payment_status='paid', paid_at=datetime('now') WHERE booking_id=?", (booking_id,))
    conn.commit()
    conn.close()
    log_action(request.user["user_id"], "CHECK_OUT", f"Booking {booking_id} checked out")
    return jsonify({"message": "Checked out successfully"})

@app.route("/api/bookings/<int:booking_id>/cancel", methods=["POST"])
@require_auth
def cancel_booking(booking_id):
    conn = get_db()
    booking = conn.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
    if not booking: return jsonify({"error": "Booking not found"}), 404
    conn.execute("UPDATE bookings SET status='cancelled' WHERE booking_id=?", (booking_id,))
    conn.execute("UPDATE rooms SET status='available' WHERE room_id=?", (booking["room_id"],))
    conn.commit()
    conn.close()
    return jsonify({"message": "Booking cancelled"})

# ─── PAYMENTS ────────────────────────────────────────────────────────────────

@app.route("/api/payments", methods=["GET"])
@require_auth
def get_payments():
    conn = get_db()
    payments = conn.execute("""
        SELECT p.*, b.check_in, b.check_out, g.name as guest_name, r.room_number
        FROM payments p
        JOIN bookings b ON p.booking_id = b.booking_id
        JOIN guests g ON b.guest_id = g.guest_id
        JOIN rooms r ON b.room_id = r.room_id
        ORDER BY p.payment_id DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(p) for p in payments])

# ─── STAFF / USERS ───────────────────────────────────────────────────────────

@app.route("/api/staff", methods=["GET"])
@require_auth
@require_role("admin")
def get_staff():
    conn = get_db()
    staff = conn.execute("SELECT user_id,username,role,status,created_at FROM users ORDER BY user_id").fetchall()
    conn.close()
    return jsonify([dict(s) for s in staff])

@app.route("/api/staff", methods=["POST"])
@require_auth
@require_role("admin")
def create_staff():
    data = request.get_json()
    pw = hashlib.sha256(data["password"].encode()).hexdigest()
    conn = get_db()
    try:
        c = conn.execute(
            "INSERT INTO users (username,password,role) VALUES (?,?,?)",
            (data["username"], pw, data.get("role","receptionist"))
        )
        conn.commit()
        uid = c.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400
    finally:
        conn.close()
    return jsonify({"user_id": uid, "message": "Staff created"}), 201

@app.route("/api/staff/<int:user_id>", methods=["PUT"])
@require_auth
@require_role("admin")
def update_staff(user_id):
    data = request.get_json()
    conn = get_db()
    if "password" in data and data["password"]:
        pw = hashlib.sha256(data["password"].encode()).hexdigest()
        conn.execute("UPDATE users SET role=?,status=?,password=? WHERE user_id=?",
                     (data.get("role","receptionist"), data.get("status",1), pw, user_id))
    else:
        conn.execute("UPDATE users SET role=?,status=? WHERE user_id=?",
                     (data.get("role","receptionist"), data.get("status",1), user_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Staff updated"})

# ─── HOUSEKEEPING ────────────────────────────────────────────────────────────

@app.route("/api/housekeeping", methods=["GET"])
@require_auth
def get_housekeeping():
    conn = get_db()
    rooms = conn.execute(
        "SELECT * FROM rooms WHERE status IN ('cleaning','maintenance','available') ORDER BY room_number"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rooms])

@app.route("/api/housekeeping/<int:room_id>", methods=["PUT"])
@require_auth
@require_role("admin","housekeeping","receptionist")
def update_housekeeping(room_id):
    data = request.get_json()
    status = data.get("status")
    if status not in ("available","cleaning","maintenance"):
        return jsonify({"error": "Invalid status"}), 400
    conn = get_db()
    conn.execute("UPDATE rooms SET status=? WHERE room_id=?", (status, room_id))
    conn.commit()
    conn.close()
    log_action(request.user["user_id"], "HOUSEKEEPING", f"Room {room_id} status → {status}")
    return jsonify({"message": "Room status updated"})

# ─── REPORTS / DASHBOARD ─────────────────────────────────────────────────────

@app.route("/api/reports/dashboard", methods=["GET"])
@require_auth
def dashboard():
    conn = get_db()
    today = datetime.date.today().isoformat()
    month_start = datetime.date.today().replace(day=1).isoformat()

    total_rooms      = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    available_rooms  = conn.execute("SELECT COUNT(*) FROM rooms WHERE status='available'").fetchone()[0]
    occupied_rooms   = conn.execute("SELECT COUNT(*) FROM rooms WHERE status='occupied'").fetchone()[0]
    cleaning_rooms   = conn.execute("SELECT COUNT(*) FROM rooms WHERE status='cleaning'").fetchone()[0]
    maintenance_rooms= conn.execute("SELECT COUNT(*) FROM rooms WHERE status='maintenance'").fetchone()[0]

    total_bookings   = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    today_checkins   = conn.execute("SELECT COUNT(*) FROM bookings WHERE check_in=? AND status IN ('confirmed','checked_in')", (today,)).fetchone()[0]
    today_checkouts  = conn.execute("SELECT COUNT(*) FROM bookings WHERE check_out=? AND status='checked_in'", (today,)).fetchone()[0]
    active_guests    = conn.execute("SELECT COUNT(*) FROM bookings WHERE status='checked_in'").fetchone()[0]

    daily_revenue    = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_status='paid' AND date(paid_at)=?", (today,)).fetchone()[0]
    monthly_revenue  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_status='paid' AND date(paid_at)>=?", (month_start,)).fetchone()[0]

    # Last 7 days revenue
    revenue_7d = []
    for i in range(6, -1, -1):
        d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        rev = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_status='paid' AND date(paid_at)=?", (d,)).fetchone()[0]
        revenue_7d.append({"date": d, "revenue": rev})

    # Booking status distribution
    booking_dist = conn.execute("""
        SELECT status, COUNT(*) as count FROM bookings GROUP BY status
    """).fetchall()

    # Room type distribution
    room_types = conn.execute("""
        SELECT room_type, COUNT(*) as total,
               SUM(CASE WHEN status='available' THEN 1 ELSE 0 END) as available
        FROM rooms GROUP BY room_type
    """).fetchall()

    conn.close()
    return jsonify({
        "rooms": {
            "total": total_rooms, "available": available_rooms,
            "occupied": occupied_rooms, "cleaning": cleaning_rooms,
            "maintenance": maintenance_rooms
        },
        "bookings": {
            "total": total_bookings, "today_checkins": today_checkins,
            "today_checkouts": today_checkouts, "active_guests": active_guests
        },
        "revenue": {
            "today": daily_revenue, "monthly": monthly_revenue,
            "last_7_days": revenue_7d
        },
        "occupancy_rate": round((occupied_rooms / total_rooms * 100) if total_rooms else 0, 1),
        "booking_distribution": [dict(b) for b in booking_dist],
        "room_types": [dict(r) for r in room_types]
    })

@app.route("/api/reports/revenue", methods=["GET"])
@require_auth
def revenue_report():
    period = request.args.get("period","monthly")
    conn = get_db()
    if period == "daily":
        data = conn.execute("""
            SELECT date(paid_at) as period, SUM(amount) as revenue, COUNT(*) as transactions
            FROM payments WHERE payment_status='paid'
            GROUP BY date(paid_at) ORDER BY period DESC LIMIT 30
        """).fetchall()
    else:
        data = conn.execute("""
            SELECT strftime('%Y-%m', paid_at) as period, SUM(amount) as revenue, COUNT(*) as transactions
            FROM payments WHERE payment_status='paid'
            GROUP BY strftime('%Y-%m', paid_at) ORDER BY period DESC LIMIT 12
        """).fetchall()
    conn.close()
    return jsonify([dict(d) for d in data])

@app.route("/api/logs", methods=["GET"])
@require_auth
@require_role("admin")
def get_logs():
    conn = get_db()
    logs = conn.execute("""
        SELECT l.*, u.username FROM system_logs l
        LEFT JOIN users u ON l.user_id = u.user_id
        ORDER BY l.created_at DESC LIMIT 200
    """).fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])

# ─── FRONTEND SERVE ──────────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("  HRMS Backend started on http://localhost:5000")
    print("  Default login: admin / admin123")
    print("=" * 50)
    app.run(debug=True, port=5000, host="0.0.0.0")
