/* =====================================================================
 * Bang LED tai dau cau — Linh Than (mascot) + phong nen dong + so lieu
 * MODULE M3 · F2.2 (FR-05, FR-17). Phu trach: HOAN.
 *
 * Mo:   http://<may-chu>:8000/led/            (Chrome/Edge, F11 toan man hinh)
 * Tham so URL:  ?scene=3   khoa canh 3      ?debug=1   mo bang debug (hoac nhan phim D)
 *               ?api=http://192.168.1.5:8000  khi trang mo tu may khac
 * Sua cau thoai, gio ngay/dem, thu tu canh... trong CONFIG ben duoi.
 * ===================================================================== */
const CONFIG = {
  apiBase: new URLSearchParams(location.search).get("api") || "",
  pollMs: 1000,
  offlineAfterMs: 10000,          // mat du lieu hon 10 giay -> chip "mat ket noi", giu nguyen clip
  dayStart: "06:00", dayEnd: "17:30",
  sceneMode: "clock",             // "clock" (theo gio) | "fixed:1" ... "fixed:4"
  altEveryMin: 5, altDurationSec: 60,   // Xanh/Vang: moi 5 phut xen canh phu 60 giay
  tourSceneSec: 30,               // Do: moi canh tour 30 giay
  tourFollowsClock: false,        // true: tour chi gom canh cung khung gio
  crossfadeMs: 800,
  scenes: {
    1: { name: "Phố cổ Hội An", time: "day", src: "media/scene1", tour: "Phố cổ Hội An rực rỡ sắc đèn lồng." },
    2: { name: "Sông Hoài", time: "night", src: "media/scene2", tour: "Sông Hoài lung linh đèn hoa đăng về đêm." },
    3: { name: "Cầu Rồng", time: "night", src: "media/scene3", tour: "Cầu Rồng bắc qua sông Hàn, rực sáng về đêm." },
    4: { name: "Chùa Cầu", time: "day", src: "media/scene4", tour: "Chùa Cầu với tượng khỉ và chó canh giữ hai đầu cầu." },
  },
  clock: { day: { main: 1, alt: 4 }, night: { main: 3, alt: 2 } },
  // Clip nhan vat. null = chua co -> dung clip thay the. Linh Khuyen: tha file vao media/ roi dien ten o day.
  clips: {
    than: { idle: "media/than_idle.webm", wave: "media/than_wave.webm", bow: "media/than_bow.webm",
            yellow: "media/than_yellow.webm", red: "media/than_red.webm", walkIn: null, walkOut: null },
    khuyen: { idle: null, stop: null, bow: null, walkIn: null, walkOut: null },
  },
  timing: { greenActMin: 25, greenActMax: 35, yellowRepeat: 20, redRepeat: 18, quietAfter: 60, quietRepeat: 20,
            newGuestGap: 30, bubbleMs: 8000 },
  lines: {
    intro: ["{chao}! Mình là Linh Thân, rất vui được đón bạn đến Chùa Cầu."],
    green: ["{chao}! Cầu đang thông thoáng, mời bạn thong thả dạo bước. Hiện có {onbridge} khách trên cầu.",
            "Chùa Cầu hân hạnh đón bạn. Nhớ lưu lại thật nhiều khoảnh khắc đẹp nhé!"],
    greenBow: ["Xin kính chào quý khách. Chúc bạn một chuyến tham quan thật trọn vẹn."],
    guest: ["Hôm nay đã có {dem} lượt khách ghé thăm. Chào mừng bạn!"],
    toYellow: ["Cầu đang khá đông ({onbridge} người). Xin đi chậm, giữ khoảng cách và đừng dừng lại giữa lối đi nhé."],
    yellow: ["Bạn thân mến, hãy đi chậm một chút để mọi người cùng an toàn.",
             "Hiện có {onbridge} người trên cầu. Xin giữ khoảng cách giúp mình nhé."],
    yellowToGreen: ["Cảm ơn quý khách đã đi chậm. Cầu đã thông thoáng trở lại!"],
    toRed: ["Cầu đang quá tải ({onbridge} người). Xin quý khách chờ ở đầu cầu giây lát. Mời bạn dạo cảnh tham quan ảo trên màn hình này."],
    red: ["Xin bạn vui lòng chờ một chút để đảm bảo an toàn cho di tích và mọi người."],
    redDown: ["Cảm ơn bạn đã kiên nhẫn chờ đợi!"],
    quiet: ["{chao}! Mời bạn đến tham quan Chùa Cầu, di tích hơn 400 năm tuổi của Hội An."],
  },
  sign: {
    green: { chip: "AN TOÀN", vi: "MỜI QUÝ KHÁCH THAM QUAN", en: "WELCOME · PLEASE ENTER" },
    yellow: { chip: "ĐI CHẬM", vi: "CẦU SẮP ĐẦY · XIN ĐI CHẬM", en: "NEARLY FULL · PLEASE KEEP MOVING" },
    red: { chip: "QUÁ TẢI", vi: "CẦU ĐANG ĐẦY · VUI LÒNG CHỜ", en: "THE BRIDGE IS FULL · PLEASE WAIT" },
  },
};

/* ---------------------------------------------------------------- tien ich */
const Q = new URLSearchParams(location.search);
if (/^[1-4]$/.test(Q.get("scene") || "")) CONFIG.sceneMode = "fixed:" + Q.get("scene");
const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const rand = (a, b) => a + Math.random() * (b - a);
let utcOffsetH = 7;
const lastPicked = {};
function pick(key) {             // chon ngau nhien, khong lap cau vua noi
  const list = CONFIG.lines[key] || [key];
  if (list.length === 1) return list[0];
  let i;
  do { i = Math.floor(Math.random() * list.length); } while (i === lastPicked[key]);
  lastPicked[key] = i;
  return list[i];
}
function vnNow() { const d = new Date(Date.now() + utcOffsetH * 3600e3); return { h: d.getUTCHours(), m: d.getUTCMinutes(), s: d.getUTCSeconds() }; }
const toMin = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; };
function isDay() { const t = vnNow(); const x = t.h * 60 + t.m; return x >= toMin(CONFIG.dayStart) && x < toMin(CONFIG.dayEnd); }
function chao() { const h = vnNow().h; return h >= 4 && h < 11 ? "Chào buổi sáng" : h >= 11 && h < 18 ? "Chào buổi chiều" : "Chào buổi tối"; }
function fill(text) { return text.replace("{chao}", chao()).replace("{onbridge}", S.onbridge).replace("{dem}", S.dem); }
const levelOf = (code) => (code === "CRITICAL" ? "red" : code === "WARNING" || code === "ALERT" ? "yellow" : "green");

/* ---------------------------------------------------------------- loi thoai */
let bubbleTimer = null;
function say(key, ms = CONFIG.timing.bubbleMs) {
  const el = $("bubble"), tx = $("bubbleText");
  tx.textContent = fill(key.includes(" ") ? key : pick(key));
  // toi da 2 dong: thu nho chu, roi noi rong o neu can
  let fs = 2.8; tx.style.fontSize = fs + "vh"; $("bubbleWrap").style.maxWidth = "";
  const fits = () => tx.scrollHeight <= tx.clientHeight + 2;
  while (!fits() && fs > 1.8) { fs -= 0.1; tx.style.fontSize = fs.toFixed(1) + "vh"; }
  if (!fits()) $("bubbleWrap").style.maxWidth = "58vw";
  el.classList.add("show");
  clearTimeout(bubbleTimer);
  bubbleTimer = setTimeout(() => el.classList.remove("show"), ms);
}

/* ---------------------------------------------------------------- mascot */
const Mascot = {
  vids: {}, current: null, busy: false, token: 0,
  init() {
    const box = $("mascot");
    for (const [who, set] of Object.entries(CONFIG.clips)) {
      for (const [name, src] of Object.entries(set)) {
        if (!src) continue;
        const v = document.createElement("video");
        Object.assign(v, { src, muted: true, playsInline: true, preload: "auto" });
        v.loop = name === "idle";
        box.appendChild(v);
        this.vids[`${who}.${name}`] = v;
      }
    }
    this.show("than.idle");
  },
  has(key) { return !!this.vids[key]; },
  show(key) {
    const v = this.vids[key] || this.vids["than.idle"];
    for (const x of Object.values(this.vids)) if (x !== v) { x.classList.remove("on"); if (!x.loop) x.pause(); }
    v.classList.add("on");
    if (v.paused) v.play().catch(() => needTap());
    this.current = key;
    return v;
  },
  /** Phat 1 clip hanh dong roi ve idle. Clip moi (chuyen muc) se ngat clip dang phat. */
  async play(key, line) {
    const my = ++this.token;
    this.busy = true;
    const v = this.vids[key];
    if (line) say(line);
    if (!v) { await sleep(4000); } else {
      v.currentTime = 0; this.show(key);
      await new Promise((res) => { const done = () => { v.removeEventListener("ended", done); res(); };
        v.addEventListener("ended", done); setTimeout(done, (v.duration || 10) * 1000 + 500); });
    }
    if (my === this.token) { this.show("than.idle"); this.busy = false; }
  },
  async walkOut() { const m = $("mascot"); m.classList.add("walking", "out"); await sleep(1300); m.classList.remove("walking"); },
  async walkIn() { const m = $("mascot"); m.classList.add("walking"); m.classList.remove("out"); await sleep(1300); m.classList.remove("walking"); },
};

/* ---------------------------------------------------------------- phong nen */
const BG = {
  a: null, b: null, cur: 0, pending: 0, fading: false, forceAt: 0,
  init() { this.a = $("bgA"); this.b = $("bgB");
    for (const v of [this.a, this.b]) v.addEventListener("timeupdate", () => this.onTime(v)); },
  setSrc(v, n) {
    const base = CONFIG.scenes[n].src;
    v.innerHTML = `<source src="${base}.webm" type="video/webm"><source src="${base}.mp4" type="video/mp4">`;
    v.load();
  },
  start(n) { this.cur = n; this.setSrc(this.a, n); this.a.loop = true; this.a.play().catch(() => needTap()); this.label(); },
  request(n) {                    // doi canh vao ranh gioi vong lap -> khong khung hinh bi khung
    if (n === this.cur || n === this.pending) return;
    this.pending = n; this.forceAt = Date.now() + 12000;
    const back = this.a.classList.contains("show") ? this.b : this.a;
    this.setSrc(back, n);
  },
  onTime(v) {
    if (!this.pending || this.fading || !v.classList.contains("show")) return;
    if (v.duration && v.duration - v.currentTime <= CONFIG.crossfadeMs / 1000 + 0.06) this.swap();
  },
  tick() { if (this.pending && !this.fading && Date.now() > this.forceAt) this.swap(); },
  swap() {
    const front = this.a.classList.contains("show") ? this.a : this.b;
    const back = front === this.a ? this.b : this.a;
    this.fading = true; back.loop = true; back.currentTime = 0;
    back.play().catch(() => {});
    back.classList.add("show"); front.classList.remove("show");
    this.cur = this.pending; this.pending = 0; this.label();
    setTimeout(() => { front.pause(); this.fading = false; }, CONFIG.crossfadeMs + 50);
  },
  label() { $("sceneName").textContent = CONFIG.scenes[this.cur]?.name || ""; },
};

/* ---------------------------------------------------------------- trang thai */
const S = {
  level: null, onbridge: 0, dem: 0, capacity: 20, wait: null, waitEn: null,
  lastOk: Date.now(), offline: false, booted: false,
  lastDemUp: Date.now(), lastGuestLine: 0, nextAct: 0,
  tour: null, override: null, overrideBump: 0,
};

function applySign() {
  const lv = S.level || "green", t = CONFIG.sign[lv];
  document.body.classList.remove("lvl-green", "lvl-yellow", "lvl-red");
  document.body.classList.add("lvl-" + lv);
  $("level-chip-big").textContent = t.chip; $("chipLevel").textContent = t.chip;
  $("msgVi").textContent = t.vi; $("msgEn").textContent = t.en;
  $("countNum").textContent = S.onbridge; $("countCap").textContent = "/ " + S.capacity;
  $("chipCount").textContent = `${S.onbridge} người trên cầu`;
  $("wait").textContent = lv === "red" && S.wait ? `Thời gian chờ dự kiến: ${S.wait} · Estimated wait: ${S.waitEn}` : "";
  $("chipOffline").hidden = !S.offline;
}

async function onLevelChange(prev, next) {
  const T = CONFIG.timing;
  Mascot.token++;                       // ngat hanh dong dang phat
  if (next === "red") {
    startTour();
    if (Mascot.has("khuyen.stop")) {   // co du clip Linh Khuyen: doi nhan vat
      await Mascot.walkOut(); Mascot.show("khuyen.idle"); await Mascot.walkIn();
      Mascot.play("khuyen.stop", "toRed");
    } else {
      Mascot.play("than.red", "toRed");
    }
    S.nextAct = Date.now() + T.redRepeat * 1000;
    return;
  }
  stopTour();
  if (prev === "red") {
    await Mascot.play(Mascot.has("khuyen.bow") ? "khuyen.bow" : "than.bow", "redDown");
    if (Mascot.has("khuyen.walkOut")) { await Mascot.walkOut(); Mascot.show("than.idle"); await Mascot.walkIn(); }
    if (S.level !== next) return;
    say(next === "yellow" ? "yellow" : "green");
  } else if (next === "yellow") {
    Mascot.play("than.yellow", "toYellow");
  } else if (prev === "yellow" && next === "green") {
    Mascot.play("than.wave", "yellowToGreen");
  }
  S.nextAct = Date.now() + (next === "yellow" ? T.yellowRepeat : rand(T.greenActMin, T.greenActMax)) * 1000;
}

function periodic() {
  const T = CONFIG.timing, now = Date.now();
  if (!S.booted || S.offline || Mascot.busy) return;
  if (S.level === "green") {
    const quiet = now - S.lastDemUp > T.quietAfter * 1000;
    if (now >= S.nextAct) {
      const bow = Math.random() < 0.35;
      Mascot.play(bow ? "than.bow" : "than.wave", quiet ? "quiet" : bow ? "greenBow" : "green");
      S.nextAct = now + (quiet ? T.quietRepeat : rand(T.greenActMin, T.greenActMax)) * 1000;
    }
  } else if (S.level === "yellow" && now >= S.nextAct) {
    Mascot.play("than.yellow", "yellow"); S.nextAct = now + T.yellowRepeat * 1000;
  } else if (S.level === "red" && now >= S.nextAct) {
    Mascot.play(Mascot.has("khuyen.stop") ? "khuyen.stop" : "than.red", "red"); S.nextAct = now + T.redRepeat * 1000;
  }
}

/* ---------------------------------------------------------------- canh */
function clockScene() {
  const part = isDay() ? CONFIG.clock.day : CONFIG.clock.night;
  const t = vnNow(), secOfDay = t.h * 3600 + t.m * 60 + t.s, cycle = CONFIG.altEveryMin * 60;
  return secOfDay % cycle >= cycle - CONFIG.altDurationSec ? part.alt : part.main;
}
function startTour() {
  if (CONFIG.sceneMode.startsWith("fixed")) return;
  let list = [1, 2, 3, 4];
  if (CONFIG.tourFollowsClock) list = list.filter((n) => CONFIG.scenes[n].time === (isDay() ? "day" : "night"));
  const i = list.indexOf(BG.cur);       // bat dau tu canh KHAC canh dang hien
  list = list.slice(i + 1).concat(list.slice(0, i + 1));
  S.tour = { list, idx: 0, since: Date.now(), announced: -1 };
}
function stopTour() { S.tour = null; }
function desiredScene() {
  if (CONFIG.sceneMode.startsWith("fixed:")) return Number(CONFIG.sceneMode.split(":")[1]);
  if (S.tour) {
    const k = Math.floor((Date.now() - S.tour.since) / (CONFIG.tourSceneSec * 1000));
    return S.tour.list[k % S.tour.list.length];
  }
  return clockScene();
}
function sceneTick() {
  document.body.classList.toggle("night", !isDay());
  BG.request(desiredScene()); BG.tick();
  if (S.tour && BG.cur && S.tour.announced !== BG.cur && !BG.pending && !Mascot.busy) {
    S.tour.announced = BG.cur;                     // dung cho + thuyet minh canh (doi dien xong moi noi)
    say(CONFIG.scenes[BG.cur].tour);
    S.nextAct = Math.max(S.nextAct, Date.now() + 9000);   // khong de cau "vui long cho" de len ngay
  }
}

/* ---------------------------------------------------------------- du lieu */
async function poll() {
  try {
    const r = await fetch(`${CONFIG.apiBase}/display/state`, { cache: "no-store" });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    S.lastOk = Date.now(); utcOffsetH = d.utc_offset_hours ?? 7;
    S.offline = !!d.stale; S.capacity = d.capacity; S.wait = d.wait_label; S.waitEn = d.wait_label_en;
    let onb = d.onbridge, dem = d.dem, code = d.level;
    if (S.override) { code = S.override; S.offline = false; }
    dem += S.overrideBump; onb += S.overrideBump;
    S.onbridge = onb;
    if (dem > S.dem && S.booted) {
      S.lastDemUp = Date.now();
      const T = CONFIG.timing;
      if (S.level === "green" && !Mascot.busy && Date.now() - S.lastGuestLine > T.newGuestGap * 1000) {
        S.dem = dem; S.lastGuestLine = Date.now(); Mascot.play("than.wave", "guest");
      }
    }
    S.dem = dem;
    const next = levelOf(code);
    if (S.level === null) S.level = next;          // muc ban dau luon lay tu du lieu
    else if (!S.offline) {
      if (next !== S.level) { const prev = S.level; S.level = next; applySign(); onLevelChange(prev, next); }
    }
  } catch (e) {
    if (Date.now() - S.lastOk > CONFIG.offlineAfterMs) S.offline = true;
  }
  applySign();
}

async function boot() {
  Mascot.init(); BG.init();
  await poll();
  BG.start(desiredScene());
  applySign();
  $("mascot").classList.add("out");
  await sleep(400);
  if (Mascot.has("than.walkIn")) Mascot.play("than.walkIn");
  await Mascot.walkIn();
  S.booted = true;
  if (S.level === "red") onLevelChange("green", "red");
  else { Mascot.play("than.wave", "intro"); S.nextAct = Date.now() + rand(CONFIG.timing.greenActMin, CONFIG.timing.greenActMax) * 1000; }
  setInterval(poll, CONFIG.pollMs);
  setInterval(() => { periodic(); sceneTick(); clockTick(); }, 500);
}

function clockTick() { const t = vnNow(); $("clock").textContent = `${String(t.h).padStart(2, "0")}:${String(t.m).padStart(2, "0")}`; if (DBG.on) DBG.render(); }
function needTap() {
  const el = $("tapToStart"); if (!el.hidden) return; el.hidden = false;
  el.onclick = () => { el.hidden = true; document.querySelectorAll("video").forEach((v) => (v.classList.contains("on") || v.classList.contains("show")) && v.play()); };
}

/* ---------------------------------------------------------------- debug */
const DBG = {
  on: Q.get("debug") === "1", built: false,
  build() {
    const el = $("debug");
    el.innerHTML = `<b>BẢNG DEBUG</b> (phím D)<div id="dbgInfo" class="row"></div>
      <div class="row">Giả lập mức: <button data-l="OK">Xanh</button><button data-l="WARNING">Vàng</button><button data-l="CRITICAL">Đỏ</button><button data-l="">Tự động</button></div>
      <div>Khách: <button data-g="1">+1 khách</button></div>
      <div class="row">Cảnh: <button data-s="clock">Theo giờ</button>${[1, 2, 3, 4].map((n) => `<button data-s="fixed:${n}">${n}</button>`).join("")}</div>
      <div>Tour theo giờ: <button id="dbgTour"></button></div>`;
    el.querySelectorAll("[data-l]").forEach((b) => (b.onclick = () => { S.override = b.dataset.l || null; poll(); }));
    el.querySelectorAll("[data-g]").forEach((b) => (b.onclick = () => { S.overrideBump++; poll(); }));
    el.querySelectorAll("[data-s]").forEach((b) => (b.onclick = () => { CONFIG.sceneMode = b.dataset.s; if (S.level === "red") startTour(); }));
    $("dbgTour").onclick = () => { CONFIG.tourFollowsClock = !CONFIG.tourFollowsClock; };
    this.built = true;
  },
  render() {
    const el = $("debug"); el.hidden = !this.on; if (!this.on) return;
    if (!this.built) this.build();
    $("dbgInfo").innerHTML = `Mức: <b>${S.level}</b>${S.override ? " (giả lập)" : ""} · trên cầu ${S.onbridge}/${S.capacity} · dem ${S.dem}<br>
      Cảnh: <b>${BG.cur}</b> ${BG.pending ? "→ " + BG.pending : ""} · ${CONFIG.sceneMode} · ${isDay() ? "ngày" : "đêm"}${S.tour ? " · tour" : ""}<br>
      Mascot: ${Mascot.current}${Mascot.busy ? " (đang diễn)" : ""} · mất kết nối: ${S.offline}`;
    $("dbgTour").textContent = CONFIG.tourFollowsClock ? "đang bật" : "đang tắt";
  },
};
document.addEventListener("keydown", (e) => { if (e.key === "d" || e.key === "D") { DBG.on = !DBG.on; DBG.render(); } });

boot();
