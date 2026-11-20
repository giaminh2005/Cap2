# Kết quả đo sai số đếm người (NFR-02)

- Thời điểm: 12:49 20/11/2026 · mô hình: `yolov8n.pt` · chế độ: lượt qua vạch
- Số video: 3 (Sprint 0 yêu cầu ≥ 3 video mật độ khác nhau)

| Video | Đếm tay in | Hệ thống in | Sai số in | Đếm tay out | Hệ thống out | Sai số out |
|---|---|---|---|---|---|---|
| thua.mp4 | 2 | 2 | 0.0% | 0 | 0 | 0.0% |
| vua.mp4 | 4 | 3 | 25.0% | 4 | 3 | 25.0% |
| dong.mp4 | 6 | 5 | 16.7% | 4 | 6 | 50.0% |

| Chỉ số | in | out |
|---|---|---|
| Sai số trên tổng | 16.7% | 12.5% |
| Sai số trung bình mỗi video | 13.9% | 25.0% |
| Sai số lớn nhất | 25.0% | 50.0% |

**MVP (≤ 15%): CHƯA ĐẠT** · **Nghiệm thu thực tế (≤ 10%): CHƯA ĐẠT**

## Phạm vi lần đo

- Ba clip thưa, vừa và đông dài 7,93 giây mỗi clip.
- Cả ba clip dùng [vạch đã lưu](eval_counting_line.json), ở khoảng 93,3–93,5% chiều cao tính từ trên xuống. Phía dưới vạch là phía trong cầu. Ngưỡng tin cậy là `0.4` và vùng đệm quanh vạch là `0.03`.
- [CSV đếm tay](eval_counting.csv) đã cập nhật clip thưa thành 0 lượt ra. Khi cả đếm tay lẫn hệ thống đều bằng 0, script tính sai số là 0%.
- Kết luận dùng giá trị lớn hơn giữa sai số trung bình theo video của lượt vào và lượt ra.
