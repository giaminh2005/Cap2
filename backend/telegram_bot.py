"""
backend/telegram_bot.py  —  Bot Telegram 2 chieu (luong nen)
=============================================================
Doc tin nhan gui TOI bot (getUpdates, long polling) va tra loi:

    /tinhhinh   tinh hinh cau ngay luc nay (so nguoi, tung chan cau, xu huong, camera, su co)
    /homnay     tong ket hom nay den gio + du bao
    /suco       su co dang mo
    /start /help  danh sach lenh + chat_id cua ban

Nut bam duoi tin canh bao:
    ✅ Đã xử lý   (ack:<id>)  -> nhan xu ly su co ngay tren Telegram, bao cho ca nhom
    📍 Tình hình  (status)    📊 Hôm nay (today)

Chi chat da co trong danh sach "Nguoi nhan canh bao" moi duoc xem so lieu / bam nut.
Chat la -> bot tra loi chat_id de quan tri vien them vao.

Vi getUpdates chi cho 1 noi doc, khi bot chay thi trang "Nguoi nhan canh bao"
lay danh sach chat vua nhan tin tu SEEN (xem routers/admin.py).
Tat bang SMARTCAU_DISABLE_SCHEDULER=1 (khi chay test).
"""

import os
import threading
import time
from html import escape

from . import messages, notify
from .database import SessionLocal

SEEN = {}            # chat_id -> {chat_id, name, type, username}
_state = {"running": False, "offset": 0}

HELP = ("🤖 <b>SmartCau AI · Bot Chùa Cầu</b>\n\n"
        "/tinhhinh — tình hình trên cầu ngay lúc này\n"
        "/homnay — tổng kết hôm nay và dự báo\n"
        "/suco — sự cố đang mở\n"
        "/help — danh sách lệnh\n\n"
        "Khi có cảnh báo Đỏ, bấm <b>✅ Đã xử lý</b> ngay dưới tin nhắn để nhận xử lý.")


def running() -> bool:
    return _state["running"]


def _chat_name(chat: dict) -> str:
    return (chat.get("title") or " ".join(x for x in (chat.get("first_name"), chat.get("last_name")) if x)
            or chat.get("username") or str(chat["id"]))


def _remember(chat: dict):
    cid = str(chat["id"])
    SEEN[cid] = {"chat_id": cid, "name": _chat_name(chat), "type": chat.get("type"), "username": chat.get("username")}


def _allowed(db, chat_id: str) -> bool:
    from .routers.admin import Recipient
    return db.query(Recipient).filter(Recipient.address == chat_id, Recipient.channel == "telegram").first() is not None


def _open_incidents_text(db) -> str:
    from .routers.alerts import Incident
    rows = db.query(Incident).filter(Incident.closed_at.is_(None)).order_by(Incident.id).all()
    if not rows:
        return "✅ Không có sự cố nào đang mở."
    out = ["🚨 <b>SỰ CỐ ĐANG MỞ</b>"]
    for i in rows:
        out.append(f"• #{i.id} · cao nhất {i.peak_count} người · "
                   + (f"đã nhận bởi {escape(i.acked_by)}" if i.acked_at else "<b>chưa ai nhận</b>"))
    return "\n".join(out)


def handle_update(upd: dict, send=None, answer=None):
    """Xu ly 1 update cua Telegram. send(chat_id, text, buttons), answer(callback_id, text). Tra ve ten hanh dong."""
    from .routers.alerts import Incident, acknowledge, buttons

    send = send or (lambda cid, text, btn=None: notify._send_telegram(cid, text, btn))
    answer = answer or (lambda qid, text: notify.telegram_api("answerCallbackQuery", callback_query_id=qid, text=text))
    msg = upd.get("message") or upd.get("channel_post")
    cq = upd.get("callback_query")
    chat = (msg or {}).get("chat") or ((cq or {}).get("message") or {}).get("chat")
    if not chat:
        if upd.get("my_chat_member", {}).get("chat"):
            _remember(upd["my_chat_member"]["chat"])
        return None
    _remember(chat)
    cid = str(chat["id"])
    with SessionLocal() as db:
        allowed = _allowed(db, cid)
        if cq is not None:
            data = cq.get("data") or ""
            if not allowed:
                answer(cq["id"], "Bạn chưa có trong danh sách người nhận cảnh báo.")
                return "denied"
            who = _chat_name(cq.get("from") or chat)
            if data.startswith("ack:"):
                inc = db.query(Incident).filter(Incident.id == int(data[4:] or 0)).first()
                if inc is None or inc.closed_at is not None:
                    answer(cq["id"], "Sự cố này đã đóng.")
                    return "ack-closed"
                if inc.acked_at is not None:
                    answer(cq["id"], f"{inc.acked_by} đã nhận xử lý trước đó.")
                    return "ack-dup"
                acknowledge(db, inc, who, via="telegram")
                answer(cq["id"], f"Đã ghi nhận: {who} xử lý sự cố #{inc.id}.")
                return "ack"
            answer(cq["id"], "")
            text = messages.today_message(db) if data == "today" else messages.status_message(db)
            send(cid, text, buttons())
            return data or "status"
        text = (msg.get("text") or "").strip()
        cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
        if not allowed:
            if cmd or chat.get("type") == "private":
                send(cid, f"👋 Xin chào! Bot này dành cho đội vận hành Chùa Cầu.\n"
                          f"Chat ID của bạn: <code>{cid}</code>\n"
                          "Gửi số này cho quản trị viên để được thêm vào danh sách nhận cảnh báo.", None)
            return "unknown-chat"
        if cmd in ("/tinhhinh", "/status", "/tinh_hinh"):
            send(cid, messages.status_message(db), buttons())
            return "status"
        if cmd in ("/homnay", "/today"):
            send(cid, messages.today_message(db), buttons())
            return "today"
        if cmd in ("/suco", "/incidents"):
            send(cid, _open_incidents_text(db), buttons())
            return "incidents"
        if cmd in ("/start", "/help", "/trogiup"):
            send(cid, HELP, buttons())
            return "help"
    return None


def _loop():
    while True:
        if not notify.telegram_token():
            _state["running"] = False
            time.sleep(10)
            continue
        _state["running"] = True
        ok, res = notify.telegram_api("getUpdates", offset=_state["offset"], timeout=25,
                                      allowed_updates=["message", "callback_query", "my_chat_member", "channel_post"])
        if not ok:
            time.sleep(5)
            continue
        for upd in res:
            _state["offset"] = upd["update_id"] + 1
            try:
                handle_update(upd)
            except Exception as e:   # 1 tin loi khong lam bot dung
                print(f"[telegram_bot] Lỗi xử lý tin: {e}")


def start():
    if os.environ.get("SMARTCAU_DISABLE_SCHEDULER") or os.environ.get("SMARTCAU_DISABLE_BOT"):
        return None
    t = threading.Thread(target=_loop, daemon=True, name="telegram-bot")
    t.start()
    return t
