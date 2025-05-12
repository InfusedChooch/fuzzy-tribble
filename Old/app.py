from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
import pandas as pd
import json
import datetime
import os
import io
import csv

# === INITIALIZE FLASK APP ===
app = Flask(__name__)

# === CONFIGURATION FILE ===
CONFIG_FILE = 'data/config.json'

def load_json_file(filepath, default_value):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default_value
    return default_value

config = load_json_file(CONFIG_FILE, {})

app.secret_key = 'IloveGooningp00'

# === FILE LOCATIONS ===
MASTERLIST_FILE = 'data/masterlist.csv'
PASSLOG_FILE = 'data/passlog.json'
AUDITLOG_FILE = 'data/auditlog.json'

masterlist_df = pd.read_csv(MASTERLIST_FILE)

# === LOAD CONFIGURED PERIOD SCHEDULE ===
PERIOD_SCHEDULE = config.get('period_schedule', {})

# === INITIALIZE PASSES BASED ON CONFIGURED PASSES_AVAILABLE ===
passes = {str(i): {'status': 'open', 'user': None, 'time_out': None} for i in range(1, config.get('passes_available', 3) + 1)}
if '3' not in passes:
    passes['3'] = {'status': 'open', 'user': None, 'time_out': None}

passlog = load_json_file(PASSLOG_FILE, {})
auditlog = load_json_file(AUDITLOG_FILE, [])

def get_current_period():
    now = datetime.datetime.now().time()
    for period, times in PERIOD_SCHEDULE.items():
        start = datetime.datetime.strptime(times['start'], '%H:%M').time()
        end = datetime.datetime.strptime(times['end'], '%H:%M').time()
        if start <= now <= end:
            return period
    return None

def save_json_file(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def log_audit(student_id, reason):
    auditlog.append({
        'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'student_id': student_id,
        'reason': reason
    })
    save_json_file(AUDITLOG_FILE, auditlog)

@app.route('/')
def index():
    return render_template('index.html',
                           passes=passes,
                           current_period=get_current_period(),
                           school_name=config.get('school_name', 'School'),
                           theme_color=config.get('theme_color', '#4a90e2'),
                           logo_url=config.get('logo_url', '/static/images/school_logo.png'))

@app.route('/passes')
def get_passes():
    return jsonify(passes)

@app.route('/check', methods=['POST'])
def check():
    student_id = request.form.get('student_id', '').strip()
    current_period = get_current_period()
    current_day = datetime.datetime.now().strftime('%A')
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')

    try:
        student_row = masterlist_df[masterlist_df['ID'] == int(student_id)]
    except ValueError:
        log_audit(student_id, 'Invalid ID format')
        return jsonify({'message': 'Invalid ID format.'})

    if student_row.empty:
        log_audit(student_id, 'Invalid ID number')
        return jsonify({'message': 'Invalid ID number.'})

    student_period_value = student_row.iloc[0]['Period']
    # Normalize period to match JSON string key
    if float(student_period_value).is_integer():
        student_period_str = str(int(student_period_value))
    else:
        student_period_str = str(student_period_value)

    if current_period is None:
        log_audit(student_id, 'No active period')
        return jsonify({'message': 'No active period right now.'})

    if current_period != student_period_str:
        log_audit(student_id, f'Invalid period: tried {current_period}, expected {student_period_str}')
        return jsonify({'message': f'You cannot leave during this period (current: {current_period}).'})

    for pass_id, pass_data in passes.items():
        if pass_data['user'] == student_id and pass_data['status'] == 'in use':
            checkin_time = datetime.datetime.now().strftime('%H:%M:%S')
            time_out_dt = datetime.datetime.combine(datetime.datetime.today(), datetime.datetime.strptime(pass_data['time_out'], '%H:%M:%S').time())
            total_time = int((datetime.datetime.now() - time_out_dt).total_seconds())
            total_time = max(total_time, 0)
            passlog.setdefault(student_id, []).append({
                'Date': current_date,
                'DayOfWeek': current_day,
                'Period': str(current_period),
                'CheckoutTime': pass_data['time_out'],
                'CheckinTime': checkin_time,
                'TotalPassTime': total_time
            })
            save_json_file(PASSLOG_FILE, passlog)
            passes[pass_id] = {'status': 'open', 'user': None, 'time_out': None}
            return jsonify({'message': 'Returned successfully.'})

    for pass_id, pass_data in passes.items():
        if pass_id == '3':  # skip admin-only pass
            continue
        if pass_data['status'] == 'open':
            checkout_time = datetime.datetime.now().strftime('%H:%M:%S')
            passes[pass_id] = {'status': 'in use', 'user': student_id, 'time_out': checkout_time}
            return jsonify({'message': f'Pass {pass_id} claimed at {checkout_time}.'})

    return jsonify({'message': 'No passes available right now.'})

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        valid_username = username == config.get('admin_username')
        valid_password = password == config.get('admin_password')

        if valid_username and valid_password:
            session['logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin_view'))
        else:
            return render_template('admin_login.html', error='Incorrect username or password.', logo_url=config.get('logo_url'))
    return render_template('admin_login.html', logo_url=config.get('logo_url'))

@app.route('/admin_logout')
def admin_logout():
    session.pop('logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_view():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    weekly_summary = []
    for student_id, records in passlog.items():
        student_row = masterlist_df[masterlist_df['ID'] == int(student_id)]
        student_name = student_row.iloc[0]['Name'] if not student_row.empty else 'Unknown'
        total_time = sum(r['TotalPassTime'] for r in records)
        total_passes = len(records)
        avg_time = total_time // total_passes if total_passes else 0
        passes_over_5_min = sum(1 for r in records if r['TotalPassTime'] > config['report_time_thresholds']['over_5'])
        summary = {
            'student_id': student_id,
            'student_name': student_name,
            'total_time': f"{total_time // 60}m {total_time % 60}s",
            'total_passes': total_passes,
            'avg_time': f"{avg_time // 60}m {avg_time % 60}s",
            'passes_over_5_min': passes_over_5_min
        }
        weekly_summary.append(summary)

    return render_template('admin.html',
                           weekly_summary=weekly_summary,
                           audit_log=auditlog,
                           admin_username=session.get('admin_username'),
                           logo_url=config.get('logo_url'))

@app.route('/admin_passes')
def admin_passes():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403
    active_passes = []
    for pass_id, pass_data in passes.items():
        if pass_data['status'] == 'in use':
            student_row = masterlist_df[masterlist_df['ID'] == int(pass_data['user'])]
            student_name = student_row.iloc[0]['Name'] if not student_row.empty else 'Unknown'
            active_passes.append({
                'pass_id': pass_id,
                'student_id': pass_data['user'],
                'student_name': student_name,
                'time_out': pass_data['time_out']
            })
    return jsonify(active_passes)

@app.route('/admin_checkin/<pass_id>', methods=['POST'])
def admin_checkin(pass_id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403
    if pass_id not in passes or passes[pass_id]['status'] != 'in use':
        return jsonify({'message': f'Pass {pass_id} is not currently out.'})
    student_id = passes[pass_id]['user']
    checkin_time = datetime.datetime.now().strftime('%H:%M:%S')
    time_out_dt = datetime.datetime.combine(datetime.datetime.today(), datetime.datetime.strptime(passes[pass_id]['time_out'], '%H:%M:%S').time())
    total_time = int((datetime.datetime.now() - time_out_dt).total_seconds())
    total_time = max(total_time, 0)
    passlog.setdefault(student_id, []).append({
        'Date': datetime.datetime.now().strftime('%Y-%m-%d'),
        'DayOfWeek': datetime.datetime.now().strftime('%A'),
        'Period': str(get_current_period()),
        'CheckoutTime': passes[pass_id]['time_out'],
        'CheckinTime': checkin_time,
        'TotalPassTime': total_time
    })
    save_json_file(PASSLOG_FILE, passlog)
    passes[pass_id] = {'status': 'open', 'user': None, 'time_out': None}
    return jsonify({'message': f'Pass {pass_id} manually checked in.'})

@app.route('/admin_create_pass', methods=['POST'])
def admin_create_pass():
    if not session.get('logged_in'):
        return jsonify({'message': 'Unauthorized'}), 403
    data = request.get_json()
    student_id = data.get('student_id')
    try:
        student_row = masterlist_df[masterlist_df['ID'] == int(student_id)]
    except ValueError:
        return jsonify({'message': 'Invalid ID format.'})
    if student_row.empty:
        return jsonify({'message': 'Student ID not found.'})
    if passes['3']['status'] == 'in use':
        return jsonify({'message': 'Admin pass is already in use.'})
    passes['3'] = {'status': 'in use', 'user': student_id, 'time_out': datetime.datetime.now().strftime('%H:%M:%S')}
    return jsonify({'message': f'Admin Pass 3 created for Student ID {student_id}.'})

@app.route('/admin_report')
def admin_report():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403
    report_data = []
    days = config.get('report_days', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
    for student_id, records in passlog.items():
        student_row = masterlist_df[masterlist_df['ID'] == int(student_id)]
        student_name = student_row.iloc[0]['Name'] if not student_row.empty else 'Unknown'
        day_totals = {d: 0 for d in days}
        over_5 = sum(1 for r in records if r['TotalPassTime'] > config['report_time_thresholds']['over_5'])
        over_10 = sum(1 for r in records if r['TotalPassTime'] > config['report_time_thresholds']['over_10'])
        for r in records:
            if r['DayOfWeek'] in day_totals:
                day_totals[r['DayOfWeek']] += r['TotalPassTime']
        weekly = ' '.join(f"{d[0]}:{day_totals[d]//60}" for d in days)
        report_data.append({
            'student_name': student_name,
            'student_id': student_id,
            'weekly_report': weekly,
            'passes_over_5_min': over_5,
            'passes_over_10_min': over_10
        })
    return render_template('admin_report.html', report_data=report_data, logo_url=config.get('logo_url'))

@app.route('/admin_report_csv')
def admin_report_csv():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Student ID', 'Weekly Report', 'Passes Over 5 Min', 'Passes Over 10 Min'])
    days = config.get('report_days', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
    for student_id, records in passlog.items():
        student_row = masterlist_df[masterlist_df['ID'] == int(student_id)]
        student_name = student_row.iloc[0]['Name'] if not student_row.empty else 'Unknown'
        day_totals = {d: 0 for d in days}
        over_5 = sum(1 for r in records if r['TotalPassTime'] > config['report_time_thresholds']['over_5'])
        over_10 = sum(1 for r in records if r['TotalPassTime'] > config['report_time_thresholds']['over_10'])
        for r in records:
            if r['DayOfWeek'] in day_totals:
                day_totals[r['DayOfWeek']] += r['TotalPassTime']
        weekly = ' '.join(f"{d[0]}:{day_totals[d]//60}" for d in days)
        writer.writerow([student_name, student_id, weekly, over_5, over_10])
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=weekly_report.csv"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=config.get('debug_mode', True))
