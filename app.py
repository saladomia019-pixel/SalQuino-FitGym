from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
from functools import wraps
import logging
import re

app = Flask(__name__)
app.secret_key = "antigravity-secret-key-2024"

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= DATABASE =================
def get_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="gym_db",
            autocommit=True
        )
    except Error as e:
        logger.error(f"Database connection failed: {e}")
        return None

# ================= AUTH DECORATORS =================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_type' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_type') != 'admin':
            return redirect('/admin-login')
        return f(*args, **kwargs)
    return decorated

def member_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_type') != 'member':
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# =============================================
#              PUBLIC ROUTES
# =============================================

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_connection()
        if not conn:
            flash("Database unavailable", "error")
            return render_template('login.html')

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM members WHERE email=%s", (email,))
            member = cursor.fetchone()
            cursor.close()
            conn.close()

            if member and check_password_hash(member['password'], password):
                session.clear()
                session['user_id'] = member['member_id']
                session['name'] = f"{member['first_name']} {member['last_name']}"
                session['user_type'] = 'member'
                return redirect('/dashboard')
            else:
                flash("Invalid email or password", "error")
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash("Login failed", "error")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = {
                'first_name': request.form.get('first_name', '').strip(),
                'last_name': request.form.get('last_name', '').strip(),
                'gender': request.form.get('gender', 'Other').strip(),
                'email': request.form.get('email', '').strip().lower(),
                'phone': request.form.get('phone', '').strip(),
                'password': request.form.get('password', ''),
                'confirm_password': request.form.get('confirm_password', '')
            }
            safe = {k: v for k, v in data.items() if k not in ('password', 'confirm_password')}

            if len(data['phone']) != 11 or not data['phone'].isdigit():
                flash("Phone must be exactly 11 digits", "error")
                return render_template('register.html', **safe)
            if data['password'] != data['confirm_password']:
                flash("Passwords don't match", "error")
                return render_template('register.html', **safe)
            if len(data['first_name']) < 2 or len(data['last_name']) < 2:
                flash("Name must be at least 2 characters", "error")
                return render_template('register.html', **safe)
            if len(data['password']) < 6:
                flash("Password must be at least 6 characters", "error")
                return render_template('register.html', **safe)
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', data['email']):
                flash("Invalid email format", "error")
                return render_template('register.html', **safe)

            conn = get_connection()
            if not conn:
                flash("Database unavailable", "error")
                return render_template('register.html', **safe)

            cursor = conn.cursor()
            cursor.execute("SELECT member_id FROM members WHERE email=%s OR phone=%s",
                           (data['email'], data['phone']))
            if cursor.fetchone():
                cursor.close(); conn.close()
                flash("Email or phone already registered", "error")
                return render_template('register.html', **safe)

            hashed = generate_password_hash(data['password'])
            cursor.execute("""
                INSERT INTO members (first_name, last_name, gender, email, phone, password, join_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), 'active')
            """, (data['first_name'], data['last_name'], data['gender'],
                  data['email'], data['phone'], hashed))
            conn.commit()
            cursor.close(); conn.close()
            flash("Account created successfully! Please login.", "success")
            return redirect('/login')
        except Exception as e:
            logger.error(f"Register error: {e}")
            flash(f"Registration failed: {str(e)}", "error")

    return render_template('register.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        conn = get_connection()
        if not conn:
            flash("Database unavailable", "error")
            return render_template('admin_login.html')

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE username=%s", (username,))
        admin = cursor.fetchone()
        cursor.close(); conn.close()

        if admin and (check_password_hash(admin['password'], password) or password == admin['password']):
            session.clear()
            session['user_id'] = admin['admin_id']
            session['name'] = admin['username']
            session['user_type'] = 'admin'
            return redirect('/admin-dashboard')
        else:
            flash("Invalid username or password", "error")

    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    user_type = session.get('user_type', 'member')
    session.clear()
    if user_type == 'admin':
        return redirect('/admin-login')
    return redirect('/login')

# =============================================
#              MEMBER ROUTES
# =============================================

@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('user_type') == 'admin':
        return redirect('/admin-dashboard')
    return render_template('member_dashboard.html', user=session)

@app.route('/api/plans', methods=['GET'])
@login_required
def get_plans():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT plan_id, plan_name, type, duration_days, price, description
            FROM membership_plans WHERE status='active' ORDER BY price ASC
        """)
        plans = cursor.fetchall()
        for p in plans:
            p['price'] = float(p['price'])
        cursor.close(); conn.close()
        return jsonify({"plans": plans})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/apply-membership', methods=['POST'])
@member_required
def apply_membership():
    data = request.get_json()
    required = ['plan_id', 'full_name', 'phone', 'gender', 'age', 'address', 'payment_method', 'start_date']
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    payment_method = data['payment_method']  # 'online' or 'walkin'
    if payment_method not in ('online', 'walkin'):
        return jsonify({"error": "Invalid payment method"}), 400

    # Parse and validate start_date
    try:
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if start_date < date.today():
            return jsonify({"error": "Start date cannot be in the past"}), 400
    except ValueError:
        return jsonify({"error": "Invalid start date format"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        member_id = session['user_id']

        # Check existing pending application
        cursor.execute("SELECT application_id FROM membership_applications WHERE member_id=%s AND status='pending'",
                       (member_id,))
        if cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({"error": "You already have a pending application"}), 400

        # Get plan details
        cursor.execute("SELECT price, plan_name, type, duration_days FROM membership_plans WHERE plan_id=%s", (data['plan_id'],))
        plan = cursor.fetchone()
        if not plan:
            cursor.close(); conn.close()
            return jsonify({"error": "Invalid plan selected"}), 400

        cursor.execute("""
            INSERT INTO membership_applications
            (member_id, plan_id, full_name, email, phone, gender, age, address, start_date, status, applied_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
        """, (member_id, data['plan_id'], data['full_name'],
              data.get('email', ''), data['phone'], data['gender'],
              data['age'], data['address'], start_date))

        app_id = cursor.lastrowid

        # Compute end date for response
        end_date = start_date + timedelta(days=plan['duration_days'])

        # Payment status depends on payment method
        payment_status = 'paid' if payment_method == 'online' else 'pending'
        cursor.execute("""
            INSERT INTO payments (member_id, membership_id, amount, payment_date, status, payment_method)
            VALUES (%s, NULL, %s, NOW(), %s, %s)
        """, (member_id, plan['price'], payment_status, payment_method))
        payment_id = cursor.lastrowid

        cursor.close(); conn.close()

        # Build response with ticket/receipt data
        import random, string
        ref_code = 'AG-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        response_data = {
            "message": "Application submitted successfully!",
            "payment_method": payment_method,
            "payment_status": payment_status,
            "reference_code": ref_code,
            "application_id": app_id,
            "payment_id": payment_id,
            "plan_name": plan['plan_name'],
            "plan_type": plan['type'],
            "duration_days": plan['duration_days'],
            "amount": float(plan['price']),
            "full_name": data['full_name'],
            "start_date": str(start_date),
            "end_date": str(end_date),
            "date": str(date.today())
        }
        return jsonify(response_data), 201
    except Exception as e:
        logger.error(f"Apply membership error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/my-membership', methods=['GET'])
@member_required
def get_my_membership():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        mid = session['user_id']

        cursor.execute("""
            SELECT m.*, p.plan_name, p.type as plan_type, p.price, p.duration_days,
                   DATEDIFF(m.end_date, CURDATE()) as days_remaining
            FROM memberships m JOIN membership_plans p ON m.plan_id = p.plan_id
            WHERE m.member_id=%s AND m.status='active' AND m.end_date >= CURDATE()
            ORDER BY m.start_date DESC LIMIT 1
        """, (mid,))
        membership = cursor.fetchone()

        cursor.execute("""
            SELECT a.*, p.plan_name, p.type as plan_type, p.price, p.duration_days
            FROM membership_applications a JOIN membership_plans p ON a.plan_id = p.plan_id
            WHERE a.member_id=%s AND a.status='pending'
            ORDER BY a.applied_at DESC LIMIT 1
        """, (mid,))
        pending = cursor.fetchone()
        cursor.close(); conn.close()

        result = {"has_active": False, "membership": None, "has_pending": False, "pending_application": None}
        if membership:
            result["has_active"] = True
            result["membership"] = {
                "plan_name": membership['plan_name'], "plan_type": membership['plan_type'],
                "price": float(membership['price']), "duration_days": membership['duration_days'],
                "start_date": str(membership['start_date']), "end_date": str(membership['end_date']),
                "days_remaining": max(0, membership['days_remaining']), "status": membership['status']
            }
        if pending:
            result["has_pending"] = True
            pending_start = pending.get('start_date')
            pending_end = None
            if pending_start:
                from datetime import timedelta as td
                if isinstance(pending_start, str):
                    pending_start_d = datetime.strptime(pending_start, '%Y-%m-%d').date()
                else:
                    pending_start_d = pending_start
                pending_end = pending_start_d + timedelta(days=pending['duration_days'])
                pending_start = str(pending_start_d)
                pending_end = str(pending_end)
            result["pending_application"] = {
                "application_id": pending['application_id'], "plan_name": pending['plan_name'],
                "plan_type": pending['plan_type'], "price": float(pending['price']),
                "duration_days": pending['duration_days'],
                "status": pending['status'], "applied_at": str(pending['applied_at']),
                "start_date": pending_start, "end_date": pending_end
            }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/checkin', methods=['POST'])
@member_required
def checkin():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        mid = session['user_id']

        cursor.execute("SELECT COUNT(*) as cnt FROM memberships WHERE member_id=%s AND status='active' AND end_date >= CURDATE()", (mid,))
        if cursor.fetchone()['cnt'] == 0:
            cursor.close(); conn.close()
            return jsonify({"error": "No active membership. Please apply first."}), 403

        cursor.execute("SELECT COUNT(*) as cnt FROM attendance WHERE member_id=%s AND DATE(checkin_time)=CURDATE()", (mid,))
        if cursor.fetchone()['cnt'] > 0:
            cursor.close(); conn.close()
            return jsonify({"error": "Already checked in today!"}), 400

        cursor.execute("INSERT INTO attendance (member_id, checkin_time) VALUES (%s, NOW())", (mid,))
        cursor.close(); conn.close()
        return jsonify({"message": "Check-in successful! Have a great workout! 💪"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/my-checkins', methods=['GET'])
@member_required
def get_my_checkins():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT attendance_id, checkin_time, DATE(checkin_time) as checkin_date
            FROM attendance WHERE member_id=%s ORDER BY checkin_time DESC
        """, (session['user_id'],))
        checkins = cursor.fetchall()
        cursor.close(); conn.close()
        for c in checkins:
            c['checkin_time'] = str(c['checkin_time'])
            c['checkin_date'] = str(c['checkin_date'])
        return jsonify(checkins)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/log-weight', methods=['POST'])
@member_required
def log_weight():
    data = request.get_json()
    weight = data.get('weight_kg')
    if not weight or float(weight) <= 0:
        return jsonify({"error": "Valid weight is required"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO weight_logs (member_id, weight_kg, logged_at) VALUES (%s, %s, NOW())",
                       (session['user_id'], float(weight)))
        cursor.close(); conn.close()
        return jsonify({"message": "Weight logged successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/my-weights', methods=['GET'])
@member_required
def get_my_weights():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT log_id, weight_kg, logged_at FROM weight_logs WHERE member_id=%s ORDER BY logged_at DESC",
                       (session['user_id'],))
        weights = cursor.fetchall()
        cursor.close(); conn.close()
        for w in weights:
            w['weight_kg'] = float(w['weight_kg'])
            w['logged_at'] = str(w['logged_at'])
        return jsonify(weights)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
#              MEMBER PROFILE & PASSWORD
# =============================================

@app.route('/api/my-profile', methods=['GET'])
@member_required
def get_my_profile():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT member_id, first_name, last_name, email, phone, gender, join_date, status, height_cm FROM members WHERE member_id=%s",
                       (session['user_id'],))
        member = cursor.fetchone()
        cursor.close(); conn.close()
        if not member:
            return jsonify({"error": "Member not found"}), 404
        member['join_date'] = str(member['join_date'])
        return jsonify(member)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/my-profile', methods=['PUT'])
@member_required
def update_my_profile():
    data = request.get_json()
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone = data.get('phone', '').strip()
        height_cm = data.get('height_cm')

        if len(first_name) < 2 or len(last_name) < 2:
            return jsonify({"error": "Name must be at least 2 characters"}), 400
        if len(phone) != 11 or not phone.isdigit():
            return jsonify({"error": "Phone must be exactly 11 digits"}), 400

        try:
            height_val = float(height_cm) if height_cm else None
        except ValueError:
            height_val = None

        cursor = conn.cursor()
        cursor.execute("UPDATE members SET first_name=%s, last_name=%s, phone=%s, height_cm=%s WHERE member_id=%s",
                       (first_name, last_name, phone, height_val, session['user_id']))
        cursor.close(); conn.close()
        session['name'] = f"{first_name} {last_name}"
        return jsonify({"message": "Profile updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/change-password', methods=['POST'])
@member_required
def change_password():
    data = request.get_json()
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')
    confirm_pw = data.get('confirm_password', '')
    if not current_pw or not new_pw or not confirm_pw:
        return jsonify({"error": "All fields are required"}), 400
    if len(new_pw) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400
    if new_pw != confirm_pw:
        return jsonify({"error": "New passwords don't match"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT password FROM members WHERE member_id=%s", (session['user_id'],))
        member = cursor.fetchone()
        if not member or not check_password_hash(member['password'], current_pw):
            cursor.close(); conn.close()
            return jsonify({"error": "Current password is incorrect"}), 400
        hashed = generate_password_hash(new_pw)
        cursor.execute("UPDATE members SET password=%s WHERE member_id=%s", (hashed, session['user_id']))
        cursor.close(); conn.close()
        return jsonify({"message": "Password changed successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
#              CHECK-IN STREAK
# =============================================

@app.route('/api/my-streak', methods=['GET'])
@member_required
def get_my_streak():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT DISTINCT DATE(checkin_time) as checkin_date
            FROM attendance WHERE member_id=%s ORDER BY checkin_date DESC
        """, (session['user_id'],))
        rows = cursor.fetchall()
        cursor.close(); conn.close()

        checkin_dates = [str(r['checkin_date']) for r in rows]

        # Calculate current streak
        current_streak = 0
        if checkin_dates:
            today = date.today()
            check_date = today
            # Allow streak to start from today or yesterday
            if checkin_dates[0] == str(today):
                current_streak = 1
                check_date = today - timedelta(days=1)
                idx = 1
            elif checkin_dates[0] == str(today - timedelta(days=1)):
                current_streak = 1
                check_date = today - timedelta(days=2)
                idx = 1
            else:
                idx = 0
                check_date = None

            if check_date is not None:
                for i in range(idx, len(checkin_dates)):
                    if checkin_dates[i] == str(check_date):
                        current_streak += 1
                        check_date -= timedelta(days=1)
                    else:
                        break

        # Calculate longest streak
        longest_streak = 0
        if checkin_dates:
            dates_sorted = sorted(checkin_dates)
            streak = 1
            for i in range(1, len(dates_sorted)):
                prev = datetime.strptime(dates_sorted[i-1], '%Y-%m-%d').date()
                curr = datetime.strptime(dates_sorted[i], '%Y-%m-%d').date()
                if (curr - prev).days == 1:
                    streak += 1
                else:
                    longest_streak = max(longest_streak, streak)
                    streak = 1
            longest_streak = max(longest_streak, streak)

        return jsonify({
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_checkins": len(checkin_dates),
            "checkin_dates": checkin_dates
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
#              MEMBERSHIP RENEWAL
# =============================================

@app.route('/api/renew-membership', methods=['POST'])
@member_required
def renew_membership():
    data = request.get_json()
    plan_id = data.get('plan_id')
    payment_method = data.get('payment_method')
    start_date_str = data.get('start_date')

    if not plan_id or not payment_method or not start_date_str:
        return jsonify({"error": "plan_id, payment_method, and start_date are required"}), 400
    if payment_method not in ('online', 'walkin'):
        return jsonify({"error": "Invalid payment method"}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid start date format"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        member_id = session['user_id']

        # Get current active membership
        cursor.execute("""
            SELECT m.*, DATEDIFF(m.end_date, CURDATE()) as days_remaining
            FROM memberships m WHERE m.member_id=%s AND m.status='active' AND m.end_date >= CURDATE()
            ORDER BY m.end_date DESC LIMIT 1
        """, (member_id,))
        current = cursor.fetchone()
        if not current or current['days_remaining'] > 14:
            cursor.close(); conn.close()
            return jsonify({"error": "Renewal is only available when your membership has 14 or fewer days remaining"}), 400

        # Check no pending application
        cursor.execute("SELECT application_id FROM membership_applications WHERE member_id=%s AND status='pending'", (member_id,))
        if cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({"error": "You already have a pending application"}), 400

        # Get plan details
        cursor.execute("SELECT price, plan_name, type, duration_days FROM membership_plans WHERE plan_id=%s AND status='active'", (plan_id,))
        plan = cursor.fetchone()
        if not plan:
            cursor.close(); conn.close()
            return jsonify({"error": "Invalid plan selected"}), 400

        # Get member info for the application
        cursor.execute("SELECT first_name, last_name, phone, gender, email FROM members WHERE member_id=%s", (member_id,))
        member = cursor.fetchone()

        end_date = start_date + timedelta(days=plan['duration_days'])

        # Create the renewal application
        cursor.execute("""
            INSERT INTO membership_applications
            (member_id, plan_id, full_name, email, phone, gender, age, address, start_date, status, applied_at)
            VALUES (%s, %s, %s, %s, %s, %s, 0, 'Renewal', %s, 'pending', NOW())
        """, (member_id, plan_id, f"{member['first_name']} {member['last_name']}",
              member['email'], member['phone'], member['gender'], start_date))
        app_id = cursor.lastrowid

        # Create payment
        payment_status = 'paid' if payment_method == 'online' else 'pending'
        cursor.execute("""
            INSERT INTO payments (member_id, membership_id, amount, payment_date, status, payment_method)
            VALUES (%s, NULL, %s, NOW(), %s, %s)
        """, (member_id, plan['price'], payment_status, payment_method))
        payment_id = cursor.lastrowid

        cursor.close(); conn.close()

        import random, string
        ref_code = 'RN-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return jsonify({
            "message": "Renewal application submitted successfully!",
            "payment_method": payment_method,
            "payment_status": payment_status,
            "reference_code": ref_code,
            "application_id": app_id,
            "payment_id": payment_id,
            "plan_name": plan['plan_name'],
            "plan_type": plan['type'],
            "duration_days": plan['duration_days'],
            "amount": float(plan['price']),
            "full_name": f"{member['first_name']} {member['last_name']}",
            "start_date": str(start_date),
            "end_date": str(end_date),
            "date": str(date.today())
        }), 201
    except Exception as e:
        logger.error(f"Renew membership error: {e}")
        return jsonify({"error": str(e)}), 500

# =============================================
#              ADMIN ROUTES
# =============================================

def log_admin_activity(admin_id, action_type, description):
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO admin_activity_logs (admin_id, action_type, description) VALUES (%s, %s, %s)",
                           (admin_id, action_type, description))
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log admin activity: {e}")

@app.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', user=session)

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as count FROM members")
        total_members = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM memberships WHERE status='active' AND end_date >= CURDATE()")
        active = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM membership_applications WHERE status='pending'")
        pending = cursor.fetchone()['count']
        cursor.execute("SELECT COALESCE(SUM(amount),0) as total FROM payments WHERE status='paid'")
        revenue = cursor.fetchone()['total']
        cursor.close(); conn.close()
        return jsonify({"total_members": total_members, "active_memberships": active,
                        "pending_requests": pending, "total_revenue": float(revenue)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/members', methods=['GET'])
@admin_required
def admin_get_members():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT member_id, first_name, last_name, email, phone, gender, status, join_date FROM members ORDER BY join_date DESC")
        members = cursor.fetchall()
        cursor.close(); conn.close()
        for m in members:
            m['join_date'] = str(m['join_date'])
        return jsonify(members)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/members/<int:member_id>', methods=['PUT'])
@admin_required
def admin_edit_member(member_id):
    data = request.get_json()
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE members SET first_name=%s, last_name=%s, email=%s, phone=%s, gender=%s, status=%s
            WHERE member_id=%s
        """, (data['first_name'], data['last_name'], data['email'],
              data['phone'], data['gender'], data['status'], member_id))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Edit Member', f'Member ID: {member_id}')
        return jsonify({"message": "Member updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/members/<int:member_id>', methods=['DELETE'])
@admin_required
def admin_delete_member(member_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM weight_logs WHERE member_id=%s", (member_id,))
        cursor.execute("DELETE FROM attendance WHERE member_id=%s", (member_id,))
        cursor.execute("DELETE FROM payments WHERE member_id=%s", (member_id,))
        cursor.execute("DELETE FROM memberships WHERE member_id=%s", (member_id,))
        cursor.execute("DELETE FROM membership_applications WHERE member_id=%s", (member_id,))
        cursor.execute("DELETE FROM members WHERE member_id=%s", (member_id,))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Delete Member', f'Member ID: {member_id}')
        return jsonify({"message": "Member deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/pending-applications', methods=['GET'])
@admin_required
def admin_pending_applications():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, p.plan_name, p.type as plan_type, p.price, p.duration_days,
                   pay.status as payment_status, pay.payment_method, pay.payment_id as pay_id
            FROM membership_applications a
            JOIN membership_plans p ON a.plan_id = p.plan_id
            LEFT JOIN payments pay ON pay.member_id = a.member_id AND pay.amount = p.price
                AND pay.payment_id = (
                    SELECT MAX(p2.payment_id) FROM payments p2
                    WHERE p2.member_id = a.member_id AND p2.amount = p.price
                )
            ORDER BY CASE a.status WHEN 'pending' THEN 1 WHEN 'approved' THEN 2 ELSE 3 END, a.applied_at DESC
        """)
        apps = cursor.fetchall()
        cursor.close(); conn.close()
        for a in apps:
            a['price'] = float(a['price'])
            a['applied_at'] = str(a['applied_at'])
            a['payment_status'] = a.get('payment_status') or 'unknown'
            a['payment_method'] = a.get('payment_method') or 'unknown'
            a['pay_id'] = a.get('pay_id')
        return jsonify(apps)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/application/<int:app_id>/approve', methods=['POST'])
@admin_required
def admin_approve(app_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, p.duration_days, p.price
            FROM membership_applications a JOIN membership_plans p ON a.plan_id = p.plan_id
            WHERE a.application_id=%s AND a.status='pending'
        """, (app_id,))
        application = cursor.fetchone()
        if not application:
            cursor.close(); conn.close()
            return jsonify({"error": "Application not found or already processed"}), 404

        # APPROVAL CONSTRAINT: Check if payment is 'paid' before allowing approval
        cursor.execute("""
            SELECT payment_id, status FROM payments
            WHERE member_id=%s AND amount=%s AND membership_id IS NULL
            ORDER BY payment_date DESC LIMIT 1
        """, (application['member_id'], application['price']))
        payment = cursor.fetchone()
        if not payment or payment['status'] != 'paid':
            cursor.close(); conn.close()
            return jsonify({"error": "Cannot approve: Payment has not been completed yet. Please mark payment as Paid first."}), 400

        # Use the member's chosen start date (or fallback to today)
        start = application.get('start_date') or date.today()
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d').date()
        # If the chosen start date is in the past, use today
        if start < date.today():
            start = date.today()
        end = start + timedelta(days=application['duration_days'])
        cursor.execute("INSERT INTO memberships (member_id, plan_id, start_date, end_date, status) VALUES (%s,%s,%s,%s,'active')",
                       (application['member_id'], application['plan_id'], start, end))
        ms_id = cursor.lastrowid

        # Link the paid payment to the new membership
        cursor.execute("""
            UPDATE payments SET membership_id=%s
            WHERE payment_id=%s
        """, (ms_id, payment['payment_id']))

        cursor.execute("UPDATE membership_applications SET status='approved' WHERE application_id=%s", (app_id,))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Approve Membership', f'Application ID: {app_id}')
        return jsonify({"message": "Application approved! Membership activated."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/application/<int:app_id>/reject', methods=['POST'])
@admin_required
def admin_reject(app_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)

        # Get application info to find and remove pending payment
        cursor.execute("SELECT member_id, plan_id FROM membership_applications WHERE application_id=%s", (app_id,))
        app_info = cursor.fetchone()

        if app_info:
            # Get plan price to match the pending payment
            cursor.execute("SELECT price FROM membership_plans WHERE plan_id=%s", (app_info['plan_id'],))
            plan = cursor.fetchone()
            if plan:
                cursor.execute("DELETE FROM payments WHERE member_id=%s AND status='pending' AND amount=%s AND membership_id IS NULL ORDER BY payment_date DESC LIMIT 1",
                               (app_info['member_id'], plan['price']))

        cursor.execute("UPDATE membership_applications SET status='rejected' WHERE application_id=%s", (app_id,))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Reject Membership', f'Application ID: {app_id}')
        return jsonify({"message": "Application rejected."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/application/<int:app_id>/edit', methods=['PUT'])
@admin_required
def admin_edit_app(app_id):
    data = request.get_json()
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE membership_applications
            SET full_name=%s, phone=%s, gender=%s, age=%s, address=%s, plan_id=%s
            WHERE application_id=%s AND status='pending'
        """, (data['full_name'], data['phone'], data['gender'],
              data['age'], data['address'], data['plan_id'], app_id))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Edit Application', f'Application ID: {app_id}')
        return jsonify({"message": "Application updated."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/payment/<int:payment_id>/mark-paid', methods=['POST'])
@admin_required
def admin_mark_paid(payment_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM payments WHERE payment_id=%s AND status='pending'", (payment_id,))
        payment = cursor.fetchone()
        if not payment:
            cursor.close(); conn.close()
            return jsonify({"error": "Payment not found or already paid"}), 404
        cursor.execute("UPDATE payments SET status='paid', payment_date=NOW() WHERE payment_id=%s", (payment_id,))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Mark Payment Paid', f'Payment ID: {payment_id}')
        return jsonify({"message": "Payment marked as Paid successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/payments', methods=['GET'])
@admin_required
def admin_payments():
    status_filter = request.args.get('status', 'all')
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT p.payment_id, p.amount, p.payment_date, p.status,
                   COALESCE(p.payment_method, '--') as payment_method,
                   CONCAT(m.first_name,' ',m.last_name) as member_name,
                   COALESCE(mp.plan_name, ap_plan.plan_name, '--') as plan_name
            FROM payments p
            JOIN members m ON p.member_id = m.member_id
            LEFT JOIN memberships ms ON p.membership_id = ms.membership_id
            LEFT JOIN membership_plans mp ON ms.plan_id = mp.plan_id
            LEFT JOIN membership_applications ma ON ma.member_id = p.member_id AND ma.status = 'pending'
            LEFT JOIN membership_plans ap_plan ON ma.plan_id = ap_plan.plan_id
            WHERE 1=1
        """
        params = []
        if status_filter in ('paid', 'pending'):
            query += " AND p.status=%s"
            params.append(status_filter)
        query += " ORDER BY p.payment_date DESC"
        cursor.execute(query, params)
        payments = cursor.fetchall()
        cursor.close(); conn.close()
        for p in payments:
            p['amount'] = float(p['amount'])
            p['payment_date'] = str(p['payment_date'])
        return jsonify(payments)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
#              ADMIN PLANS CRUD
# =============================================

@app.route('/api/admin/all-plans', methods=['GET'])
@admin_required
def admin_get_all_plans():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM membership_plans ORDER BY price ASC")
        plans = cursor.fetchall()
        cursor.close(); conn.close()
        for p in plans:
            p['price'] = float(p['price'])
        return jsonify(plans)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/plans', methods=['POST'])
@admin_required
def admin_create_plan():
    data = request.get_json()
    required = ['plan_name', 'type', 'duration_days', 'price']
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO membership_plans (plan_name, type, duration_days, price, description, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
        """, (data['plan_name'], data['type'], int(data['duration_days']),
              float(data['price']), data.get('description', '')))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Create Plan', f"Plan: {data['plan_name']}")
        return jsonify({"message": "Plan created successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/plans/<int:plan_id>', methods=['PUT'])
@admin_required
def admin_update_plan(plan_id):
    data = request.get_json()
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE membership_plans
            SET plan_name=%s, type=%s, duration_days=%s, price=%s, description=%s, status=%s
            WHERE plan_id=%s
        """, (data['plan_name'], data['type'], int(data['duration_days']),
              float(data['price']), data.get('description', ''), data.get('status', 'active'), plan_id))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Update Plan', f"Plan ID: {plan_id}")
        return jsonify({"message": "Plan updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/plans/<int:plan_id>/deactivate', methods=['POST'])
@admin_required
def admin_deactivate_plan(plan_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE membership_plans SET status='inactive' WHERE plan_id=%s", (plan_id,))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Deactivate Plan', f"Plan ID: {plan_id}")
        return jsonify({"message": "Plan deactivated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/plans/<int:plan_id>/activate', methods=['POST'])
@admin_required
def admin_activate_plan(plan_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE membership_plans SET status='active' WHERE plan_id=%s", (plan_id,))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Activate Plan', f"Plan ID: {plan_id}")
        return jsonify({"message": "Plan activated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
#              ADMIN ACTIVITY LOGS
# =============================================

@app.route('/api/admin/activity-logs', methods=['GET'])
@admin_required
def admin_activity_logs():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT l.log_id, l.action_type, l.description, l.created_at, a.username
            FROM admin_activity_logs l
            JOIN admins a ON l.admin_id = a.admin_id
            ORDER BY l.created_at DESC
        """)
        logs = cursor.fetchall()
        cursor.close(); conn.close()
        for log in logs:
            log['created_at'] = str(log['created_at'])
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
#              ANNOUNCEMENTS
# =============================================

@app.route('/api/announcements', methods=['GET'])
def get_active_announcements():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, content, created_at FROM announcements WHERE status='active' ORDER BY created_at DESC")
        announcements = cursor.fetchall()
        cursor.close(); conn.close()
        for a in announcements:
            a['created_at'] = str(a['created_at'])
        return jsonify(announcements)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/announcements', methods=['GET'])
@admin_required
def admin_get_announcements():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM announcements ORDER BY created_at DESC")
        announcements = cursor.fetchall()
        cursor.close(); conn.close()
        for a in announcements:
            a['created_at'] = str(a['created_at'])
        return jsonify(announcements)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/announcements', methods=['POST'])
@admin_required
def admin_create_announcement():
    data = request.get_json()
    if not data or not data.get('title') or not data.get('content'):
        return jsonify({"error": "Title and content are required"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO announcements (title, content, status) VALUES (%s, %s, %s)",
                       (data['title'], data['content'], data.get('status', 'active')))
        conn.commit()
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Create Announcement', f"Title: {data['title']}")
        return jsonify({"message": "Announcement created successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/announcements/<int:announcement_id>', methods=['PUT'])
@admin_required
def admin_update_announcement(announcement_id):
    data = request.get_json()
    if not data or not data.get('title') or not data.get('content'):
        return jsonify({"error": "Title and content are required"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE announcements SET title=%s, content=%s WHERE id=%s",
                       (data['title'], data['content'], announcement_id))
        conn.commit()
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Update Announcement', f"ID: {announcement_id}")
        return jsonify({"message": "Announcement updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/announcements/<int:announcement_id>', methods=['DELETE'])
@admin_required
def admin_delete_announcement(announcement_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM announcements WHERE id=%s", (announcement_id,))
        conn.commit()
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Delete Announcement', f"ID: {announcement_id}")
        return jsonify({"message": "Announcement deleted successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/announcements/<int:announcement_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_announcement(announcement_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database unavailable"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM announcements WHERE id=%s", (announcement_id,))
        announcement = cursor.fetchone()
        if not announcement:
            cursor.close(); conn.close()
            return jsonify({"error": "Announcement not found"}), 404
        
        new_status = 'inactive' if announcement['status'] == 'active' else 'active'
        cursor.execute("UPDATE announcements SET status=%s WHERE id=%s", (new_status, announcement_id))
        cursor.close(); conn.close()
        log_admin_activity(session['user_id'], 'Toggle Announcement', f"ID: {announcement_id} to {new_status}")
        return jsonify({"message": f"Announcement marked as {new_status}!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
