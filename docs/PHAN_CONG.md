# Phân công module & quy trình làm việc song song — Nhóm 50

Kế hoạch đầy đủ (Gantt, checklist từng sprint, file nộp cuối kỳ) nằm trong artifact "Kế Hoạch Nhóm 50". File này là bản rút gọn để mở ngay trong repo.

## 7 module, mỗi người sở hữu trọn "từ giao diện tới backend" của module mình

Trạng thái tháng 11/2026: **cả 7 module đã chạy với dữ liệu thật**, không còn API mẫu (mock). Việc còn lại của mỗi người là kiểm thử nghiệm thu (UAT) theo tiêu chí chấp nhận trong BRD và sửa lỗi phát hiện được.

| Module | Chức năng BFD | Backend | Giao diện | Người sở hữu |
|---|---|---|---|---|
| M1 Lõi AI & đếm | F1.1–F1.4, F3.1, F3.2 | routers/counting.py, routers/bridge.py, routers/demographics.py, ai_engine/* | views/luot_qua_cau.py, views/camera.py | **Minh** |
| M2 Nền tảng | F6.1, PB-T3 | main.py, database.py, models.py, schemas.py, security.py, timeutil.py, routers/accounts.py | app.py, common.py, views/tai_khoan.py | **Minh** |
| M3 Cảnh báo & sự cố | F2.1–F2.4 | routers/alerts.py, notify.py | views/truc_ca.py, views/bang_led.py | **Hoan** (F2.1–F2.3: Minh) |
| M4 Phân tích & báo cáo | F3.3, F5.2, F5.3 | routers/reports.py | views/co_cau_khach.py, views/bao_cao.py (PDF/Excel: backend/report_export.py) | **Hoan** |
| M5 Đối chiếu vé | F4.1, F4.2 | routers/tickets.py | views/doi_chieu_ve.py | **Hoan** |
| M6 Dashboard | F5.1 | (dùng API M1) | views/tong_quan.py, views/lich_su.py | **Khánh** |
| M7 Quản trị | F6.2, F6.3, PB-06 | routers/admin.py | views/cau_hinh.py, views/nguoi_nhan.py, views/quyen_rieng_tu.py | **Khánh** |

## 5 quy tắc để không ai phải chờ ai

1. **Làm trên hợp đồng API.** Trang giao diện gọi đúng đường dẫn trong `docs/API_CONTRACT.md`.
2. **Chỉ sửa file mình sở hữu.** Cần đổi file dùng chung (`models.py`, `common.py`, `main.py`, `requirements.txt`) → mở GitHub Issue gán cho Minh.
3. **Không cần camera để làm việc.** `python tools/simulate_bridge.py --random 200` gửi lượt qua cầu giả lập qua API thật.
4. **Mỗi việc một nhánh, mỗi nhánh tối đa 1–2 ngày.** Nhánh nhỏ thì Pull Request (PR) nhỏ, review nhanh, ít xung đột.
5. **Họp nhanh 15 phút mỗi tối** (online): hôm nay xong gì · mai làm gì · đang vướng gì. Vướng quá 30 phút → hỏi ngay trên nhóm chat.

## Quy trình Git hằng ngày

```bash
git checkout main
git pull origin main                       # lấy code mới nhất MỖI SÁNG
git checkout -b hoan/f4-doi-chieu-ve       # ten-nguoi/ma-chuc-nang-mo-ta
# ... sửa code, chạy thử ...
pytest tests/ -q                           # trước khi tạo Pull Request
git add backend/routers/tickets.py frontend/views/doi_chieu_ve.py
git commit -m "F4.2: tinh ty le chenh lech that tu visit_events"
git push -u origin hoan/f4-doi-chieu-ve
```

Sau đó lên GitHub → **Compare & pull request** → gán người review (Minh review code của Hoan/Khánh, Khánh review code của Minh) → **Merge** → xóa nhánh.

Không bao giờ `git push` thẳng lên `main`. Minh nên bật *Settings → Branches → Branch protection* cho `main` (bắt buộc PR).

## Nhãn GitHub Issues gợi ý

`F1` … `F6` · `frontend` · `backend` · `ai` · `docs` · `bug` · `api-change` · `sprint-3` … `sprint-5`. Dùng GitHub Projects dạng bảng Kanban (To do / Doing / Review / Done) — chụp màn hình bảng này mỗi sprint để đưa vào phần Execution của báo cáo.
