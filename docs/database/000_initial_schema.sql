-- SmartCau AI - Lược đồ CSDL hiện hành (phiên bản 000)
-- Khớp với các lớp SQLAlchemy trong backend/models.py, backend/routers/*.py, backend/daily_report.py.
-- Ứng dụng tự tạo các bảng này qua backend/database.py::ensure_schema(); tệp này dùng để
-- đọc, kiểm tra hoặc tạo CSDL thủ công:  sqlite3 backend/smartcau.db < docs/database/000_initial_schema.sql
-- Thời gian lưu theo UTC, trừ bridge_crossings.local_time (giờ Việt Nam).

-- D1 Điểm giám sát
CREATE TABLE IF NOT EXISTS camera_status (
  camera_id     INTEGER PRIMARY KEY,               -- 1 = chân cầu 1, 2 = chân cầu 2
  source        VARCHAR DEFAULT '',
  fps           INTEGER DEFAULT 0,
  line          VARCHAR DEFAULT '',                -- vạch đếm (JSON, tọa độ chuẩn hóa 0-1)
  sends_alerts  INTEGER DEFAULT 0,
  demographics  INTEGER DEFAULT 0,
  machine       VARCHAR DEFAULT '',
  last_seen     DATETIME,
  started_at    DATETIME
);
-- D2 Cấu hình ngưỡng (một dòng, id = 1)
CREATE TABLE IF NOT EXISTS system_config (
  id              INTEGER PRIMARY KEY,
  alert_threshold INTEGER DEFAULT 20,
  open_time       VARCHAR DEFAULT '07:00',
  close_time      VARCHAR DEFAULT '21:30',
  updated_at      DATETIME,
  updated_by      VARCHAR,
  telegram_token  VARCHAR
);
-- D3 Số liệu lượt khách
CREATE TABLE IF NOT EXISTS bridge_state (
  id         INTEGER PRIMARY KEY,                  -- một dòng, id = 1
  num1       INTEGER DEFAULT 0,
  num2       INTEGER DEFAULT 0,
  dem        INTEGER DEFAULT 0,
  dem_date   VARCHAR,                              -- YYYY-MM-DD giờ Việt Nam
  updated_at DATETIME
);
CREATE TABLE IF NOT EXISTS bridge_crossings (
  id             INTEGER PRIMARY KEY,
  timestamp      DATETIME,
  local_time     DATETIME,
  camera_id      INTEGER,
  direction      VARCHAR,                          -- in | out
  track_id       INTEGER,
  onbridge_after INTEGER
);
CREATE INDEX IF NOT EXISTS ix_bridge_crossings_id ON bridge_crossings (id);
CREATE INDEX IF NOT EXISTS ix_bridge_crossings_local_time ON bridge_crossings (local_time);
CREATE INDEX IF NOT EXISTS ix_bridge_crossings_camera_id ON bridge_crossings (camera_id);
CREATE INDEX IF NOT EXISTS ix_bridge_crossings_direction ON bridge_crossings (direction);
CREATE TABLE IF NOT EXISTS occupancy_state (
  id            INTEGER PRIMARY KEY,
  current_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS occupancy_snapshots (
  id        INTEGER PRIMARY KEY,
  timestamp DATETIME,
  count     INTEGER,
  status    VARCHAR                                 -- OK | WARNING | ALERT | CRITICAL
);
CREATE INDEX IF NOT EXISTS ix_occupancy_snapshots_id ON occupancy_snapshots (id);
CREATE INDEX IF NOT EXISTS ix_occupancy_snapshots_timestamp ON occupancy_snapshots (timestamp);
CREATE TABLE IF NOT EXISTS facade_passes (
  id        INTEGER PRIMARY KEY,
  timestamp DATETIME,
  camera_id INTEGER
);
CREATE INDEX IF NOT EXISTS ix_facade_passes_timestamp ON facade_passes (timestamp);
-- D4 Nhật ký sự cố
CREATE TABLE IF NOT EXISTS system_events (
  id         INTEGER PRIMARY KEY,
  timestamp  DATETIME,
  event_type VARCHAR,
  count      INTEGER,
  message    VARCHAR,
  camera_id  INTEGER
);
CREATE INDEX IF NOT EXISTS ix_system_events_id ON system_events (id);
CREATE INDEX IF NOT EXISTS ix_system_events_timestamp ON system_events (timestamp);
CREATE INDEX IF NOT EXISTS ix_system_events_event_type ON system_events (event_type);
CREATE TABLE IF NOT EXISTS incidents (
  id           INTEGER PRIMARY KEY,
  opened_at    DATETIME,
  peak_count   INTEGER DEFAULT 0,
  alert_count  INTEGER DEFAULT 1,
  acked_at     DATETIME,
  acked_by     VARCHAR,
  note         VARCHAR,
  closed_at    DATETIME,
  close_reason VARCHAR,                             -- auto | manual
  closed_by    VARCHAR,
  false_alarm  BOOLEAN DEFAULT 0,
  false_note   VARCHAR,
  false_by     VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_incidents_opened_at ON incidents (opened_at);
-- D5 Hồ sơ lượt khách
CREATE TABLE IF NOT EXISTS visit_events (
  id        INTEGER PRIMARY KEY,
  track_id  INTEGER,
  timestamp DATETIME,
  age       INTEGER,
  age_range VARCHAR,                                -- 0-5 … 70+ | Khong ro
  gender    VARCHAR,                                -- Man | Woman | NULL
  origin    VARCHAR,                                -- Trong nuoc | Nuoc ngoai | NULL
  camera_id INTEGER
);
CREATE INDEX IF NOT EXISTS ix_visit_events_id ON visit_events (id);
CREATE INDEX IF NOT EXISTS ix_visit_events_track_id ON visit_events (track_id);
CREATE INDEX IF NOT EXISTS ix_visit_events_timestamp ON visit_events (timestamp);
-- D6 Tài khoản người dùng
CREATE TABLE IF NOT EXISTS users (
  id                   INTEGER PRIMARY KEY,
  username             VARCHAR,
  full_name            VARCHAR DEFAULT '',
  password_hash        VARCHAR,
  role                 VARCHAR DEFAULT 'nguoi_truc', -- admin | quan_ly | nguoi_truc
  active               BOOLEAN DEFAULT 1,
  must_change_password BOOLEAN DEFAULT 0,
  created_at           DATETIME,
  last_login           DATETIME
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE TABLE IF NOT EXISTS auth_tokens (
  token      VARCHAR PRIMARY KEY,
  user_id    INTEGER,
  created_at DATETIME,
  expires_at DATETIME
);
CREATE INDEX IF NOT EXISTS ix_auth_tokens_user_id ON auth_tokens (user_id);
-- D7 Dữ liệu vé
CREATE TABLE IF NOT EXISTS ticket_counts (
  id           INTEGER PRIMARY KEY,
  date         VARCHAR,                             -- YYYY-MM-DD giờ Việt Nam
  hour         INTEGER,                             -- NULL = cả ngày
  ticket_count INTEGER,
  entered_by   VARCHAR DEFAULT '',
  created_at   DATETIME
);
CREATE INDEX IF NOT EXISTS ix_ticket_counts_date ON ticket_counts (date);
-- D8 Nhật ký cấu hình
CREATE TABLE IF NOT EXISTS audit_log (
  id        INTEGER PRIMARY KEY,
  timestamp DATETIME,
  username  VARCHAR,
  action    VARCHAR,
  detail    VARCHAR DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log (timestamp);
-- D9 Người nhận cảnh báo
CREATE TABLE IF NOT EXISTS recipients (
  id         INTEGER PRIMARY KEY,
  name       VARCHAR,
  channel    VARCHAR DEFAULT 'telegram',
  address    VARCHAR,                               -- chat_id Telegram
  active     BOOLEAN DEFAULT 1,
  created_at DATETIME,
  topics     VARCHAR                                -- red,yellow,…; NULL = nhận tất cả
);
-- D10 Báo cáo ngày
CREATE TABLE IF NOT EXISTS daily_reports (
  id            INTEGER PRIMARY KEY,
  date          VARCHAR,
  data          TEXT,                               -- JSON của /reports/summary?period=day
  total_entries INTEGER DEFAULT 0,
  incidents     INTEGER DEFAULT 0,
  created_at    DATETIME,
  sent_at       DATETIME,
  delivery      VARCHAR
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_daily_reports_date ON daily_reports (date);
