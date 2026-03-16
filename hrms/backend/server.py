"""
Hotel Room Management System - Backend API
Flask + SQLite (local) / PostgreSQL (Supabase cloud)
"""
from flask import Flask, request, jsonify, send_from_directory
import hashlib, jwt, datetime, os
from functools import wraps

app = Flask(__name__, static_folder='../frontend', static_url_path='')

SECRET_KEY = "hrms_secret_key_2024"

# ════════════════════════════════════════════════════════════════════════════
#   PASTE YOUR SUPABASE DATABASE URL ON LINE 19 BELOW
#   Get it: supabase.com → Project → Settings → Database → URI tab → Copy
#   Example: "postgresql://postgres:MyPass@db.abcxyz.supabase.co:5432/postgres"
#   Leave as None to run locally with SQLite
# ════════════════════════════════════════════════════════════════════════════

DATABASE_URL = postgresql://postgres:[chirugowda@009]@db.yjuznwcosfwjnizwtirk.supabase.co:5432/postgres
# ─── AUTO DETECT: SQLite (local) vs PostgreSQL (Supabase) ───────────────────

_PG_URL  = DATABASE_URL or os.environ.get("DATABASE_URL", "")
_USE_PG  = bool(_PG_URL)

if _USE_PG:
    try:
        import psycopg2, psycopg2.extras
        print("✓ PostgreSQL / Supabase mode")
    except ImportError:
        print("ERROR: Run → pip install psycopg2-binary")
        _USE_PG = False

if not _USE_PG:
    import sqlite3
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hrms.db")
    print("✓ SQLite local mode")

# ─── UNIFIED DB WRAPPER ──────────────────────────────────────────────────────

class DB:
    """Single class that works with both SQLite and PostgreSQL."""

    def __init__(self):
        if _USE_PG:
            self._conn = psycopg2.connect(_PG_URL)
            self._pg = True
        else:
            self._conn = sqlite3.connect(DB_PATH)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._pg = False

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(self._fix(sql), params)
        return cur

    def executescript(self, sql):
        if self._pg:
            for stmt in sql.split(';'):
                s = self._fix(stmt.strip())
                if s:
                    try:
                        self._conn.cursor().execute(s)
                    except Exception:
                        self._conn.rollback()
        else:
            self._conn.executescript(sql)

    def fetchall(self, sql, params=()):
        cur = self.execute(sql, params)
        if self._pg:
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        return [dict(r) for r in cur.fetchall()]

    def fetchone(self, sql, params=()):
        cur = self.execute(sql, params)
        if self._pg:
            row = cur.fetchone()
            if row is None: return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
        row = cur.fetchone()
        return dict(row) if row else None

    def lastrowid(self, cur):
        if self._pg:
            c2 = self._conn.cursor(); c2.execute("SELECT lastval()")
            return c2.fetchone()[0]
        return cur.lastrowid

    def commit(self):  self._conn.commit()
    def close(self):   self._conn.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()

    def _fix(self, sql):
        """Translate SQLite syntax to PostgreSQL when needed."""
        if not self._pg: return sql
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        sql = sql.replace("AUTOINCREMENT", "")
        sql = sql.replace("datetime('now')", "NOW()")
        sql = sql.replace("date(paid_at)", "DATE(paid_at)")
        sql = sql.replace("strftime('%Y-%m', paid_at)", "TO_CHAR(paid_at, 'YYYY-MM')")
        sql = sql.replace("INSERT OR IGNORE", "INSERT")
        sql = sql.replace("PRAGMA foreign_keys = ON", "SET client_encoding='UTF8'")
        return ''.join('%s' if c == '?' else c for c in sql)


def get_db(): return DB()

# ─── DATABASE INIT ───────────────────────────────────────────────────────────

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        username   TEXT UNIQUE NOT NULL,
        password   TEXT NOT NULL,
        role       TEXT NOT NULL DEFAULT 'receptionist',
        status     INTEGER DEFAULT 1,
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
        booking_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        guest_id     INTEGER NOT NULL,
        room_id      INTEGER NOT NULL,
        check_in     TEXT NOT NULL,
        check_out    TEXT NOT NULL,
        status       TEXT DEFAULT 'confirmed',
        total_amount REAL DEFAULT 0,
        notes        TEXT DEFAULT '',
        created_at   TEXT DEFAULT (datetime('now')),
        created_by   INTEGER
    );
    CREATE TABLE IF NOT EXISTS payments (
        payment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id     INTEGER NOT NULL,
        amount         REAL NOT NULL,
        payment_method TEXT DEFAULT 'cash',
        payment_status TEXT DEFAULT 'pending',
        paid_at        TEXT
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
    conn.commit()

    # Default admin
    pw = hashlib.sha256("admin123".encode()).hexdigest()
    try:
        conn.execute("INSERT OR IGNORE INTO users (username,password,role) VALUES (?,?,?)", ("admin", pw, "admin"))
        conn.commit()
    except Exception: conn.commit()

    # Sample rooms
    for r in [
        ("101","Standard Single",1500,"available",1,"Cozy single room with city view"),
        ("102","Standard Double",2200,"available",1,"Comfortable double room"),
        ("103","Deluxe Double",3500,"occupied",1,"Spacious deluxe room with balcony"),
        ("201","Suite",6000,"available",2,"Luxury suite with lounge area"),
        ("202","Standard Single",1500,"cleaning",2,"Single room near elevator"),
        ("203","Standard Double",2200,"available",2,"Double room with garden view"),
        ("301","Penthouse Suite",12000,"available",3,"Top-floor penthouse with panoramic view"),
        ("302","Deluxe Double",3500,"maintenance",3,"Deluxe room - under maintenance"),
        ("303","Standard Single",1500,"available",3,"Standard single room"),
        ("304","Standard Double",2200,"available",3,"Double room with pool view"),
    ]:
        try:
            conn.execute("INSERT OR IGNORE INTO rooms (room_number,room_type,price,status,floor,description) VALUES (?,?,?,?,?,?)", r)
            conn.commit()
        except Exception: conn.commit()

    # Sample guests
    for g in [
        ("Rajesh Kumar","9876543210","rajesh@email.com","Mumbai, Maharashtra","Aadhaar","1234-5678-9012"),
        ("Priya Sharma","8765432109","priya@email.com","Delhi, NCR","Passport","P1234567"),
        ("Amit Singh","7654321098","amit@email.com","Bangalore, Karnataka","Aadhaar","9876-5432-1098"),
        ("Sunita Patel","6543210987","sunita@email.com","Ahmedabad, Gujarat","PAN","ABCDE1234F"),
        ("Vikram Nair","9988776655","vikram@email.com","Kochi, Kerala","Aadhaar","4567-8901-2345"),
    ]:
        try:
            conn.execute("INSERT OR IGNORE INTO guests (name,phone,email,address,id_proof,id_number) VALUES (?,?,?,?,?,?)", g)
            conn.commit()
        except Exception: conn.commit()

    conn.close()

# ─── AUTH ────────────────────────────────────────────────────────────────────

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization","").replace("Bearer ","")
        if not token: return jsonify({"error":"Missing token"}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user = payload
        except jwt.ExpiredSignatureError: return jsonify({"error":"Token expired"}), 401
        except jwt.InvalidTokenError:     return jsonify({"error":"Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.user.get("role") not in roles:
                return jsonify({"error":"Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def log_action(user_id, action, details=""):
    try:
        conn = get_db()
        conn.execute("INSERT INTO system_logs (user_id,action,details,ip_address) VALUES (?,?,?,?)",
                     (user_id, action, details, request.remote_addr))
        conn.commit(); conn.close()
    except Exception: pass

# ─── CORS ────────────────────────────────────────────────────────────────────

@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    r.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return r

@app.route("/api/<path:path>", methods=["OPTIONS"])
def options_handler(path): return jsonify({}), 200

# ─── AUTH ROUTES ─────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    u, p = data.get("username","").strip(), data.get("password","").strip()
    if not u or not p: return jsonify({"error":"Username and password required"}), 400
    pw_hash = hashlib.sha256(p.encode()).hexdigest()
    conn = get_db()
    user = conn.fetchone("SELECT * FROM users WHERE username=? AND password=? AND status=1", (u, pw_hash))
    conn.close()
    if not user: return jsonify({"error":"Invalid credentials"}), 401
    token = jwt.encode({
        "user_id": user["user_id"], "username": user["username"], "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
    }, SECRET_KEY, algorithm="HS256")
    log_action(user["user_id"], "LOGIN", f"User {u} logged in")
    return jsonify({"token": token, "user": {"user_id": user["user_id"], "username": user["username"], "role": user["role"]}})

@app.route("/api/auth/me", methods=["GET"])
@require_auth
def me(): return jsonify(request.user)

# ─── ROOMS ───────────────────────────────────────────────────────────────────

@app.route("/api/rooms", methods=["GET"])
@require_auth
def get_rooms():
    status = request.args.get("status")
    conn = get_db()
    rooms = conn.fetchall("SELECT * FROM rooms WHERE status=? ORDER BY room_number", (status,)) if status \
            else conn.fetchall("SELECT * FROM rooms ORDER BY room_number")
    conn.close(); return jsonify(rooms)

@app.route("/api/rooms/<int:room_id>", methods=["GET"])
@require_auth
def get_room(room_id):
    conn = get_db()
    room = conn.fetchone("SELECT * FROM rooms WHERE room_id=?", (room_id,))
    conn.close()
    return jsonify(room) if room else (jsonify({"error":"Room not found"}), 404)

@app.route("/api/rooms", methods=["POST"])
@require_auth
@require_role("admin")
def create_room():
    data = request.get_json()
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO rooms (room_number,room_type,price,status,floor,description) VALUES (?,?,?,?,?,?)",
            (data["room_number"], data["room_type"], float(data["price"]),
             data.get("status","available"), data.get("floor",1), data.get("description","")))
        conn.commit(); room_id = conn.lastrowid(cur)
        log_action(request.user["user_id"], "CREATE_ROOM", f"Room {data['room_number']} created")
    except Exception:
        conn.close(); return jsonify({"error":"Room number already exists"}), 400
    conn.close(); return jsonify({"room_id": room_id, "message":"Room created"}), 201

@app.route("/api/rooms/<int:room_id>", methods=["PUT"])
@require_auth
@require_role("admin","receptionist")
def update_room(room_id):
    data = request.get_json()
    fields, values = [], []
    for f in ["room_type","price","status","floor","description","room_number"]:
        if f in data: fields.append(f"{f}=?"); values.append(data[f])
    if not fields: return jsonify({"error":"Nothing to update"}), 400
    values.append(room_id)
    conn = get_db()
    conn.execute(f"UPDATE rooms SET {', '.join(fields)} WHERE room_id=?", values)
    conn.commit(); conn.close()
    log_action(request.user["user_id"], "UPDATE_ROOM", f"Room {room_id} updated")
    return jsonify({"message":"Room updated"})

@app.route("/api/rooms/<int:room_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def delete_room(room_id):
    conn = get_db()
    conn.execute("DELETE FROM rooms WHERE room_id=?", (room_id,))
    conn.commit(); conn.close()
    return jsonify({"message":"Room deleted"})

# ─── GUESTS ──────────────────────────────────────────────────────────────────

@app.route("/api/guests", methods=["GET"])
@require_auth
def get_guests():
    s = request.args.get("search","")
    conn = get_db()
    guests = conn.fetchall("SELECT * FROM guests WHERE name LIKE ? OR phone LIKE ? ORDER BY created_at DESC", (f"%{s}%",f"%{s}%")) if s \
             else conn.fetchall("SELECT * FROM guests ORDER BY created_at DESC")
    conn.close(); return jsonify(guests)

@app.route("/api/guests/<int:guest_id>", methods=["GET"])
@require_auth
def get_guest(guest_id):
    conn = get_db()
    guest = conn.fetchone("SELECT * FROM guests WHERE guest_id=?", (guest_id,))
    bookings = conn.fetchall("""
        SELECT b.*, r.room_number, r.room_type FROM bookings b
        JOIN rooms r ON b.room_id=r.room_id WHERE b.guest_id=? ORDER BY b.created_at DESC
    """, (guest_id,))
    conn.close()
    return (jsonify({"guest": guest, "bookings": bookings}) if guest else (jsonify({"error":"Not found"}), 404))

@app.route("/api/guests", methods=["POST"])
@require_auth
def create_guest():
    data = request.get_json()
    conn = get_db()
    cur = conn.execute("INSERT INTO guests (name,phone,email,address,id_proof,id_number) VALUES (?,?,?,?,?,?)",
        (data["name"], data["phone"], data.get("email",""), data.get("address",""), data.get("id_proof",""), data.get("id_number","")))
    conn.commit(); guest_id = conn.lastrowid(cur); conn.close()
    return jsonify({"guest_id": guest_id, "message":"Guest created"}), 201

@app.route("/api/guests/<int:guest_id>", methods=["PUT"])
@require_auth
def update_guest(guest_id):
    data = request.get_json()
    conn = get_db()
    conn.execute("UPDATE guests SET name=?,phone=?,email=?,address=?,id_proof=?,id_number=? WHERE guest_id=?",
        (data["name"],data["phone"],data.get("email",""),data.get("address",""),data.get("id_proof",""),data.get("id_number",""),guest_id))
    conn.commit(); conn.close()
    return jsonify({"message":"Guest updated"})

# ─── BOOKINGS ────────────────────────────────────────────────────────────────

@app.route("/api/bookings", methods=["GET"])
@require_auth
def get_bookings():
    status = request.args.get("status"); date = request.args.get("date")
    conn = get_db()
    q = """SELECT b.*, g.name as guest_name, g.phone as guest_phone,
               r.room_number, r.room_type, r.price as room_price
           FROM bookings b JOIN guests g ON b.guest_id=g.guest_id
           JOIN rooms r ON b.room_id=r.room_id WHERE 1=1"""
    params = []
    if status: q += " AND b.status=?"; params.append(status)
    if date:   q += " AND (b.check_in<=? AND b.check_out>=?)"; params += [date, date]
    q += " ORDER BY b.created_at DESC"
    bookings = conn.fetchall(q, params); conn.close()
    return jsonify(bookings)

@app.route("/api/bookings/<int:booking_id>", methods=["GET"])
@require_auth
def get_booking(booking_id):
    conn = get_db()
    booking = conn.fetchone("""
        SELECT b.*, g.name as guest_name, g.phone as guest_phone, g.email as guest_email,
               g.address as guest_address, g.id_proof, g.id_number,
               r.room_number, r.room_type, r.price as room_price
        FROM bookings b JOIN guests g ON b.guest_id=g.guest_id
        JOIN rooms r ON b.room_id=r.room_id WHERE b.booking_id=?
    """, (booking_id,))
    payment = conn.fetchone("SELECT * FROM payments WHERE booking_id=?", (booking_id,))
    conn.close()
    return (jsonify({"booking": booking, "payment": payment}) if booking else (jsonify({"error":"Not found"}), 404))

@app.route("/api/bookings", methods=["POST"])
@require_auth
def create_booking():
    data = request.get_json()
    conn = get_db()
    room = conn.fetchone("SELECT * FROM rooms WHERE room_id=?", (data["room_id"],))
    if not room: conn.close(); return jsonify({"error":"Room not found"}), 404
    if room["status"] != "available": conn.close(); return jsonify({"error":f"Room is {room['status']}"}), 400
    overlap = conn.fetchone("""SELECT 1 FROM bookings WHERE room_id=? AND status IN ('confirmed','checked_in')
        AND NOT (check_out<=? OR check_in>=?)""", (data["room_id"], data["check_in"], data["check_out"]))
    if overlap: conn.close(); return jsonify({"error":"Room already booked for these dates"}), 400
    ci = datetime.date.fromisoformat(data["check_in"])
    co = datetime.date.fromisoformat(data["check_out"])
    nights = (co - ci).days; total = nights * room["price"]
    cur = conn.execute(
        "INSERT INTO bookings (guest_id,room_id,check_in,check_out,status,total_amount,notes,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (data["guest_id"],data["room_id"],data["check_in"],data["check_out"],"confirmed",total,data.get("notes",""),request.user["user_id"]))
    booking_id = conn.lastrowid(cur)
    conn.execute("UPDATE rooms SET status='occupied' WHERE room_id=?", (data["room_id"],))
    conn.execute("INSERT INTO payments (booking_id,amount,payment_method,payment_status) VALUES (?,?,?,?)",
                 (booking_id, total, data.get("payment_method","cash"), "pending"))
    conn.commit(); conn.close()
    log_action(request.user["user_id"], "CREATE_BOOKING", f"Booking {booking_id} created")
    return jsonify({"booking_id": booking_id, "total_amount": total, "nights": nights}), 201

@app.route("/api/bookings/<int:booking_id>/checkin", methods=["POST"])
@require_auth
def checkin(booking_id):
    conn = get_db()
    b = conn.fetchone("SELECT * FROM bookings WHERE booking_id=?", (booking_id,))
    if not b: conn.close(); return jsonify({"error":"Not found"}), 404
    if b["status"] != "confirmed": conn.close(); return jsonify({"error":"Not confirmed"}), 400
    conn.execute("UPDATE bookings SET status='checked_in' WHERE booking_id=?", (booking_id,))
    conn.execute("UPDATE rooms SET status='occupied' WHERE room_id=?", (b["room_id"],))
    conn.commit(); conn.close()
    log_action(request.user["user_id"], "CHECK_IN", f"Booking {booking_id} checked in")
    return jsonify({"message":"Checked in successfully"})

@app.route("/api/bookings/<int:booking_id>/checkout", methods=["POST"])
@require_auth
def checkout(booking_id):
    conn = get_db()
    b = conn.fetchone("SELECT * FROM bookings WHERE booking_id=?", (booking_id,))
    if not b: conn.close(); return jsonify({"error":"Not found"}), 404
    if b["status"] != "checked_in": conn.close(); return jsonify({"error":"Not checked in"}), 400
    conn.execute("UPDATE bookings SET status='checked_out' WHERE booking_id=?", (booking_id,))
    conn.execute("UPDATE rooms SET status='cleaning' WHERE room_id=?", (b["room_id"],))
    conn.execute("UPDATE payments SET payment_status='paid', paid_at=datetime('now') WHERE booking_id=?", (booking_id,))
    conn.commit(); conn.close()
    log_action(request.user["user_id"], "CHECK_OUT", f"Booking {booking_id} checked out")
    return jsonify({"message":"Checked out successfully"})

@app.route("/api/bookings/<int:booking_id>/cancel", methods=["POST"])
@require_auth
def cancel_booking(booking_id):
    conn = get_db()
    b = conn.fetchone("SELECT * FROM bookings WHERE booking_id=?", (booking_id,))
    if not b: conn.close(); return jsonify({"error":"Not found"}), 404
    conn.execute("UPDATE bookings SET status='cancelled' WHERE booking_id=?", (booking_id,))
    conn.execute("UPDATE rooms SET status='available' WHERE room_id=?", (b["room_id"],))
    conn.commit(); conn.close()
    return jsonify({"message":"Booking cancelled"})

# ─── PAYMENTS ────────────────────────────────────────────────────────────────

@app.route("/api/payments", methods=["GET"])
@require_auth
def get_payments():
    conn = get_db()
    payments = conn.fetchall("""
        SELECT p.*, b.check_in, b.check_out, g.name as guest_name, r.room_number
        FROM payments p JOIN bookings b ON p.booking_id=b.booking_id
        JOIN guests g ON b.guest_id=g.guest_id JOIN rooms r ON b.room_id=r.room_id
        ORDER BY p.payment_id DESC""")
    conn.close(); return jsonify(payments)

# ─── STAFF ───────────────────────────────────────────────────────────────────

@app.route("/api/staff", methods=["GET"])
@require_auth
@require_role("admin")
def get_staff():
    conn = get_db()
    staff = conn.fetchall("SELECT user_id,username,role,status,created_at FROM users ORDER BY user_id")
    conn.close(); return jsonify(staff)

@app.route("/api/staff", methods=["POST"])
@require_auth
@require_role("admin")
def create_staff():
    data = request.get_json()
    pw = hashlib.sha256(data["password"].encode()).hexdigest()
    conn = get_db()
    try:
        cur = conn.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                           (data["username"], pw, data.get("role","receptionist")))
        conn.commit(); uid = conn.lastrowid(cur)
    except Exception: conn.close(); return jsonify({"error":"Username already exists"}), 400
    conn.close(); return jsonify({"user_id": uid, "message":"Staff created"}), 201

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
    conn.commit(); conn.close()
    return jsonify({"message":"Staff updated"})

# ─── HOUSEKEEPING ────────────────────────────────────────────────────────────

@app.route("/api/housekeeping", methods=["GET"])
@require_auth
def get_housekeeping():
    conn = get_db()
    rooms = conn.fetchall("SELECT * FROM rooms WHERE status IN ('cleaning','maintenance','available') ORDER BY room_number")
    conn.close(); return jsonify(rooms)

@app.route("/api/housekeeping/<int:room_id>", methods=["PUT"])
@require_auth
@require_role("admin","housekeeping","receptionist")
def update_housekeeping(room_id):
    data = request.get_json(); status = data.get("status")
    if status not in ("available","cleaning","maintenance"):
        return jsonify({"error":"Invalid status"}), 400
    conn = get_db()
    conn.execute("UPDATE rooms SET status=? WHERE room_id=?", (status, room_id))
    conn.commit(); conn.close()
    log_action(request.user["user_id"], "HOUSEKEEPING", f"Room {room_id} → {status}")
    return jsonify({"message":"Room status updated"})

# ─── REPORTS ─────────────────────────────────────────────────────────────────

@app.route("/api/reports/dashboard", methods=["GET"])
@require_auth
def dashboard():
    conn = get_db()
    today       = datetime.date.today().isoformat()
    month_start = datetime.date.today().replace(day=1).isoformat()

    def n(sql, p=()):
        row = conn.fetchone(sql, p)
        return list(row.values())[0] if row else 0

    result = {
        "rooms": {
            "total":       n("SELECT COUNT(*) as v FROM rooms"),
            "available":   n("SELECT COUNT(*) as v FROM rooms WHERE status='available'"),
            "occupied":    n("SELECT COUNT(*) as v FROM rooms WHERE status='occupied'"),
            "cleaning":    n("SELECT COUNT(*) as v FROM rooms WHERE status='cleaning'"),
            "maintenance": n("SELECT COUNT(*) as v FROM rooms WHERE status='maintenance'"),
        },
        "bookings": {
            "total":          n("SELECT COUNT(*) as v FROM bookings"),
            "today_checkins": n("SELECT COUNT(*) as v FROM bookings WHERE check_in=? AND status IN ('confirmed','checked_in')",(today,)),
            "today_checkouts":n("SELECT COUNT(*) as v FROM bookings WHERE check_out=? AND status='checked_in'",(today,)),
            "active_guests":  n("SELECT COUNT(*) as v FROM bookings WHERE status='checked_in'"),
        },
        "revenue": {
            "today":   n("SELECT COALESCE(SUM(amount),0) as v FROM payments WHERE payment_status='paid' AND date(paid_at)=?",(today,)),
            "monthly": n("SELECT COALESCE(SUM(amount),0) as v FROM payments WHERE payment_status='paid' AND date(paid_at)>=?",(month_start,)),
            "last_7_days": [
                {"date": (datetime.date.today()-datetime.timedelta(days=i)).isoformat(),
                 "revenue": n("SELECT COALESCE(SUM(amount),0) as v FROM payments WHERE payment_status='paid' AND date(paid_at)=?",
                              ((datetime.date.today()-datetime.timedelta(days=i)).isoformat(),))}
                for i in range(6,-1,-1)
            ]
        },
        "booking_distribution": conn.fetchall("SELECT status, COUNT(*) as count FROM bookings GROUP BY status"),
        "room_types": conn.fetchall("""SELECT room_type, COUNT(*) as total,
            SUM(CASE WHEN status='available' THEN 1 ELSE 0 END) as available FROM rooms GROUP BY room_type"""),
    }
    tr = result["rooms"]["total"]
    result["occupancy_rate"] = round((result["rooms"]["occupied"]/tr*100) if tr else 0, 1)
    conn.close()
    return jsonify(result)

@app.route("/api/reports/revenue", methods=["GET"])
@require_auth
def revenue_report():
    period = request.args.get("period","monthly")
    conn = get_db()
    if period == "daily":
        data = conn.fetchall("""SELECT date(paid_at) as period, SUM(amount) as revenue, COUNT(*) as transactions
            FROM payments WHERE payment_status='paid' GROUP BY date(paid_at) ORDER BY period DESC LIMIT 30""")
    else:
        data = conn.fetchall("""SELECT strftime('%Y-%m', paid_at) as period, SUM(amount) as revenue, COUNT(*) as transactions
            FROM payments WHERE payment_status='paid' GROUP BY strftime('%Y-%m', paid_at) ORDER BY period DESC LIMIT 12""")
    conn.close(); return jsonify(data)

@app.route("/api/logs", methods=["GET"])
@require_auth
@require_role("admin")
def get_logs():
    conn = get_db()
    logs = conn.fetchall("""SELECT l.*, u.username FROM system_logs l
        LEFT JOIN users u ON l.user_id=u.user_id ORDER BY l.created_at DESC LIMIT 200""")
    conn.close(); return jsonify(logs)

# ─── SERVE FRONTEND ──────────────────────────────────────────────────────────

@app.route("/", defaults={"path":""})
@app.route("/<path:path>")
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

# ─── START ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("  HRMS  →  http://localhost:5000")
    print("  Login: admin / admin123")
    print("=" * 50)
    app.run(debug=True, port=5000, host="0.0.0.0")
