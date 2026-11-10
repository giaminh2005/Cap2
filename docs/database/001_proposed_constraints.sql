-- SmartCau AI - Migration 001 (ĐỀ XUẤT, chưa áp dụng vào code)
-- Mục tiêu: bổ sung ràng buộc toàn vẹn theo ERD Sprint 3.
-- SQLite không thêm được FOREIGN KEY vào bảng có sẵn, nên mỗi bảng được tạo lại:
--   tạo bảng mới -> chép dữ liệu -> xóa bảng cũ -> đổi tên. Sao lưu smartcau.db trước khi chạy.
-- Sau khi áp dụng, cần sửa các lớp SQLAlchemy tương ứng (ForeignKey, UniqueConstraint) để code và CSDL khớp nhau.
PRAGMA foreign_keys = OFF;
BEGIN;

-- 1. auth_tokens.user_id -> users.id (xóa tài khoản thì xóa phiên)
CREATE TABLE auth_tokens_new (
  token VARCHAR PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at DATETIME, expires_at DATETIME NOT NULL);
INSERT INTO auth_tokens_new SELECT token, user_id, created_at, expires_at FROM auth_tokens WHERE user_id IN (SELECT id FROM users);
DROP TABLE auth_tokens; ALTER TABLE auth_tokens_new RENAME TO auth_tokens;
CREATE INDEX ix_auth_tokens_user_id ON auth_tokens (user_id);

-- 2. ticket_counts: không trùng (date, hour); người nhập tham chiếu users.username
CREATE TABLE ticket_counts_new (
  id INTEGER PRIMARY KEY, date VARCHAR NOT NULL, hour INTEGER CHECK (hour BETWEEN 0 AND 23),
  ticket_count INTEGER NOT NULL CHECK (ticket_count >= 0),
  entered_by VARCHAR REFERENCES users(username) ON UPDATE CASCADE, created_at DATETIME,
  UNIQUE (date, hour));
INSERT INTO ticket_counts_new SELECT id, date, hour, ticket_count, NULLIF(entered_by,''), created_at FROM ticket_counts;
DROP TABLE ticket_counts; ALTER TABLE ticket_counts_new RENAME TO ticket_counts;
CREATE INDEX ix_ticket_counts_date ON ticket_counts (date);

-- 3. incidents: người xác nhận, đóng, báo sai tham chiếu users.username
CREATE TABLE incidents_new (
  id INTEGER PRIMARY KEY, opened_at DATETIME NOT NULL, peak_count INTEGER DEFAULT 0, alert_count INTEGER DEFAULT 1,
  acked_at DATETIME, acked_by VARCHAR REFERENCES users(username) ON UPDATE CASCADE, note VARCHAR,
  closed_at DATETIME, close_reason VARCHAR CHECK (close_reason IN ('auto','manual')),
  closed_by VARCHAR REFERENCES users(username) ON UPDATE CASCADE,
  false_alarm BOOLEAN DEFAULT 0, false_note VARCHAR, false_by VARCHAR REFERENCES users(username) ON UPDATE CASCADE);
INSERT INTO incidents_new SELECT * FROM incidents;
DROP TABLE incidents; ALTER TABLE incidents_new RENAME TO incidents;
CREATE INDEX ix_incidents_opened_at ON incidents (opened_at);

-- 4. camera_id của các bảng sự kiện tham chiếu camera_status.camera_id
CREATE TABLE bridge_crossings_new (
  id INTEGER PRIMARY KEY, timestamp DATETIME, local_time DATETIME NOT NULL,
  camera_id INTEGER NOT NULL REFERENCES camera_status(camera_id),
  direction VARCHAR NOT NULL CHECK (direction IN ('in','out')), track_id INTEGER, onbridge_after INTEGER);
INSERT OR IGNORE INTO camera_status (camera_id) SELECT DISTINCT camera_id FROM bridge_crossings WHERE camera_id IS NOT NULL;
INSERT INTO bridge_crossings_new SELECT * FROM bridge_crossings;
DROP TABLE bridge_crossings; ALTER TABLE bridge_crossings_new RENAME TO bridge_crossings;
CREATE INDEX ix_bridge_crossings_local_time ON bridge_crossings (local_time);
CREATE INDEX ix_bridge_crossings_camera_id ON bridge_crossings (camera_id);
CREATE INDEX ix_bridge_crossings_direction ON bridge_crossings (direction);

-- 5. Tách loại tin của người nhận thành bảng liên kết (thay cột topics dạng chuỗi nhiều giá trị)
CREATE TABLE recipient_topics (
  recipient_id INTEGER NOT NULL REFERENCES recipients(id) ON DELETE CASCADE,
  topic VARCHAR NOT NULL CHECK (topic IN ('red','yellow','group','camera','morning','ticket','daily','weekly','system')),
  PRIMARY KEY (recipient_id, topic));
-- Dữ liệu cột recipients.topics được chép sang bảng mới bằng script Python (tách chuỗi theo dấu phẩy).

-- 6. Bỏ bảng trùng lặp occupancy_state (số người trên cầu = bridge_state.num1 + num2) sau khi sửa code đọc từ bridge_state.
-- DROP TABLE occupancy_state;

COMMIT;
PRAGMA foreign_keys = ON;
