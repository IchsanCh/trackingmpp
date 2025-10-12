from flask import Flask, request, jsonify
import requests
import urllib3
from bs4 import BeautifulSoup
import re
from functools import wraps

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

API_TOKEN = "tokentrackingmpp20251110"
REQUEST_TIMEOUT = (10, 60)

def require_auth(f):
    """Decorator untuk validasi authorization token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != API_TOKEN:
            return jsonify({
                'success': False,
                'message': 'Unauthorized: Invalid or missing authorization token'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def get_csrf_token(html_text):
    """Extract CSRF token dari HTML"""
    token_match = re.search(r'name="_token" value="([^"]+)"', html_text)
    if not token_match:
        token_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html_text)
    return token_match.group(1) if token_match else None

def login_mpp(base_url, username, password, lokasi="1"):
    """Login ke MPP Digital dan return session + csrf_token"""
    session = requests.Session()
    
    try:
        # Get login page untuk ambil CSRF token
        login_page = session.get(f"{base_url}/sim", verify=False, timeout=REQUEST_TIMEOUT)
        csrf_token = get_csrf_token(login_page.text)
        
        if not csrf_token:
            return None, None, "CSRF token tidak ditemukan"
        
        login_url = f"{base_url}/sim/login"
        payload = {
            "_token": csrf_token,
            "db_name": lokasi,
            "username": username,
            "password": password,
        }
        
        response = session.post(login_url, data=payload, verify=False, timeout=REQUEST_TIMEOUT)
        
        if "Sim" not in response.text and not response.url.endswith("/sim"):
            return None, None, "Login gagal: Username atau password salah"
        
        return session, csrf_token, None
        
    except Exception as e:
        return None, None, f"Error saat login: {str(e)}"

def extract_pdf_from_detail(session, detail_url):
    """Extract PDF link dari halaman detail"""
    try:
        response = session.get(detail_url, verify=False, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        
        embed = soup.find("embed", {"type": "application/pdf"})
        if embed and embed.get("src"):
            return embed.get("src")
        
        pdf_match = re.search(r'<embed[^>]+src=["\']([^"\']+\.pdf[^"\']*)["\']', response.text, re.IGNORECASE)
        if pdf_match:
            return pdf_match.group(1)
        
        return None
    except Exception as e:
        print(f"Error extract PDF: {str(e)}")
        return None

def get_alasan_tolak(session, base_url, nama_pemohon):
    """Get alasan tolak dari halaman permohonan dengan status=tolak"""
    try:
        search_url = f"{base_url}/sim/permohonan"
        params = {
            "cari": nama_pemohon,
            "status": "tolak"
        }
        
        response = session.get(search_url, params=params, verify=False, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        
        table = soup.find("table", {"id": "tabel1"})
        if not table:
            return None
        
        tbody = table.find("tbody")
        if not tbody:
            return None
        
        rows = tbody.find_all("tr")
        
        if rows:
            cols = rows[0].find_all("td")
            if len(cols) >= 10:
                alasan_tolak = cols[9].get_text(strip=True)
                return alasan_tolak if alasan_tolak else None
            elif len(cols) >= 9:
                alasan_tolak = cols[8].get_text(strip=True)
                if alasan_tolak and alasan_tolak.upper() != "DITOLAK":
                    return alasan_tolak
        
        return None
        
    except Exception as e:
        print(f"Error get alasan tolak: {str(e)}")
        return None

def search_pemohon(session, base_url, nama_pemohon):
    """Search pemohon berdasarkan nama dan return list hasil"""
    try:
        search_url = f"{base_url}/sim/permohonan"
        params = {
            "cari": nama_pemohon,
            "status": "all"
        }
        
        response = session.get(search_url, params=params, verify=False, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        
        table = soup.find("table", {"id": "tabel1"})
        if not table:
            return []
        
        tbody = table.find("tbody")
        if not tbody:
            return []
        
        rows = tbody.find_all("tr")
        results = []
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 9:
                continue
            try:
                detail_link = None
                first_col = cols[0]
                a_tag = first_col.find("a", href=True)
                if a_tag:
                    detail_href = a_tag.get("href")
                    if detail_href and not detail_href.startswith('http'):
                        detail_link = f"{base_url}{detail_href}" if detail_href.startswith('/') else f"{base_url}/{detail_href}"
                    else:
                        detail_link = detail_href
                
                no_permohonan = cols[1].get_text(strip=True)
                nama_izin = cols[2].get_text(strip=True)
                nama = cols[4].get_text(strip=True)
                
                hp_text = cols[6].get_text(strip=True)
                hp_match = re.search(r'(\+?\d[\d\s\-().]{4,})', hp_text)
                nomor_hp = re.sub(r'\D', '', hp_match.group(1)) if hp_match else hp_text
                
                tgl_pengajuan = cols[7].get_text(strip=True)
                tahapan = cols[8].get_text(strip=True)
                
                link_izin = None
                alasan_tolak = None
                
                if tahapan and tahapan.upper().strip() == "SK DITERBITKAN" and detail_link:
                    print(f"[INFO] Tahapan SK DITERBITKAN detected for {nama}, fetching PDF...")
                    link_izin = extract_pdf_from_detail(session, detail_link)
                    if link_izin:
                        print(f"[SUCCESS] PDF found: {link_izin}")
                    else:
                        print(f"[WARNING] PDF not found in detail page")
                
                if tahapan and tahapan.upper().strip() == "DITOLAK":
                    print(f"[INFO] Tahapan DITOLAK detected for {nama}, fetching alasan tolak...")
                    alasan_tolak = get_alasan_tolak(session, base_url, nama)
                    if alasan_tolak:
                        print(f"[SUCCESS] Alasan tolak found: {alasan_tolak}")
                    else:
                        print(f"[WARNING] Alasan tolak not found")
                
                item = {
                    "no_permohonan": no_permohonan,
                    "nama_izin": nama_izin,
                    "nama": nama,
                    "nomor_hp": nomor_hp,
                    "tgl_pengajuan": tgl_pengajuan,
                    "tahapan": tahapan,
                    "detail_link": detail_link,
                    "link_izin": link_izin,
                    "alasan_tolak": alasan_tolak
                }
                
                results.append(item)
                
            except Exception as e:
                continue
        
        return results
        
    except Exception as e:
        raise Exception(f"Error saat search: {str(e)}")

def get_detail_pemohon(session, detail_url):
    """Get detail pemohon dari halaman detail (termasuk PDF link jika ada)"""
    try:
        response = session.get(detail_url, verify=False, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        
        detail_data = {}
        
        embed = soup.find("embed", {"type": "application/pdf"})
        if embed and embed.get("src"):
            detail_data["pdf_link"] = embed.get("src")
        else:
            pdf_match = re.search(r'<embed[^>]+src=["\']([^"\']+\.pdf[^"\']*)["\']', response.text, re.IGNORECASE)
            if pdf_match:
                detail_data["pdf_link"] = pdf_match.group(1)
        
        return detail_data
        
    except Exception as e:
        return {"error": f"Error saat get detail: {str(e)}"}

@app.route('/api/tracking/search', methods=['POST'], strict_slashes=False)
@require_auth
def tracking_search():
    """
    API endpoint untuk tracking/search pemohon
    
    Body request (JSON):
    {
        "base_url": "https://admin.mppdigital.go.id",
        "username": "username_mpp",
        "password": "password_mpp",
        "lokasi": "1",
        "nama_pemohon": "nama yang dicari"
    }
    """
    try:
        data = request.get_json()
        
        required_fields = ['base_url', 'username', 'password', 'nama_pemohon']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        base_url = data['base_url'].rstrip('/')
        username = data['username']
        password = data['password']
        lokasi = data.get('lokasi', '1')
        nama_pemohon = data['nama_pemohon']
        
        session, csrf_token, error = login_mpp(base_url, username, password, lokasi)
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 401
        
        results = search_pemohon(session, base_url, nama_pemohon)
        
        return jsonify({
            'success': True,
            'message': f'Ditemukan {len(results)} hasil untuk "{nama_pemohon}"',
            'data': results,
            'total': len(results)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/tracking/detail', methods=['POST'], strict_slashes=False)
@require_auth
def tracking_detail():
    """
    API endpoint untuk get detail pemohon dari link detail
    
    Body request (JSON):
    {
        "base_url": "https://admin.mppdigital.go.id",
        "username": "username_mpp",
        "password": "password_mpp",
        "lokasi": "1",
        "detail_link": "https://admin.mppdigital.go.id/sim/permohonan/detail/123"
    }
    """
    try:
        data = request.get_json()
        
        required_fields = ['base_url', 'username', 'password', 'detail_link']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        base_url = data['base_url'].rstrip('/')
        username = data['username']
        password = data['password']
        lokasi = data.get('lokasi', '1')
        detail_link = data['detail_link']
        
        session, csrf_token, error = login_mpp(base_url, username, password, lokasi)
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 401
        
        detail_data = get_detail_pemohon(session, detail_link)
        
        return jsonify({
            'success': True,
            'message': 'Detail pemohon berhasil diambil',
            'data': detail_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/tracking/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'MPP Digital Tracking API is running',
        'version': '1.0.0'
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=23459)