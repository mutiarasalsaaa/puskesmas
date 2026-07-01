import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, date
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify, g)

app = Flask(__name__)
@app.route("/health")
def health():
    return "OK", 200
app.secret_key = 'puskesmas-rahasia-2024-ganti-di-produksi'

DATABASE = os.path.join(os.path.dirname(__file__), 'puskesmas.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid

def hash_password(pw):
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + pw).encode()).hexdigest()
    return f"{salt}:{hashed}"

def check_password(stored, provided):
    try:
        salt, hashed = stored.split(':')
        return hashlib.sha256((salt + provided).encode()).hexdigest() == hashed
    except:
        return False

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nama TEXT NOT NULL,
        role TEXT NOT NULL,
        aktif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS pasien (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        no_rm TEXT UNIQUE NOT NULL,
        nik TEXT UNIQUE NOT NULL,
        nama TEXT NOT NULL,
        tanggal_lahir TEXT NOT NULL,
        jenis_kelamin TEXT NOT NULL,
        alamat TEXT,
        no_hp TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS kunjungan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pasien_id INTEGER NOT NULL REFERENCES pasien(id),
        tanggal TEXT DEFAULT (date('now','localtime')),
        poli TEXT NOT NULL,
        status TEXT DEFAULT 'menunggu',
        no_antrian TEXT,
        keluhan TEXT,
        created_by INTEGER REFERENCES admin(id),
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS cek_vital (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kunjungan_id INTEGER NOT NULL REFERENCES kunjungan(id),
        tekanan_darah TEXT,
        nadi INTEGER,
        suhu REAL,
        berat_badan REAL,
        tinggi_badan REAL,
        saturasi_o2 INTEGER,
        catatan TEXT,
        created_by INTEGER REFERENCES admin(id),
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS rekam_medis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kunjungan_id INTEGER NOT NULL REFERENCES kunjungan(id),
        anamnesis TEXT,
        pemeriksaan_fisik TEXT,
        diagnosis TEXT,
        tindakan TEXT,
        resep TEXT,
        catatan TEXT,
        created_by INTEGER REFERENCES admin(id),
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    existing = db.execute("SELECT id FROM admin WHERE username='superadmin'").fetchone()
    if not existing:
        accounts = [
            ('superadmin', hash_password('admin123'), 'Super Administrator', 'super_admin'),
            ('loket1',     hash_password('loket123'),  'Admin Loket',        'loket'),
            ('cekvi1',     hash_password('cekvi123'),  'Admin Cek Vital',    'cek_vital'),
            ('dokter1',    hash_password('dokter123'), 'Dr. Budi Santoso',   'poli'),
        ]
        db.executemany("INSERT INTO admin (username,password,nama,role) VALUES (?,?,?,?)", accounts)
        db.commit()
        print("Database berhasil diinisialisasi.")
    db.close()

# ── Panggil init_db() di sini agar Gunicorn juga menjalankannya ──
init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'admin_id' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        admin = query("SELECT * FROM admin WHERE username=? AND aktif=1", (username,), one=True)
        if admin and check_password(admin['password'], password):
            session.update({'admin_id': admin['id'], 'username': admin['username'],
                            'nama': admin['nama'], 'role': admin['role']})
            flash(f"Selamat datang, {admin['nama']}!", 'success')
            return redirect(url_for('dashboard'))
        flash('Username atau password salah.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    role = session['role']
    today = date.today().isoformat()
    if role == 'super_admin':
        stats = {
            'total_admin':        query("SELECT COUNT(*) c FROM admin WHERE role!='super_admin'", one=True)['c'],
            'total_pasien':       query("SELECT COUNT(*) c FROM pasien", one=True)['c'],
            'kunjungan_hari_ini': query("SELECT COUNT(*) c FROM kunjungan WHERE tanggal=?", (today,), one=True)['c'],
            'kunjungan_selesai':  query("SELECT COUNT(*) c FROM kunjungan WHERE tanggal=? AND status='selesai'", (today,), one=True)['c'],
        }
        return render_template('dashboard_super_admin.html', stats=stats)
    elif role == 'loket':
        stats = {
            'kunjungan_hari_ini': query("SELECT COUNT(*) c FROM kunjungan WHERE tanggal=?", (today,), one=True)['c'],
            'menunggu':           query("SELECT COUNT(*) c FROM kunjungan WHERE tanggal=? AND status='menunggu'", (today,), one=True)['c'],
            'total_pasien':       query("SELECT COUNT(*) c FROM pasien", one=True)['c'],
        }
        kunjungan_list = query("""SELECT k.*,p.nama as pasien_nama FROM kunjungan k
            JOIN pasien p ON k.pasien_id=p.id WHERE k.tanggal=?
            ORDER BY k.created_at DESC LIMIT 20""", (today,))
        return render_template('dashboard_loket.html', stats=stats, kunjungan_list=kunjungan_list)
    elif role == 'cek_vital':
        stats = {
            'menunggu_cek_vital': query("SELECT COUNT(*) c FROM kunjungan WHERE tanggal=? AND status='menunggu'", (today,), one=True)['c'],
            'sudah_cek_vital':    query("SELECT COUNT(*) c FROM kunjungan WHERE tanggal=? AND status='cek_vital'", (today,), one=True)['c'],
        }
        kunjungan_list = query("""SELECT k.*,p.nama as pasien_nama,p.jenis_kelamin,p.tanggal_lahir,p.no_rm
            FROM kunjungan k JOIN pasien p ON k.pasien_id=p.id
            WHERE k.tanggal=? AND k.status='menunggu' ORDER BY k.no_antrian""", (today,))
        return render_template('dashboard_cek_vital.html', stats=stats, kunjungan_list=kunjungan_list)
    elif role == 'poli':
        stats = {
            'menunggu_poli': query("SELECT COUNT(*) c FROM kunjungan WHERE tanggal=? AND status='cek_vital'", (today,), one=True)['c'],
            'selesai':       query("SELECT COUNT(*) c FROM kunjungan WHERE tanggal=? AND status='selesai'", (today,), one=True)['c'],
        }
        kunjungan_list = query("""SELECT k.*,p.nama as pasien_nama,p.jenis_kelamin,p.tanggal_lahir,p.no_rm,
               cv.tekanan_darah,cv.nadi,cv.suhu,cv.saturasi_o2
            FROM kunjungan k JOIN pasien p ON k.pasien_id=p.id
            LEFT JOIN cek_vital cv ON cv.kunjungan_id=k.id
            WHERE k.tanggal=? AND k.status='cek_vital' ORDER BY k.no_antrian""", (today,))
        return render_template('dashboard_poli.html', stats=stats, kunjungan_list=kunjungan_list)
    return redirect(url_for('login'))

@app.route('/admin/list')
@login_required
@role_required('super_admin')
def admin_list():
    admins = query("SELECT * FROM admin WHERE role!='super_admin' ORDER BY created_at DESC")
    return render_template('admin_list.html', admins=admins)

@app.route('/admin/tambah', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def admin_tambah():
    if request.method == 'POST':
        username = request.form['username'].strip()
        if query("SELECT id FROM admin WHERE username=?", (username,), one=True):
            flash('Username sudah digunakan.', 'danger')
            return render_template('admin_form.html', action='tambah')
        execute("INSERT INTO admin (username,password,nama,role) VALUES (?,?,?,?)",
                (username, hash_password(request.form['password']),
                 request.form['nama'], request.form['role']))
        flash('Admin berhasil ditambahkan.', 'success')
        return redirect(url_for('admin_list'))
    return render_template('admin_form.html', action='tambah')

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def admin_edit(id):
    admin = query("SELECT * FROM admin WHERE id=?", (id,), one=True)
    if not admin:
        flash('Admin tidak ditemukan.', 'danger')
        return redirect(url_for('admin_list'))
    if request.method == 'POST':
        aktif = 1 if 'aktif' in request.form else 0
        if request.form.get('password'):
            execute("UPDATE admin SET nama=?,role=?,aktif=?,password=? WHERE id=?",
                    (request.form['nama'], request.form['role'], aktif,
                     hash_password(request.form['password']), id))
        else:
            execute("UPDATE admin SET nama=?,role=?,aktif=? WHERE id=?",
                    (request.form['nama'], request.form['role'], aktif, id))
        flash('Data admin berhasil diperbarui.', 'success')
        return redirect(url_for('admin_list'))
    return render_template('admin_form.html', action='edit', admin=admin)

@app.route('/admin/hapus/<int:id>', methods=['POST'])
@login_required
@role_required('super_admin')
def admin_hapus(id):
    execute("DELETE FROM admin WHERE id=?", (id,))
    flash('Admin berhasil dihapus.', 'success')
    return redirect(url_for('admin_list'))

@app.route('/pasien/list')
@login_required
def pasien_list():
    q = request.args.get('q', '').strip()
    if q:
        like = f'%{q}%'
        pasien = query("SELECT * FROM pasien WHERE nama LIKE ? OR nik LIKE ? OR no_rm LIKE ? ORDER BY nama", (like,like,like))
    else:
        pasien = query("SELECT * FROM pasien ORDER BY created_at DESC")
    return render_template('pasien_list.html', pasien=pasien, q=q)

@app.route('/pasien/tambah', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'loket')
def pasien_tambah():
    if request.method == 'POST':
        count = query("SELECT COUNT(*) c FROM pasien", one=True)['c'] + 1
        no_rm = f'RM{count:06d}'
        try:
            execute("INSERT INTO pasien (no_rm,nik,nama,tanggal_lahir,jenis_kelamin,alamat,no_hp) VALUES (?,?,?,?,?,?,?)",
                    (no_rm, request.form['nik'], request.form['nama'], request.form['tanggal_lahir'],
                     request.form['jenis_kelamin'], request.form.get('alamat',''), request.form.get('no_hp','')))
            flash(f'Pasien berhasil didaftarkan. No. RM: {no_rm}', 'success')
            return redirect(url_for('pasien_list'))
        except Exception as e:
            flash('Gagal mendaftarkan pasien. NIK mungkin sudah terdaftar.', 'danger')
    return render_template('pasien_form.html')

@app.route('/pasien/detail/<int:id>')
@login_required
def pasien_detail(id):
    pasien = query("SELECT * FROM pasien WHERE id=?", (id,), one=True)
    if not pasien:
        flash('Pasien tidak ditemukan.', 'danger')
        return redirect(url_for('pasien_list'))
    kunjungan = query("""SELECT k.*,rm.id as rm_id FROM kunjungan k
        LEFT JOIN rekam_medis rm ON rm.kunjungan_id=k.id
        WHERE k.pasien_id=? ORDER BY k.tanggal DESC,k.created_at DESC""", (id,))
    return render_template('pasien_detail.html', pasien=pasien, kunjungan=kunjungan)

@app.route('/rawat-jalan/daftar', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'loket')
def rawat_jalan_daftar():
    if request.method == 'POST':
        pasien_id = request.form['pasien_id']
        poli = request.form['poli']
        today = date.today().isoformat()
        count = query("SELECT COUNT(*) c FROM kunjungan WHERE tanggal=? AND poli=?", (today,poli), one=True)['c'] + 1
        no_antrian = f'{poli[:3].upper()}-{count:03d}'
        execute("INSERT INTO kunjungan (pasien_id,poli,keluhan,no_antrian,status,created_by) VALUES (?,?,?,?,?,?)",
                (pasien_id, poli, request.form.get('keluhan',''), no_antrian, 'menunggu', session['admin_id']))
        flash(f'Pasien berhasil didaftarkan. No. Antrian: {no_antrian}', 'success')
        return redirect(url_for('dashboard'))
    pasien_id_pre = request.args.get('pasien_id', '')
    return render_template('rawat_jalan_daftar.html', pasien_id_pre=pasien_id_pre)

@app.route('/cek-vital/<int:kunjungan_id>', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'cek_vital')
def cek_vital(kunjungan_id):
    kunjungan = query("""SELECT k.*,p.nama as pasien_nama,p.jenis_kelamin,p.tanggal_lahir,p.no_rm
        FROM kunjungan k JOIN pasien p ON k.pasien_id=p.id WHERE k.id=?""", (kunjungan_id,), one=True)
    if not kunjungan:
        flash('Kunjungan tidak ditemukan.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        def iv(f): v=request.form.get(f,'').strip(); return v if v else None
        execute("""INSERT INTO cek_vital
            (kunjungan_id,tekanan_darah,nadi,suhu,berat_badan,tinggi_badan,saturasi_o2,catatan,created_by)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (kunjungan_id,iv('tekanan_darah'),iv('nadi'),iv('suhu'),
             iv('berat_badan'),iv('tinggi_badan'),iv('saturasi_o2'),iv('catatan'),session['admin_id']))
        execute("UPDATE kunjungan SET status='cek_vital' WHERE id=?", (kunjungan_id,))
        flash('Data cek vital berhasil disimpan. Pasien dikirim ke Poli.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('cek_vital_form.html', kunjungan=kunjungan)

@app.route('/rekam-medis/<int:kunjungan_id>', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'poli')
def rekam_medis(kunjungan_id):
    kunjungan = query("""SELECT k.*,p.nama as pasien_nama,p.jenis_kelamin,p.tanggal_lahir,p.no_rm,p.nik
        FROM kunjungan k JOIN pasien p ON k.pasien_id=p.id WHERE k.id=?""", (kunjungan_id,), one=True)
    if not kunjungan:
        flash('Kunjungan tidak ditemukan.', 'danger')
        return redirect(url_for('dashboard'))
    vital = query("SELECT * FROM cek_vital WHERE kunjungan_id=?", (kunjungan_id,), one=True)
    rm    = query("SELECT * FROM rekam_medis WHERE kunjungan_id=?", (kunjungan_id,), one=True)

    if request.method == 'POST':
        vals = tuple(request.form.get(f,'') for f in ('anamnesis','pemeriksaan_fisik','diagnosis','tindakan','resep','catatan'))
        if rm:
            execute("""UPDATE rekam_medis SET anamnesis=?,pemeriksaan_fisik=?,diagnosis=?,
                tindakan=?,resep=?,catatan=?,updated_at=datetime('now','localtime')
                WHERE kunjungan_id=?""", vals+(kunjungan_id,))
        else:
            execute("""INSERT INTO rekam_medis
                (kunjungan_id,anamnesis,pemeriksaan_fisik,diagnosis,tindakan,resep,catatan,created_by)
                VALUES (?,?,?,?,?,?,?,?)""", (kunjungan_id,)+vals+(session['admin_id'],))
        new_status = 'selesai' if 'selesai' in request.form else 'poli'
        execute("UPDATE kunjungan SET status=? WHERE id=?", (new_status, kunjungan_id))
        flash('Rekam medis berhasil disimpan.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('rekam_medis_form.html', kunjungan=kunjungan, vital=vital, rm=rm)

@app.route('/arsip-rm')
@login_required
@role_required('super_admin', 'poli')
def arsip_rm():
    q = request.args.get('q','').strip()
    tanggal = request.args.get('tanggal','').strip()
    tahun = request.args.get('tahun','').strip()

    sql = """SELECT rm.*,k.tanggal,k.poli,k.no_antrian,
                    p.nama as pasien_nama,p.no_rm,
                    cv.tekanan_darah,cv.nadi,cv.suhu,cv.saturasi_o2,
                    cv.berat_badan,cv.tinggi_badan,cv.catatan as vital_catatan
        FROM rekam_medis rm
        JOIN kunjungan k ON rm.kunjungan_id=k.id
        JOIN pasien p ON k.pasien_id=p.id
        LEFT JOIN cek_vital cv ON cv.kunjungan_id=k.id
        WHERE 1=1"""
    args = []
    if q:
        sql += " AND (p.nama LIKE ? OR p.no_rm LIKE ?)"
        like = f'%{q}%'; args += [like, like]
    if tanggal:
        sql += " AND k.tanggal=?"; args.append(tanggal)
    if tahun:
        sql += " AND strftime('%Y', k.tanggal)=?"; args.append(tahun)
    sql += " ORDER BY rm.created_at DESC"

    rm_rows = query(sql, args)

    rm_list = []
    for row in rm_rows:
        r = dict(row)
        if r.get('tekanan_darah') or r.get('nadi') or r.get('suhu') or \
           r.get('berat_badan') or r.get('tinggi_badan') or r.get('saturasi_o2'):
            r['vital'] = {
                'tekanan_darah': r.get('tekanan_darah'),
                'nadi':          r.get('nadi'),
                'suhu':          r.get('suhu'),
                'saturasi_o2':   r.get('saturasi_o2'),
                'berat_badan':   r.get('berat_badan'),
                'tinggi_badan':  r.get('tinggi_badan'),
                'catatan':       r.get('vital_catatan'),
            }
        else:
            r['vital'] = None
        rm_list.append(r)

    tahun_list = [row[0] for row in get_db().execute(
        "SELECT DISTINCT strftime('%Y', k.tanggal) FROM kunjungan k "
        "JOIN rekam_medis rm ON rm.kunjungan_id=k.id ORDER BY 1 DESC"
    ).fetchall()]

    return render_template('arsip_rm.html', rm_list=rm_list, q=q,
                           tanggal=tanggal, tahun=tahun, tahun_list=tahun_list)

# ── API: arsip rekam medis per pasien (untuk shortcut di form rekam medis) ──
@app.route('/api/arsip-rm/<no_rm>')
@login_required
@role_required('super_admin', 'poli')
def api_arsip_rm(no_rm):
    rows = query("""
        SELECT
            rm.id,
            rm.anamnesis,
            rm.pemeriksaan_fisik,
            rm.diagnosis,
            rm.tindakan,
            rm.resep,
            rm.catatan,
            k.poli,
            k.tanggal
        FROM rekam_medis rm
        JOIN kunjungan k ON rm.kunjungan_id = k.id
        JOIN pasien p ON k.pasien_id = p.id
        WHERE p.no_rm = ?
        ORDER BY k.tanggal DESC, rm.created_at DESC
    """, (no_rm,))
    return jsonify([dict(r) for r in rows])

@app.route('/api/pasien/search')
@login_required
def api_pasien_search():
    q = request.args.get('q','').strip()
    like = f'%{q}%'
    rows = query("SELECT id,nama,no_rm,nik,tanggal_lahir FROM pasien WHERE nama LIKE ? OR nik LIKE ? OR no_rm LIKE ? LIMIT 10",
                 (like,like,like))
    return jsonify([dict(r) for r in rows])

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  Sistem Rawat Jalan Puskesmas")
    print("  Buka: http://localhost:5000")
    print("="*50)
    print("  superadmin / admin123")
    print("  loket1     / loket123")
    print("  cekvi1     / cekvi123")
    print("  dokter1    / dokter123")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)