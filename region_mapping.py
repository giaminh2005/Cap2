"""
region_mapping.py
--------------------
Module DUNG CHUNG cho Phase 3 (nang cap): quy doi ve 5 NHOM KHU VUC rong,
dung o CA 2 noi: (1) du lieu MO PHONG cho dashboard (data_simulator.py /
generate_dashboard.py) va (2) uoc luong khu vuc TRUC TIEP tu camera qua
DeepFace (demographics_engine.py) - de 2 ben dung CHUNG 1 bo nhan, bao cao
khong bi lech thuat ngu.

=== GIOI HAN CO CHU DICH - DOC KY TRUOC KHI DUNG ===
Day la nang cap CO CHU DICH them tinh nang "phan nhom khu vuc" (KHONG PHAI
"nhan dien chung toc/quoc tich") sau khi ban dau du an co chu dich KHONG
lam tinh nang nay (xem docstring dau file age_gender_estimator.py, trich
dan Luat Bao ve du lieu ca nhan 2025 - Luat so 91/2025/QH15 - va Nghi
dinh 356/2025/NĐ-CP, hieu luc tu 1/1/2026). Khi bat tinh nang nay (xem ENABLE_REGION_
ESTIMATION trong demographics_engine.py), PHAI tuan thu dung 3 nguyen tac
nhom da thong nhat:
  1. CHI phan nhom KHU VUC RONG (5 nhom ben duoi), KHONG suy dien quoc
     tich/chung toc cu the cho tung nguoi.
  2. CHI luu du lieu TONG HOP (vd "14h-15h ngay X co ~12 luot thuoc nhom
     Dong A"), TUYET DOI KHONG gan nhan khu vuc vao ho so ca nhan/track_id
     cu the (xem api_server.py - bang RegionStat la bang TONG HOP THEO
     GIO, khong co cot lien ket toi 1 nguoi/khuon mat nao).
  3. LUON hien disclaimer ro rang (xem DISCLAIMER_VI ben duoi) bat cu dau
     con so nay duoc hien thi - vi day la UOC LUONG THO tu dac diem guong
     mat qua model AI pretrained, KHONG PHAI du lieu quoc tich chinh xac.

HAN CHE KY THUAT QUAN TRONG (phai neu trong bao cao neu dung tinh nang
nay): DeepFace chi phan loai ra 1 nhom "asian" duy nhat cho CA chau A -
KHONG the tu phan biet duoc khach Viet Nam (noi dia) voi khach Han Quoc/
Nhat Ban/Trung Quoc chi tu guong mat. Vi vay nhom "Dong A / Noi dia" ben
duoi la 1 nhom GOP, khong tach duoc "noi dia" that su - muon tach chinh
xac van CAN kenh du lieu bo sung (QR check-in / dang ky doan) nhu thiet
ke GOC cua du an da neu, khong the thay the hoan toan bang camera.
"""

from typing import Dict, Optional, Tuple

# Thu tu hien thi co dinh, dung chung cho moi bieu do/bang de khong bi dao lon.
REGION_ORDER = [
    "Dong A / Noi dia",
    "Phuong Tay",
    "Nam A",
    "Khac",
]

REGION_LABEL_DISPLAY = {
    "Dong A / Noi dia": "Đông Á / Nội địa",
    "Phuong Tay": "Phương Tây",
    "Nam A": "Nam Á",
    "Khac": "Khác",
}

DISCLAIMER_VI = (
    "Nhom khu vuc o day la UOC LUONG THO tu dac diem guong mat qua mo hinh AI "
    "(hoac, trong dashboard nay, tu du lieu MO PHONG) - KHONG PHAI du lieu quoc "
    "tich chinh xac tung nguoi, va KHONG duoc luu/gan cho ho so ca nhan nao. Chi "
    "dung de thong ke xu huong tong hop phuc vu marketing, khong dung lam can cu "
    "xac dinh danh tinh/quoc tich 1 ca nhan cu the."
)

# --- (1) Du lieu MO PHONG: quy doi tu "quoc gia/xuat xu" (data_simulator.py) ---
_NATIONALITY_TO_REGION = {
    "Viet Nam (noi dia)": "Dong A / Noi dia",
    "Han Quoc": "Dong A / Noi dia",
    "Trung Quoc": "Dong A / Noi dia",
    "Dai Loan": "Dong A / Noi dia",
    "Nhat Ban": "Dong A / Noi dia",
    "Phap": "Phuong Tay",
    "My": "Phuong Tay",
    "Duc": "Phuong Tay",
    "Uc": "Phuong Tay",
    "Anh": "Phuong Tay",
    "Thai Lan": "Khac",
    "An Do": "Nam A",
}


def nationality_to_region(nationality: str) -> str:
    """Quy doi 1 nhan "quoc gia/xuat xu" (du lieu mo phong) sang 1 trong 4
    nhom khu vuc. Khong tim thay -> "Khac"."""
    return _NATIONALITY_TO_REGION.get(nationality, "Khac")


# --- (2) Camera THAT: quy doi tu ket qua DeepFace action "race" ---
# DeepFace tra ve xac suat cho 6 nhan: asian, indian, black, white,
# middle eastern, latino hispanic. Gop lai thanh 4 nhom rong o tren.
_DEEPFACE_RACE_TO_REGION = {
    "asian": "Dong A / Noi dia",
    "indian": "Nam A",
    "white": "Phuong Tay",
    "latino hispanic": "Phuong Tay",
    "middle eastern": "Khac",
    "black": "Khac",
}


def classify_region_from_deepface_race(race_probs: Optional[Dict[str, float]]) -> Tuple[Optional[str], float]:
    """Nhan dict xac suat "race" tu DeepFace (vd {"asian": 72.1, "white": 10.3, ...})
    va tra ve (nhom_khu_vuc, do_tin_cay_0_den_1). Tra ve (None, 0.0) neu
    thieu du lieu. KHONG tu goi DeepFace o day - ham nay CHI xu ly ket qua
    da co san, de demographics_engine.py quyet dinh KHI NAO (neu co) can
    goi action "race" (tinh nang nay mac dinh TAT, xem demographics_engine.py)."""
    if not race_probs:
        return None, 0.0
    # Gop xac suat cac nhan DeepFace vao dung 4 nhom roi lay nhom cao nhat,
    # thay vi chi lay nhan "thang" dau tien cua DeepFace (chinh xac hon vi
    # co nhieu nhan DeepFace cung thuoc 1 nhom, vd white + latino hispanic
    # deu la "Phuong Tay" - gop xac suat lai truoc khi so sanh).
    grouped: Dict[str, float] = {}
    total = 0.0
    for label, prob in race_probs.items():
        region = _DEEPFACE_RACE_TO_REGION.get(str(label).lower())
        if region is None:
            continue
        grouped[region] = grouped.get(region, 0.0) + float(prob)
        total += float(prob)
    if not grouped or total <= 0:
        return None, 0.0
    best_region = max(grouped, key=grouped.get)
    confidence = grouped[best_region] / total
    return best_region, confidence
