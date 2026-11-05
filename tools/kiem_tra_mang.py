"""
tools/kiem_tra_mang.py  —  Kiem tra ket noi khi chay NHIEU MAY (may chu + may camera + may xem)
================================================================================================
Tren MAY CHU (chay backend):     python tools/kiem_tra_mang.py
    -> in dia chi IP trong mang LAN, kiem tra backend / web da mo cho may khac chua,
       in san lenh cho may camera va dia chi cho may xem.
Tren MAY CAMERA / MAY XEM:        python tools/kiem_tra_mang.py http://192.168.1.10:8000
    -> thu ket noi toi may chu, do do tre, bao loi cu the neu khong duoc.
Chi dung thu vien chuan Python (khong can cai them).
"""

import json
import socket
import sys
import time
import urllib.error
import urllib.request


def lan_ips():
    ips = set()
    try:                                    # IP dung de ra mang (khong gui goi tin that)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def port_open(host, port, timeout=1.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def get_json(url, timeout=4):
    t0 = time.time()
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8")), (time.time() - t0) * 1000


def server_mode():
    ips = lan_ips()
    print("=== MÁY CHỦ ===")
    print(f"Tên máy: {socket.gethostname()}")
    if not ips:
        print("Không tìm thấy IP mạng LAN. Máy đã kết nối Wi-Fi / mạng dây chưa?")
        return 1
    print("Địa chỉ IP trong mạng LAN: " + ", ".join(ips))
    ok_all = True
    for ip in ips:
        b, w = port_open(ip, 8000), port_open(ip, 8501)
        print(f"  {ip}:8000 backend  -> {'MỞ' if b else 'CHƯA mở'}   ·   {ip}:8501 web -> {'MỞ' if w else 'CHƯA mở'}")
        ok_all &= b
    if not ok_all:
        print("\nBackend chưa mở cho máy khác. Chạy backend bằng:\n"
              "    uvicorn backend.main:app --host 0.0.0.0 --port 8000\n"
              "và mở tường lửa Windows (PowerShell chạy Run as Administrator):\n"
              '    New-NetFirewallRule -DisplayName "SmartCau 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow\n'
              '    New-NetFirewallRule -DisplayName "SmartCau 8501" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow')
    ip = ips[0]
    print(f"""
=== DÙNG CHO CÁC MÁY KHÁC (cùng mạng) ===
Máy camera chân cầu 1:  python ai_engine/camera_bridge.py --camera-id 1 --source 0 --demographics --api http://{ip}:8000
Máy camera chân cầu 2:  python ai_engine/camera_bridge.py --camera-id 2 --source 0 --demographics --api http://{ip}:8000
Máy xem web quản lý:    mở trình duyệt  http://{ip}:8501
Bảng LED đầu cầu 1:     mở Chrome/Edge  http://{ip}:8000/led/?dau=1   rồi nhấn F11
Bảng LED đầu cầu 2:     mở Chrome/Edge  http://{ip}:8000/led/?dau=2
Xem song song 2 LED:    http://{ip}:8000/led/hai-man-hinh.html
Kiểm tra từ máy khác:   python tools/kiem_tra_mang.py http://{ip}:8000""")
    return 0


def client_mode(base):
    base = base.rstrip("/")
    if not base.startswith("http"):
        base = "http://" + base
    host = base.split("//", 1)[1].split("/")[0].split(":")[0]
    port = int(base.rsplit(":", 1)[1].split("/")[0]) if base.count(":") >= 2 else 80
    print(f"=== KIỂM TRA KẾT NỐI TỚI {base} ===")
    print(f"Máy này: {socket.gethostname()} · IP: {', '.join(lan_ips()) or '?'}")
    if not port_open(host, port, timeout=3):
        print(f"✗ Không mở được cổng {port} trên {host}.\n"
              "  - Hai máy có cùng một mạng Wi-Fi không? (mạng trường / khách sạn thường CHẶN máy nói chuyện với nhau,\n"
              "    hãy dùng điểm phát Wi-Fi từ điện thoại)\n"
              "  - Máy chủ đã chạy: uvicorn backend.main:app --host 0.0.0.0 --port 8000 ?\n"
              "  - Tường lửa máy chủ đã mở cổng 8000 chưa? (chạy tools/kiem_tra_mang.py trên máy chủ để xem lệnh)")
        return 1
    try:
        h, ms = get_json(base + "/health")
        print(f"✓ Backend trả lời sau {ms:.0f} ms" + (" · camera cần --api-key" if h.get("api_key_required") else ""))
        d, _ = get_json(base + "/display/state")
        print(f"✓ Số liệu: {d['onbridge']}/{d['capacity']} người trên cầu, mức {d['level']}, "
              f"{d['dem']} lượt hôm nay, giờ máy chủ {d['server_time'][11:16]}")
        cams, _ = get_json(base + "/bridge/cameras")
        for c in cams:
            print(f"  Camera {c['camera_id']}: {'đang chạy trên máy ' + (c.get('machine') or '?') if c['online'] else 'chưa chạy'}")
        print(f"✓ Web quản lý: {'mở được' if port_open(host, 8501) else 'CHƯA mở'} tại http://{host}:8501")
        print(f"✓ Bảng LED: http://{host}:{port}/led/?dau=1 và ?dau=2 (song song: /led/hai-man-hinh.html)")
        return 0
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        print(f"✗ Cổng mở nhưng không phải backend SmartCau hoặc bị lỗi: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(client_mode(sys.argv[1]) if len(sys.argv) > 1 else server_mode())
