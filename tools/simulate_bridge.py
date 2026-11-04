"""
tools/simulate_bridge.py  —  Gia lap 2 camera chan cau (khong can camera that)
==============================================================================
Gui cac luot qua vach toi POST /bridge/crossing nhu camera_bridge.py that,
de test bien num1, num2, onbridge, dem va trang "Luot qua cau".

CHAY (backend phai chay truoc, tu THU MUC GOC Cap2/):
    python tools/simulate_bridge.py                 # kich ban mau co giai thich
    python tools/simulate_bridge.py --random 200    # 200 luot ngau nhien
"""

import argparse
import os
import random
import time

import requests

API_BASE = os.environ.get("SMARTCAU_API", "http://127.0.0.1:8000")
API_KEY = os.environ.get("SMARTCAU_API_KEY", "")
HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

# (camera, huong, giai thich)
SCENARIO = [
    (1, "in", "Khach A vao o chan cau 1"),
    (1, "in", "Khach B vao o chan cau 1"),
    (2, "in", "Khach C vao o chan cau 2"),
    (2, "out", "Khach A di het cau, ra o chan cau 2 (num2 thanh 0)"),
    (2, "out", "Khach B cung ra o chan cau 2 (num2 am)"),
    (1, "out", "Khach C quay lai, ra o chan cau 1 -> cau trong -> reset num1, num2"),
]


def send(cam, direction):
    r = requests.post(f"{API_BASE}/bridge/crossing", headers=HEADERS, timeout=3,
                      json={"camera_id": cam, "direction": direction})
    r.raise_for_status()
    return r.json()


def show(s, note=""):
    flag = "  << RESET" if s.get("reset") else ""
    print(f"num1={s['num1']:>3} | num2={s['num2']:>3} | onbridge={s['onbridge']:>3} | "
          f"dem={s['dem']:>4}  {note}{flag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--random", type=int, default=0, help="So luot ngau nhien can gui")
    ap.add_argument("--delay", type=float, default=0.3, help="Giay nghi giua 2 luot")
    args = ap.parse_args()

    if args.random:
        onbridge = 0
        for _ in range(args.random):
            # cau cang dong thi cang de co nguoi ra
            p_in = 0.75 if onbridge < 10 else 0.45
            direction = "in" if random.random() < p_in else "out"
            s = send(random.choice((1, 2)), direction)
            onbridge = s["onbridge"]
            show(s)
            time.sleep(args.delay)
        return

    for cam, direction, note in SCENARIO:
        show(send(cam, direction), f"cam{cam} {direction:<3} : {note}")
        time.sleep(args.delay)


if __name__ == "__main__":
    main()
