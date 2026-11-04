# Phân công module & quy trình làm việc song song — Nhóm 50

Kế hoạch đầy đủ (Gantt, checklist từng sprint, file nộp cuối kỳ) nằm trong artifact "Kế Hoạch Nhóm 50". File này là bản rút gọn để mở ngay trong repo.

## 7 module, mỗi người sở hữu trọn "từ giao diện tới backend" của module mình

| Module | Chức năng BFD | Backend | Giao diện | Người sở hữu |
|---|---|---|---|---|
| M1 Lõi AI & đếm | F1.1–F1.4, F3.1, F3.2 | routers/counting.py, routers/demographics.py, ai_engine/* | — | **Minh** |
| M2 Nền tảng | F6.1, PB-T3 | main.py, database.py, models.py, schemas.py, security.py | app.py, common.py | **Minh** |
| M3 Cảnh báo & sự cố | F2.1–F2.4 | routers/alerts.py (F2.1–2.3 Minh, F2.4 Hoan) | views/truc_ca.py, views/bang_led.py | **Hoan** (giao diện + F2.4) |
| M4 Phân tích & báo cáo | F3.3, F5.2, F5.3 | routers/reports.py | views/co_cau_khach.py, views/bao_cao.py | **Hoan** |
| M5 Đối chiếu vé | F4.1, F4.2 | routers/tickets.py | views/doi_chieu_ve.py | **Hoan** |
| M6 Dashboard | F5.1 | (dùng API M1) | views/tong_quan.py, views/lich_su.py | **Khánh** |
| M7 Quản trị | F6.2, F6.3, PB-06 | routers/admin.py (recipients) | views/cau_hinh.py, views/nguoi_nhan.py, views/quyen_rieng_tu.py | **Khánh** |

Khánh nhận phần code nhẹ nhất (2 trang đã chạy sẵn + 2 trang đơn giản + 1 bảng CSDL) để còn thời gian điều phối, UAT và ghép báo cáo.

## 5 quy tắc để không ai phải chờ ai

1. **Làm trên hợp đồng API, không chờ backend.** Trang giao diện gọi đúng đường dẫn trong `docs/API_CONTRACT.md`; skeleton đã trả dữ liệu mẫu nên trang chạy được ngay hôm nay.
2. **Chỉ sửa file mình sở hữu.** Cần đổi file dùng chung (`models.py`, `common.py`, `main.py`, `requirements.txt`) → mở GitHub Issue gán cho Minh.
3. **Không cần camera để làm việc.** `python tools/seed_demo_data.py` nạp dữ liệu mẫu qua API thật.
4. **Mỗi việc một nhánh, mỗi nhánh tối đa 1–2 ngày.** Nhánh nhỏ thì Pull Request (PR) nhỏ, review nhanh, ít xung đột.
5. **Họp nhanh 15 phút mỗi tối** (online): hôm nay xong gì · mai làm gì · đang vướng gì. Vướng quá 30 phút → hỏi ngay trên nhóm chat.

## Quy trình Git hằng ngày

```bash
git checkout main
git pull origin main                       # lấy code mới nhất MỖI SÁNG
git checkout -b hoan/f4-doi-chieu-ve       # ten-nguoi/ma-chuc-nang-mo-ta
# ... sửa code, chạy thử ...
pytest tests/test_api.py -q                # nếu có sửa backend
git add backend/routers/tickets.py frontend/views/doi_chieu_ve.py
git commit -m "F4.2: tinh ty le chenh lech that tu visit_events"
git push -u origin hoan/f4-doi-chieu-ve
```

Sau đó lên GitHub → **Compare & pull request** → gán người review (Minh review code của Hoan/Khánh, Khánh review code của Minh) → **Merge** → xóa nhánh.

Không bao giờ `git push` thẳng lên `main`. Minh nên bật *Settings → Branches → Branch protection* cho `main` (bắt buộc PR).

## Đưa bản tổ chức lại này lên repo (Minh làm 1 lần)

Hướng dẫn đầy đủ từng bước, kèm lỗi dễ gặp, nằm trong tài liệu "Cap2 tổ chức lại — mô tả thay đổi và cách đưa lên GitHub". Tóm tắt:

1. Báo cả nhóm ngừng push lên `main` cho tới khi PR này được merge.
2. Clone repo vào **thư mục mới** (thư mục cũ giữ nguyên làm bản dự phòng):
   `git clone https://github.com/giaminh2005/Cap2.git Cap2_moi` → `cd Cap2_moi` → `git checkout -b sprint3/to-chuc-lai`
3. `git rm -r -q .` (xóa toàn bộ file cũ khỏi thư mục và khỏi Git, `.git/` vẫn còn).
4. Giải nén `Cap2_tochuclai.zip` ra chỗ khác. Bên trong có thư mục `Cap2/` — chép **NỘI DUNG** của thư mục đó (kể cả file ẩn `.gitignore`, `.env.example`, `.streamlit/`) vào `Cap2_moi/`. Không chép nguyên thư mục `Cap2/`, nếu không sẽ thành `Cap2_moi/Cap2/...`.
5. `git status` → kiểm tra không có `.db`, `.pt`, `__pycache__`, `.venv`, `.env`.
6. `git add -A` → `git commit -m "Sprint 3: to chuc lai theo kien truc 3 lop va chuc nang BFD F1-F6"` → `git push -u origin sprint3/to-chuc-lai`
7. Tạo Pull Request, Hoan và Khánh chạy thử nhánh này, ổn thì merge.

## Nhãn GitHub Issues gợi ý

`F1` … `F6` · `frontend` · `backend` · `ai` · `docs` · `bug` · `api-change` · `sprint-3` … `sprint-5`. Dùng GitHub Projects dạng bảng Kanban (To do / Doing / Review / Done) — chụp màn hình bảng này mỗi sprint để đưa vào phần Execution của báo cáo.
