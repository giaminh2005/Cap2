"""
tools/seed_demo_data.py  —  Nap du lieu mau vao backend (khong can camera)
==========================================================================
Dung khi Hoan / Khanh lam giao dien ma may chua cai YOLO/DeepFace hoac
khong muon bat webcam. Script goi CHINH cac API that cua backend, nen du
lieu di dung duong nhu camera that.

CHAY (backend phai dang chay o terminal khac):
    python tools/seed_demo_data.py            # 120 luot vao, mac dinh
    python tools/seed_demo_data.py --n 400
"""

import argparse
import os
import random

import requests

API = os.environ.get("SMARTCAU_API", "http://127.0.0.1:8000")
KEY = os.environ.get("SMARTCAU_API_KEY", "")
HEADERS = {"X-API-Key": KEY} if KEY else {}

AGES = [("13-17", 15), ("18-24", 21), ("25-34", 29), ("35-44", 39),
        ("45-54", 49), ("55-64", 58), ("70+", 72)]


def post(path, payload=None):
    r = requests.post(f"{API}{path}", json=payload or {}, headers=HEADERS, timeout=5)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120, help="so luot khach vao")
    args = ap.parse_args()

    requests.get(f"{API}/health", timeout=3).raise_for_status()

    on_bridge = 0
    for i in range(args.n):
        age_range, age = random.choice(AGES)
        post("/entry", {"track_id": i + 1, "gender": random.choice(["Man", "Woman"]),
                        "age_range": age_range, "age": age + random.randint(-2, 2)})
        on_bridge += 1
        if on_bridge > 12 and random.random() < 0.7:
            post("/exit")
            on_bridge -= 1
        if i % 10 == 0:
            status = "CRITICAL" if on_bridge > 20 else "WARNING" if on_bridge >= 15 else "OK"
            post("/occupancy", {"count": on_bridge, "status": status})

    post("/system_events", {"event_type": "WARNING", "count": 16, "message": "Cau sap day (Vang)"})
    post("/system_events", {"event_type": "CRITICAL_ALERT", "count": 22, "message": "Qua tai (Do) > 15 giay"})
    post("/system_events", {"event_type": "GROUP_DETECTED", "count": 14, "message": "Doan 14 nguoi dang toi dau cau"})
    print(f"Da nap {args.n} luot vao + 3 su co vao {API}. Mo trang web de xem.")


if __name__ == "__main__":
    main()
