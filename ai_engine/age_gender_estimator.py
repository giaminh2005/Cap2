"""
age_gender_estimator.py
-------------------------
Uoc luong TUOI (theo KHOANG, khong doan so le) va GIOI TINH tu anh co
khuon mat, dung model pretrained (khong tu train) qua thu vien DeepFace.

QUAN TRONG - GIOI HAN CO CHU DICH: module nay CHI uoc luong tuoi/gioi tinh,
KHONG phan loai "chung toc / nguon goc / Latin - Chau A - Chau Phi..." du
DeepFace co ho tro tinh nang do (action "race"). Ly do KHONG lam:
  1. Khong co co so khoa hoc: "chung toc" hay "quoc tich" khong phai dac
     diem sinh trac hoc co the doc tu khuon mat/kieu toc mot cach dang tin
     cay - vi du 1 nguoi goc Latin, goc A, hay goc Phi deu co the mang bat
     ky quoc tich nao, va nguoc lai.
  2. Day la du lieu ca nhan NHAY CAM: phan loai chung toc/sac toc tu khuon
     mat thuoc nhom du lieu dac biet nhay cam theo Luat Bao ve du lieu ca
     nhan 2025 (Luat so 91/2025/QH15) va Nghi dinh 356/2025/NĐ-CP (hieu
     luc tu 1/1/2026) ve bao ve du lieu ca nhan (VN) va hau het khung phap
     ly bao ve du lieu ca nhan khac (GDPR...). Trien khai tinh nang nay se bien du an tu 1 he
     thong dem nguoi/canh bao an toan thanh 1 he thong "profiling" chung
     toc - rui ro phap ly va dao duc rat lon, khong phu hop de dua vao do
     an mon hoc.
  3. Da co giai phap thay the HOP LE va chinh xac hon trong ke hoach du an:
     lay du lieu quoc gia/xuat xu qua kenh check-in so (QR/dang ky doan) do
     KHACH TU KHAI, khong suy dien tu guong mat. Phan nay da duoc ghi nhan
     la 1 gioi han/rui ro trong tai lieu du an (Module rui ro).
Neu giang vien hoi vi sao khong lam nhan dien "quoc tich/chung toc" bang
camera - day chinh la cau tra loi (co the dua thang vao bao cao).

=== SUA LOI NHAN DIEN SAI (ban truoc hay bi doan sai gioi tinh/tuoi) ===
Nguyen nhan that su KHONG phai do "khong lay du vung toc" - ma la vi
DeepFace duoc goi voi enforce_detection=False: khi no KHONG tim thay
khuon mat that trong anh dua vao, no VAN tra ve mot ket qua "gia" (vung
= CA buc anh) va van doan tuoi/gioi tinh tu bat ky pixel nao co trong do
(co the la ao, toc, nen...) thay vi tu mat that - day la ly do ket qua
sai lech hoan toan. Ban sua nay LOC BO cac ket qua "gia" do (xem
_is_fake_full_image_region ben duoi) thay vi co gang tu cat/mo rong vung
mat bang tay (cach cu de lam nhieu them vi cat sai ty le DeepFace can).

Cai dat (chay tren MAY CUA BAN co Internet, khac moi truong build demo):
    pip install deepface tf-keras

Lan dau chay se tu dong tai model pretrained (~100-200MB), can Internet,
co the mat vai phut. Tu lan sau se nhanh vi model da luu cache.

Cach dung:
    python3 age_gender_estimator.py <duong_dan_anh>

=== SUA LOI LAN 4 (van hien "dang xac dinh... 0/3" mai du mat RO RANG
trong khung hinh - vd deo kinh, cui dau nhe, tay cham gan mat/cam) ===
Nguyen nhan: backend nhan dien mat MAC DINH cua ban truoc la "opencv"
(Haar Cascade - thuat toan co, nhe nhung RAT YEU) - de bo sot mat that
khi mat khong nhin THANG, hoi nghieng, bi che 1 phan (tay, toc), hoac
deo kinh (anh phan quang lam sai lech vung mat). Khi khong tim thay mat,
DeepFace tra ve ket qua "gia" (bi loc bo o _is_fake_full_image_region
ben duoi) -> gender luon None -> KHONG BAO GIO co phieu bau nao duoc
cong vao TemporalVoter (xem demographics_engine.py) -> man hinh ket
qua la "dang xac dinh... 0/3" MAI MAI du nguoi dung dung yen truoc
camera rat lau (khac voi truong hop binh thuong la "dang xac dinh...
1/3", "2/3" - co tang dan).
Sua: doi backend mac dinh sang "yunet" (OpenCV FaceDetectorYN - mot
model nhan dien mat bang deep learning NHE, van chay realtime tren CPU
binh thuong, nhung chinh xac hon Haar Cascade RAT NHIEU voi goc mat
nghieng/bi che 1 phan/deo kinh). Lan dau chay se tu tai them 1 model
nho (~1-2MB) cho backend nay, cung Internet nhu cac model khac.
"""

from typing import List, Dict, Optional, Tuple
import cv2

# Co bao "backend nhan dien mat chinh ('yunet') da bi loi, dang dung
# fallback 'opencv'" - xem giai thich trong estimate_age_gender() ben
# duoi. Bat dau la False (dung backend chinh binh thuong).
_BACKEND_FALLBACK_TO_OPENCV = False

# Nguong nhan ID(1 tuoi) den 70+ theo yeu cau: tra ve KHOANG tuoi thay vi
# 1 con so chinh xac (vi 1 con so le tu 1 frame webcam la khong dang tin).
_AGE_BUCKETS = [
    (0, 5, "0-5"),
    (6, 12, "6-12"),
    (13, 17, "13-17"),
    (18, 24, "18-24"),
    (25, 34, "25-34"),
    (35, 44, "35-44"),
    (45, 54, "45-54"),
    (55, 64, "55-64"),
    (65, 69, "65-69"),
]


def age_to_range(age: Optional[int]) -> str:
    """Doi 1 con so tuoi tho (khong dang tin de dung truc tiep) thanh 1
    KHOANG tuoi de hien thi, phu he 0 -> 70+."""
    if age is None or age < 0:
        return "Khong ro"
    if age >= 70:
        return "70+"
    for lo, hi, label in _AGE_BUCKETS:
        if lo <= age <= hi:
            return label
    return "Khong ro"


def _is_fake_full_image_region(region: dict, img_w: int, img_h: int) -> bool:
    """True neu 'region' ma DeepFace tra ve thuc chat la CA buc anh (dau
    hieu no KHONG tim thay khuon mat that, chi la ket qua fallback vi
    enforce_detection=False) - ket qua nay PHAI bi loai, khong dung de
    doan tuoi/gioi tinh.

    SUA LOI (quan trong): ban cu dung nguong "mo" (rong/cao >= 95% anh
    dau vao) de doan ket qua "gia". Nhung ham nay duoc goi tren ROI da
    la vung dau+vai CAT SAN (xem estimate_demographics_from_person_box),
    nen 1 khuon mat THAT, CHUP GAN rat hay chiem >= 95% dien tich ROI do
    - khien khuon mat THAT bi loai oan nhu la ket qua "gia", gender luon
    = None, man hinh cu hien "dang tim mat..." mai khong bao gio luu
    duoc ho so.

    Fallback THAT cua DeepFace (khi enforce_detection=False va KHONG tim
    thay mat) luon la CHINH XAC toa do (0, 0, img_w, img_h) - tuc la goc
    tren-trai (x=0, y=0) VA rong/cao bang DUNG kich thuoc anh dau vao.
    Mot khuon mat THAT du chiem gan het ROI van se co x/y > 0 (co le mep
    ben ngoai) hoac w/h nho hon kich thuoc anh 1 chut do thuat toan align
    mat. Vi vay doi sang kiem tra KHOP CHINH XAC (cho phep sai so 1px do
    so hoc lam tron) thay vi nguong ty le, de khong loai oan mat that."""
    if img_w <= 0 or img_h <= 0:
        return True
    rx, ry = region.get("x", 0), region.get("y", 0)
    rw, rh = region.get("w", 0), region.get("h", 0)
    if rw <= 0 or rh <= 0:
        return True
    return rx <= 0 and ry <= 0 and rw >= img_w - 1 and rh >= img_h - 1


def _apply_clahe(image_bgr):
    """SUA LOI LAN 7: can bang sang CUC BO (CLAHE - Contrast Limited
    Adaptive Histogram Equalization) truoc khi dua anh vao DeepFace. Anh
    webcam thuc te hay bi thieu sang/chenh sang 1 ben (gan cua so, den
    nguoc sang...), khien vung mat bi toi/chay sang mot phan - lam giam do
    chinh xac doan gioi tinh/tuoi cua model (du khuon mat van ro voi mat
    nguoi nhin). CLAHE chi can bang do sang/tuong phan CUC BO (theo tung o
    nho 8x8), KHONG doi mau sac/hinh dang khuon mat, chi giup chi tiet
    vung toi/qua sang ro hon cho model doc. Lam tren kenh L (do sang) cua
    khong gian mau LAB de khong anh huong mau sac (kenh A/B giu nguyen)."""
    try:
        lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l2 = clahe.apply(l)
        lab2 = cv2.merge((l2, a, b))
        return cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)
    except Exception:
        # Khong de 1 loi xu ly anh phu lam hong ca pipeline chinh - neu
        # CLAHE loi vi ly do gi do, dung tam anh GOC thay vi crash.
        return image_bgr


def estimate_age_gender(image_bgr, detector_backend: str = "yunet", include_race: bool = False) -> List[Dict]:
    """Tra ve danh sach dict, moi phan tu ung voi 1 khuon mat THAT phat
    hien duoc (da loc bo cac ket qua "gia"):
       {"age": int, "age_range": str, "gender": "Man"/"Woman",
        "gender_confidence": float, "region": {"x":.., "y":.., "w":.., "h":..},
        "race_probs": {"asian": 72.1, ...} hoac None neu include_race=False}
    Tra ve list rong neu khong tim thay khuon mat that nao, hoac thieu
    thu vien deepface.

    `include_race=True` (mac dinh TAT - KHONG doi hanh vi cu cho moi noi
    da goi ham nay truoc gio): yeu cau DeepFace phan tich THEM action
    "race", chi dung cho tinh nang TUY CHON "phan nhom khu vuc" (xem
    region_mapping.py + demographics_engine.py) - doc ky GIOI HAN va
    nguyen tac su dung trong docstring cua region_mapping.py TRUOC khi
    bat tinh nang nay."""
    global _BACKEND_FALLBACK_TO_OPENCV
    try:
        from deepface import DeepFace
    except ImportError:
        print("Chua cai deepface. Chay: pip install deepface tf-keras")
        return []

    if image_bgr is None or image_bgr.size == 0:
        return []
    img_h, img_w = image_bgr.shape[:2]

    # SUA LOI LAN 7: can bang sang cuc bo truoc khi phan tich - xem
    # _apply_clahe() o tren. Chi doi ANH DUA VAO DeepFace, khong doi
    # image_bgr goc (vd anh goc van duoc frame goc giu nguyen o noi goi).
    image_bgr = _apply_clahe(image_bgr)

    # NEU backend "yunet" (hoac backend khac) tung bi loi 1 lan (vd khong
    # tai duoc model do mang/firewall chan), TU DONG chuyen vinh vien sang
    # "opencv" (Haar Cascade - luon co san, khong can tai them gi) cho CAC
    # LAN GOI SAU - tranh goi lai 1 backend da biet la hong MOI FRAME (vua
    # cham vua spam loi ra console lien tuc).
    effective_backend = "opencv" if _BACKEND_FALLBACK_TO_OPENCV else detector_backend

    actions = ["age", "gender", "race"] if include_race else ["age", "gender"]
    try:
        results = DeepFace.analyze(
            img_path=image_bgr,
            actions=actions,
            enforce_detection=False,
            detector_backend=effective_backend,
            align=True,
            silent=True,
        )
    except Exception as e:
        if not _BACKEND_FALLBACK_TO_OPENCV and effective_backend != "opencv":
            print(
                f"[Canh bao] Backend nhan dien mat '{effective_backend}' bi loi ({e}) "
                "- co the do khong tai duoc model (thieu Internet luc dau). "
                "TU DONG chuyen sang backend 'opencv' (luon co san) cho cac lan sau."
            )
            _BACKEND_FALLBACK_TO_OPENCV = True
        else:
            print(f"Loi khi phan tich tuoi/gioi tinh: {e}")
        return []

    if isinstance(results, dict):
        results = [results]

    out = []
    for r in results:
        region = r.get("region", {}) or {}
        # BUOC LOC QUAN TRONG: bo ket qua "gia" (khong tim thay mat that)
        if _is_fake_full_image_region(region, img_w, img_h):
            continue

        gender_probs = r.get("gender", {}) or {}
        dominant_gender = r.get("dominant_gender") or (
            max(gender_probs, key=gender_probs.get) if gender_probs else "Khong ro"
        )
        confidence = gender_probs.get(dominant_gender, 0.0)
        age = int(r.get("age", -1))
        out.append({
            "age": age,
            "age_range": age_to_range(age),
            "gender": dominant_gender,
            "gender_confidence": round(float(confidence), 1),
            "region": region,
            "race_probs": (r.get("race") or None) if include_race else None,
        })
    return out


def estimate_demographics_from_person_box(
    frame, box: Tuple[int, int, int, int], include_race: bool = False
) -> Dict:
    """Ham DUNG CHUNG cho cac script camera (webcam_tracking_demo.py,
    camera_in.py, camera_out.py): nhan 1 khung nguoi (x, y, w, h) tu YOLO/HOG,
    cat vung DAU + VAI (nua tren cua khung nguoi, KHONG mo rong kieu "them
    toc" nhu ban cu vi lam sai ty le DeepFace can), roi de DeepFace TU tim
    khuon mat that trong vung do.

    Tra ve {"age": int|None, "age_range": str, "gender": str|None,
            "gender_confidence": float}. Neu khong tim thay khuon mat that
    (vd nguoi quay lung, khuat mat...), tra ve gender=None - script goi ham
    nay se HIEU la "chua xac dinh duoc", KHONG hien thi thong tin sai.

    === SUA LOI LAN 3 (camera dat gan/nhin tu tren xuong - chi thay toc,
    van hien "dang tim mat...") ===
    Ban truoc CO Y cat bo, chi lay ~60% PHIA TREN cua khung nguoi YOLO
    (goi la vung "dau+vai"), vi gia dinh khung nguoi la dang DUNG/DI toan
    than (dau o tren, than/chan o duoi) chup tu xa. Nhung voi camera dat
    GAN hoac nhin CHECH TU TREN XUONG (vd gan lan can cau, webcam dat cao
    chuc vao dau nguoi di qua), khung nguoi ma YOLO nhan dien duoc CO THE
    VON DA chi la vung dau/toc (khong thay than nguoi phia duoi trong
    khung hinh) - neu cat tiep 60% TREN cua khung do thi se cat MAT LUON
    ca phan mat that con lai (chi con toc), DeepFace khong con gi de tim
    -> gender luon None -> man hinh cu hien "dang tim mat...".
    Sua: KHONG con cat theo ty le chieu cao nua - dung TOAN BO khung
    nguoi ma YOLO da phat hien (+ them vien dem moi phia) va de DeepFace
    TU tim mat that o bat ky dau trong do. Lam duoc vay AN TOAN vi ham
    loc ket qua "gia" (_is_fake_full_image_region) da duoc sua o tren de
    chi khop CHINH XAC voi fallback that cua DeepFace, nen ROI lon hon se
    khong con bi hieu nham la "gia" nua.
    LUU Y QUAN TRONG (khong phai loi code): DeepFace van CAN nhin THAY
    duoc mat/mui/mieng that trong khung hinh camera. Neu nguoi dung cui
    sat/dung qua gan khien camera CHI quay duoc dinh dau (nhu anh vi du),
    thi KHONG co thuat toan nao doan duoc gioi tinh/tuoi - can lui ra xa
    hoac chinh goc camera de camera thay duoc ca khuon mat (mat, mui,
    mieng), khong chi phan toc/dinh dau.

    === SUA LOI LAN 6 (2 nguoi dung/ngoi SAT NHAU - bi gan NHAM gioi tinh
    cua nguoi BEN CANH, vd anh thuc te nguoi dung gui: 1 ban nu ngoi sat 1
    ban nam, bi he thong doan "Man" cho ca ban nu) ===
    Nguyen nhan: khi 2 nguoi dung/ngoi sat nhau, khung YOLO cua moi nguoi
    co the da gan cham nhau, roi lai được THEM vien dem (pad_x/pad_y, truoc
    la 20%) o CA 2 phia - khien vung ROI cua nguoi A de lan SANG CA mat
    nguoi B ben canh. Luc do DeepFace tim thay 2 khuon mat that trong cung
    1 ROI (dung cua A, lan cua B) - va code CU chon khuon mat LON NHAT
    trong 2 mat do de dung ket qua, nhung "lon nhat trong ROI cua A" KHONG
    co nghia la "mat cua A" - neu B ngoi gan/quay mat ro hon, mat cua B co
    the LON HON trong chinh ROI cua A, va he thong se tra nham ket qua cua
    B cho track cua A (dung chinh xac truong hop trong anh nguoi dung gui).
    Sua 2 phan:
      1. Giam vien dem tu 20% xuong 10% moi phia - van du de khong cat mat
         neu khung YOLO hoi chat, nhung giam bot ROI lan sang nguoi ben
         canh khi dung/ngoi sat nhau.
      2. Doi tieu chi chon mat: THAY VI chon mat LON NHAT (de bi anh huong
         boi nguoi ben canh), chon mat co TAM gan TAM cua chinh khung nguoi
         (box) dang xet NHAT - vi mat cua dung nguoi trong track nay, ve ly
         thuyet, phai nam gan giua khung cua chinh ho, con mat cua nguoi ben
         canh (neu lan vao ROI) se nam LECH ve 1 phia (gan mep ROI hon).
    """
    x, y, w, h = box
    fh, fw = frame.shape[:2]
    empty = {"age": None, "age_range": "Khong ro", "gender": None,
             "gender_confidence": 0.0, "race_probs": None}
    if w <= 0 or h <= 0:
        return empty

    # Dung TOAN BO khung nguoi YOLO phat hien duoc (khong con cat rieng
    # "60% phia tren" nua - xem giai thich o docstring tren), chi them
    # vien dem moi phia de khong bo sot mep mat/dau khi YOLO khoanh hoi
    # chat. SUA LOI LAN 6: giam tu 0.20 xuong 0.10 de giam lan sang nguoi
    # ben canh khi dung/ngoi sat nhau (xem docstring tren).
    pad_x = int(w * 0.10)
    pad_y = int(h * 0.10)
    x0 = max(0, x - pad_x)
    x1 = min(fw, x + w + pad_x)
    y0 = max(0, y - pad_y)
    y1 = min(fh, y + h + pad_y)

    roi = frame[y0:y1, x0:x1]
    if roi.size == 0:
        return empty

    faces = estimate_age_gender(roi, include_race=include_race)
    if not faces:
        return empty

    # SUA LOI LAN 6: neu phat hien >1 mat trong ROI (vd 2 nguoi dung/ngoi
    # sat nhau, ROI cua nguoi nay lan sang mat nguoi kia), KHONG con chon
    # mat LON NHAT nua (de bi anh huong boi nguoi ben canh neu ho gan/ro
    # hon) - thay vao do chon mat co TAM gan TAM cua chinh khung nguoi
    # (box) dang xet NHAT, vi do moi la mat THUC SU thuoc ve track nay.
    # Tam cua box goc, quy doi sang toa do CUC BO trong ROI (vi ROI da bi
    # cat di tu (x0, y0)):
    box_cx_roi = (x + w / 2.0) - x0
    box_cy_roi = (y + h / 2.0) - y0

    def _dist_to_box_center(f):
        r = f["region"]
        fcx = r.get("x", 0) + r.get("w", 0) / 2.0
        fcy = r.get("y", 0) + r.get("h", 0) / 2.0
        return ((fcx - box_cx_roi) ** 2 + (fcy - box_cy_roi) ** 2) ** 0.5

    faces.sort(key=_dist_to_box_center)
    best = faces[0]
    return {
        "age": best["age"],
        "age_range": best["age_range"],
        "gender": best["gender"],
        "gender_confidence": best["gender_confidence"],
        "race_probs": best.get("race_probs"),
    }


def annotate_age_gender(image_bgr, results: List[Dict]):
    out = image_bgr.copy()
    for r in results:
        reg = r.get("region", {})
        x, y, w, h = reg.get("x", 0), reg.get("y", 0), reg.get("w", 0), reg.get("h", 0)
        label = f"{r['gender']} ~{r.get('age_range', r.get('age'))}"
        cv2.rectangle(out, (x, y), (x + w, y + h), (255, 0, 255), 2)
        cv2.putText(out, label, (x, max(0, y - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 0, 255), 2, cv2.LINE_AA)
    return out


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Dung: python3 age_gender_estimator.py <duong_dan_anh>")
        sys.exit(1)

    img = cv2.imread(path)
    if img is None:
        print(f"Khong doc duoc anh: {path}")
        sys.exit(1)

    results = estimate_age_gender(img)
    print(f"Phat hien {len(results)} khuon mat THAT (da loc bo ket qua gia):")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['gender']} (do tin cay {r['gender_confidence']}%), khoang tuoi: {r['age_range']}")

    if results:
        annotated = annotate_age_gender(img, results)
        out_path = path.rsplit(".", 1)[0] + "_age_gender.jpg"
        cv2.imwrite(out_path, annotated)
        print(f"Da luu anh ket qua: {out_path}")
