# Hướng dẫn hệ thống giám sát tin tức

Tài liệu mô tả toàn bộ cách cài đặt, sử dụng, cấu trúc thư mục và luồng xử lý của dự án **Phan_mem** (chạy qua `He_thong.py`).

---

## 1. Hệ thống là gì?

Ứng dụng web giúp:

- Theo dõi **đối tượng** (lãnh đạo, nhân vật công chúng…) trên **Google News**
- Phân loại tin bằng **Google Gemini AI**: có liên quan không, có hoạt động không, có **thay đổi chức vụ** không
- Lưu kết quả theo **hai kênh**: hoạt động và biến động chức vụ
- Hiển thị **bảng điều khiển** (dashboard) theo khung thời gian (giờ)
- Gửi **báo cáo Telegram** sau mỗi lần quét (tùy chọn): có hoạt động / biến động thì báo chi tiết; không có gì trong cửa sổ báo cáo thì vẫn gửi tin *trống* để biết đã quét

**Quét tự động nền** theo chu kỳ (`auto_scan_enabled`, `scan_interval_minutes`) — dashboard tự làm mới khi có lượt quét mới. Có thể **Quét tất cả** hoặc **Quét riêng** từng đối tượng (nút **khóa** khi đang quét — không xếp hàng). **Ba chế độ AI** (`keyword` / `activity` / `full`): đổi chế độ → lọc lại hiển thị + **tự quét lại** toàn bộ. Giao diện **sáng / tối** (lưu trên trình duyệt).

---

## 2. Sơ đồ hoạt động (toàn hệ thống)

**File sơ đồ (PNG / PDF):**

| File | Đường dẫn |
|------|-----------|
| PNG | `docs/so_do_he_thong.png` (bản màu, ~450 KB) |
| PDF | `docs/so_do_he_thong.pdf` — nếu file đang mở trong viewer thì dùng tạm `docs/so_do_he_thong_gen.pdf` rồi đổi tên |

Nguồn Mermaid: `docs/so_do_he_thong.mmd`. Tạo lại sau khi sửa sơ đồ:

```bash
npx -y @mermaid-js/mermaid-cli -i docs/so_do_he_thong.mmd -o docs/so_do_he_thong.png -b white -w 3200 -H 2400
npx -y @mermaid-js/mermaid-cli -i docs/so_do_he_thong.mmd -o docs/so_do_he_thong.pdf -b white -w 3200
```

Bản sơ đồ dùng **màu theo từng khối**: tím (khởi động), xanh dương (web/API), cyan (người dùng), cam (kích hoạt quét), đỏ (đang quét), xanh lá (thu thập), vàng (lọc), tím AI (phân tích), xanh lam (hiển thị), teal (Telegram); ba chế độ AI có màu riêng (vàng / xanh / tím nhạt).

Sơ đồ chi tiết nằm trong `docs/so_do_he_thong.mmd` (xem bằng VS Code + extension Mermaid hoặc mở file PNG/PDF).

**Chú thích nhanh**

| Ký hiệu / trường | Ý nghĩa |
|------------------|--------|
| `ai_scan_mode` | **keyword** — không Gemini, lưu mọi tin tìm được; **activity** — Gemini + đúng đối tượng, không kênh biến động; **full** — thêm quét bổ nhiệm/miễn nhiệm |
| Đổi chế độ AI | Lưu config → **lọc lại** danh sách hiển thị ngay → **quét lại** (`mode_change`, `ignore_history`) nếu không đang quét |
| `news_kind` | `hoatdong` / `biendong`; trùng URL → ưu tiên `biendong` |
| `channel_hoatdong` | Tin đủ điều kiện lưu sau AI (hoặc keyword) |
| `channel_biendong` | Chỉ chế độ **full** + `Is_Change` có chứng cứ chức vụ |
| Quét thủ công | `ignore_history=true` — xử lý lại URL; ghi đè bản cũ cùng URL (upsert) |
| Đang quét | `POST /monitor/run` trả **409**; nút Quét trên UI **disabled** |
| Telegram digest | Gộp theo đối tượng; báo cáo dài **chia nhiều tin** (≤4096 ký tự, HTML) |

---

## 3. Cấu trúc thư mục

```
Phan_mem/
├── He_thong.py              # Điểm chạy: python He_thong.py → cổng 8000
├── requirements.txt         # Thư viện Python
├── HUONG_DAN.md             # File này
│
├── config/                  # Cấu hình (nên sao lưu)
│   ├── config.json          # API Gemini, đối tượng, Google News, Telegram
│   └── Chinh_thong.json     # Danh sách báo chính thống (domain)
│
├── data/                    # Dữ liệu chạy (tự tạo/cập nhật)
│   ├── notifications.json   # Tin đã lưu (2 kênh)
│   ├── history.json         # URL đã quét (tránh gọi AI trùng)
│   ├── telegram_sent.json   # Khóa tin Telegram đã gửi
│   └── url_decode_cache.json # Cache decode link Google News
│
├── src/                     # Mã nguồn Python
│   ├── web.py               # Flask: giao diện + REST API
│   ├── monitor.py           # Quét tin, AI, lưu, lọc hiển thị theo chế độ AI
│   ├── auto_scanner.py      # Quét nền, khóa is_scanning, quét lại khi đổi chế độ
│   ├── telegram_notify.py   # Digest Telegram (chia tin nếu dài)
│   ├── common.py            # Tiện ích dùng chung (thời gian, URL bài, bool)
│   ├── data_store.py        # Thống kê / xóa dữ liệu có chọn
│   ├── press_whitelist.py   # Lọc domain báo
│   ├── rss_fetch.py         # Thu tin RSS báo chính thống
│   ├── json_io.py           # Đọc/ghi JSON (khóa file, thử lại trên Windows)
│   └── paths.py             # Đường dẫn; migrate file legacy (một lần khi khởi động)
│
├── docs/
│   ├── so_do_he_thong.mmd   # Nguồn sơ đồ Mermaid
│   ├── so_do_he_thong.png
│   └── so_do_he_thong.pdf
│
├── scripts/
│   └── system_check.py    # Kiểm tra offline; --live khi server chạy
│
├── health_check.py          # Gọi system_check.py --live
│
├── templates/               # HTML
│   ├── dashboard.html       # Trang chính
│   └── target_detail.html   # Chi tiết từng đối tượng
│
├── static/
│   ├── css/isr-theme.css
│   └── js/
│       ├── dashboard.js
│       ├── settings.js
│       └── theme.js         # Giao diện sáng / tối (localStorage)
│
└── emip.v3.js               # (Tùy chọn) Script Qime/Telegram riêng — KHÔNG gắn vào hệ thống này
```

---

## 4. Cài đặt lần đầu

### 4.1. Yêu cầu

- Windows (hoặc OS có Python 3.10+)
- Kết nối Internet (Google News, Gemini, Telegram)

### 4.2. Cài thư viện

Mở terminal trong thư mục `Phan_mem`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4.3. Cấu hình bắt buộc

Mở `config/config.json` và điền ít nhất:

| Trường           |                   Ý nghĩa                       |
|------------------|-------------------------------------------------|
| `gemini_api_key` | API key Google AI / Gemini                      |
| `targets`        | Danh sách `{ "name", "position" }` cần theo dõi |

Có thể chỉnh thêm trong `google_news` (ngôn ngữ, số tin tối đa, lọc báo…).

### 4.4. Chạy server

```bash
python He_thong.py
```

Mở trình duyệt: **http://localhost:8000**

Dừng server: `Ctrl+C` trong terminal.

---

## 5. Hướng dẫn sử dụng giao diện

### 5.1. Trang chính (Dashboard)

| Thành phần | Chức năng |
|------------|-----------|
| **Giao diện sáng / tối** | Nút ngay **dưới Cài đặt hệ thống** (sidebar trái); chỉ đổi màu, giữ bố cục; lưu trên trình duyệt (`localStorage`, key `ui-theme`) |
| **Thời gian tìm kiếm** | Số giờ hiển thị báo cáo (ưu tiên giá trị trên UI, không ghi đè bởi config khi xem) |
| **Đối tượng** | Thêm / sửa / xóa tên và chức vụ; nút ▶ **Quét riêng** trên từng dòng |
| **Quét tất cả** | Quét toàn bộ đối tượng — **khóa** khi hệ thống đang quét (không xếp hàng) |
| **Quét riêng** | Một đối tượng (sidebar, thẻ, trang chi tiết) — cùng quy tắc khóa |
| **Tải lại** | Làm mới danh sách thẻ tóm tắt |
| **Cài đặt hệ thống** | Lọc báo, quét tự động, Telegram, danh sách báo chính thống |

**Cột phải dashboard**

| Panel | Nội dung |
|-------|----------|
| **Trạng thái hệ thống** | KPI (Đối tượng / Biến động / Có hoạt động), quét tự động, chu kỳ, trạng thái, **Lần quét cuối** (thời điểm cụ thể `dd/mm/yyyy, hh:mm:ss`), Telegram |
| **Tin mới nhất** | Danh sách tin gần đây trong cửa sổ giờ đã chọn |

**Thẻ kết quả quét:** tóm tắt theo đối tượng (hoạt động / chức vụ, trạng thái, snippet); không hiển thị thời gian dạng “X phút trước”.

**Sửa đối tượng:** chọn tên trong danh sách → sửa ô Họ tên / Chức vụ → **Thêm** (nút đổi thành lưu) hoặc **Hủy**.

**Xem chi tiết:** bấm vào thẻ đối tượng hoặc mũi tên → trang `/target?name=...` với hai mục **Hoạt động** và **Chức vụ**, nút **Quét riêng** và tải JSON.

### 5.2. Trang chi tiết đối tượng

| Thành phần | Chức năng |
|------------|-----------|
| **Quét riêng** | Quét chỉ đối tượng đang xem (dùng `hours` trên URL) |
| **Giao diện sáng / tối** | Nút trên thanh trên cùng |
| **Tải JSON** | Xuất dữ liệu trong cửa sổ giờ |

### 5.3. Cài đặt hệ thống

**Chế độ quét AI** (một lựa chọn — lưu ngay khi bấm thẻ):

| Chế độ | Ý nghĩa |
|--------|---------|
| **Từ khóa (không Gemini)** | Lưu/hiển thị mọi tin GNews & RSS tìm được, không gọi AI |
| **AI — hoạt động & đúng đối tượng** | Gemini lọc hoạt động + xác nhận đúng tên; không quét biến động chức vụ |
| **AI — đầy đủ** | Thêm lượt tìm bổ nhiệm/miễn nhiệm và kênh biến động |

Đổi chế độ → dashboard **cập nhật danh sách ngay** (lọc theo chế độ) và **tự quét lại** (nếu không đang quét). Tin cũ quét bằng từ khóa sẽ ẩn khi chuyển sang AI cho đến khi quét lại xong.

**Lọc khi quét**

| Tùy chọn | Mặc định khuyến nghị | Ý nghĩa |
|----------|----------------------|---------|
| Chỉ báo chính thống | Bật | Chỉ giữ tin từ domain trong `Chinh_thong.json`; GNews có thể tìm theo `site:domain` |
| Số tin tối đa / đối tượng | 15–50 | Giới hạn mỗi truy vấn GNews |
| Quét RSS báo chính thống | Tùy chọn | Link trực tiếp từ feed, nhanh hơn decode Google News |

**Quét tự động (real-time)**

| Tùy chọn | Ý nghĩa |
|----------|---------|
| Bật quét nền | Tự quét theo chu kỳ khi server đang chạy |
| Chu kỳ quét (phút) | Tối thiểu 5 phút |
| Làm mới giao diện (giây) | Dashboard poll `/api/monitor/status` và tải lại khi có quét mới |

**Thông báo Telegram**

| Tùy chọn | Ý nghĩa |
|----------|---------|
| Bật gửi Telegram | Bật/tắt gửi sau mỗi lần quét |
| Chỉ thông báo thay đổi chức vụ | Bật = chỉ gửi khi có biến động chức vụ trong cửa sổ báo cáo (hoặc tin mới có `Is_Change`) |
| Bot token | Token từ @BotFather |
| Chat ID | ID chat **người nhận** (bạn / nhóm), **không** phải ID bot |
| Gửi thử | Kiểm tra kết nối trước khi lưu |

**Danh sách báo chính thống:** thêm tên báo + URL trang chủ; lưu vào `config/Chinh_thong.json`.

---

## 6. File cấu hình và dữ liệu

### 6.1. `config/config.json`

Ví dụ cấu trúc (dùng placeholder, không copy key thật vào tài liệu công khai):

```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  "gemini_model": "gemini-2.5-flash",
  "auto_scan_enabled": true,
  "scan_interval_minutes": 15,
  "ui_refresh_seconds": 30,
  "google_news": {
    "language": "vi",
    "country": "VN",
    "max_results_per_target": 15,
    "filter_chinh_thong_only": true,
    "use_rss_feeds": true,
    "activity_report_hours": 24,
    "role_change_report_hours": 168,
    "ai_scan_mode": "activity",
    "use_ai": true,
    "use_gemini_analysis": true,
    "ai_verify_target": true,
    "scan_role_change": false
  },
  "targets": [
    { "name": "Tên đối tượng", "position": "Chức vụ tham chiếu" }
  ],
  "telegram": {
    "enabled": false,
    "bot_token": "",
    "chat_id": "",
    "notify_role_change_only": false
  }
}
```

| Khối / trường | Ghi chú |
|---------------|---------|
| `auto_scan_enabled` | Bật/tắt quét nền (có thể đổi trên UI) |
| `scan_interval_minutes` | Chu kỳ quét nền (phút, tối thiểu 5) |
| `ui_refresh_seconds` | Tần suất dashboard kiểm tra quét mới (10–120 giây) |
| `ai_scan_mode` | `keyword` \| `activity` \| `full` — nguồn chính cho quét thủ công + tự động |
| `gemini_model` | Model Gemini (hoặc biến môi trường `GEMINI_MODEL`) |
| `activity_report_hours` | Fallback khi UI không truyền `hours` |
| `role_change_report_hours` | Cửa sổ kênh chức vụ khi xem báo cáo |
| `telegram` | Lưu khi bấm **Lưu cài đặt** trên UI |

### 6.2. `config/Chinh_thong.json`

Mảng các object:

```json
[
  {
    "name": "VnExpress",
    "homepage_url": "https://vnexpress.net/",
    "rss_url": "https://vnexpress.net/rss/tin-moi-nhat.rss"
  }
]
```

Hệ thống lấy **domain** từ URL để so khớp link bài báo sau khi decode.

### 6.3. `data/notifications.json`

```json
{
  "channel_hoatdong": [ /* mọi tin hoạt động đã lưu */ ],
  "channel_biendong": [ /* chỉ tin có thay đổi chức vụ */ ]
}
```

Mỗi bản ghi thường có: `timestamp`, `target_name`, `target_position`, `title`, `description`, `url`, `resolved_url`, `press_name`, `news_kind`, `ai_result` (JSON từ Gemini).

### 6.4. `data/history.json`

Mảng chuỗi dạng `"Tên đối tượng|URL"` — đã gọi Gemini (kể cả bài bị loại). Tránh quét trùng URL.

**Lưu ý:** URL đã có trong `history.json` sẽ **không** được xử lý lại ở lần quét sau → `processed_new = 0` là bình thường. Telegram vẫn có thể gửi (báo cáo hoặc tin trống) tùy dữ liệu trong `notifications.json`.

### 6.5. `data/telegram_sent.json`

Mảng chuỗi khóa đã gửi Telegram, ví dụ:

| Dạng khóa | Ý nghĩa |
|-----------|---------|
| `Tên đối tượng\|https://...` | Bài báo đã gửi (không gửi lại cùng URL) |
| `Tên đối tượng\|empty_status` | Đã gửi tin trống (không gửi lại đến khi có tin mới) |

Có thể xóa file này nếu muốn **gửi lại** toàn bộ (cẩn thận trùng tin trên Telegram).

---

## 7. Luồng quét và phân loại AI

### 7.0. Ba chế độ `ai_scan_mode`

| Chế độ | Gemini | Quét biến động | Lọc `Matched_Target` | Hiển thị |
|--------|--------|----------------|----------------------|----------|
| `keyword` | Không | Không | Không (lưu hết tin tìm được) | Mọi tin đã lưu |
| `activity` | Có | Không | Có | Tin pass AI; ẩn tin `keyword_scan` cũ |
| `full` | Có | Có | Có | Giống activity + kênh biến động |

Đồng bộ cờ legacy trong config: `use_ai`, `use_gemini_analysis`, `ai_verify_target`, `scan_role_change` — tự ghi theo `ai_scan_mode` khi quét/lưu.

### 7.1. Hai loại truy vấn Google News

| Loại | Truy vấn | `news_kind` |
|------|----------|-------------|
| Hoạt động | Tên đối tượng | `hoatdong` |
| Biến động chức vụ | Tên + từ khóa (bổ nhiệm, miễn nhiệm…) | `biendong` |

Cùng một bài có thể xuất hiện ở cả hai truy vấn. Hệ thống **ưu tiên biến động chức vụ**: nếu trùng URL, bài **hoạt động** bị bỏ — chỉ phân tích **một lần** (loại `biendong`).

### 7.1.1. RSS báo chính thống (nhanh)

Khi `use_rss_feeds: true`, hệ thống đọc feed từ `Chinh_thong.json` (trường `rss_url` hoặc RSS mặc định theo domain), lọc bài có tên đối tượng. Link RSS **trực tiếp** — không cần decode Google News.

| Tối ưu | Mô tả |
|--------|--------|
| **A** | URL đã trong `history.json` → bỏ qua **trước** bước decode |
| **B** | Decode Google News **song song** + cache `data/url_decode_cache.json` |
| **C** | Gọi Gemini **song song** (`gemini_workers`, mặc định 3) |

Cấu hình trong `google_news`:

```json
"use_rss_feeds": true,
"rss_max_per_feed": 40,
"decode_workers": 4,
"gemini_workers": 3,
"decode_interval": 0.15
```

### 7.2. Kết quả Gemini (`ai_result`)

| Trường | Ý nghĩa |
|--------|---------|
| `Matched_Target` | Bài có đúng đối tượng không |
| `Is_Activity` | Có nói về hoạt động/việc làm không |
| `Is_Change` | Có thay đổi chức vụ không |
| `Summary` | Một câu tóm tắt theo quy tắc prompt |
| `Confidence` | 0–100 |

**Lưu vào hệ thống** (chế độ có Gemini): `Is_Activity` true và (nếu `ai_verify_target`) `Matched_Target` true.

- Ghi **upsert** theo URL — quét lại cùng bài thì thay bản cũ, không nhân đôi
- Luôn thêm vào `channel_hoatdong` khi đạt điều kiện
- `channel_biendong` chỉ khi chế độ **full** + xác nhận đổi chức vụ
- Chế độ **keyword**: mọi bài sau lọc báo/decode đều lưu, không gọi Gemini

**Hiển thị dashboard/API:** `filter_notifications_for_display()` lọc tin đã lưu theo **chế độ AI hiện tại** (không chỉ lọc báo chính thống).

### 7.3. Cửa sổ thời gian trên UI

Khi gọi API với `?hours=24`, hệ thống **ưu tiên 24 giờ** từ giao diện để lọc tin hiển thị — không bị `activity_report_hours` trong config ghi đè.

---

## 8. Telegram — cấu hình chi tiết

### 8.1. Tạo bot

1. Telegram → **@BotFather** → `/newbot`
2. Copy **token** → dán vào cài đặt

### 8.2. Lấy Chat ID (chat cá nhân)

1. Mở bot của bạn → **Start** (`/start`)
2. Trình duyệt: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Tìm `"chat":{"id": 123456789` → đó là Chat ID (số dương)

### 8.3. Nhóm / kênh

- Thêm bot vào nhóm, gửi một tin trong nhóm
- Gọi lại `getUpdates` → ID nhóm thường **âm** (ví dụ `-1001234567890`)

### 8.4. Lỗi thường gặp

| Thông báo | Nguyên nhân | Cách xử lý |
|-----------|-------------|------------|
| `can't send messages to the bot` | Chat ID là ID của bot | Dùng ID người/nhóm nhận |
| `Chat not found` | Sai Chat ID | Kiểm tra lại getUpdates |
| `Unauthorized` | Sai token | Tạo lại token BotFather |
| `bot was blocked` | Đã chặn bot | Mở bot, bấm Start |

### 8.5. Khi nào gửi tin? (sau mỗi lần quét)

Telegram bật → với **mỗi đối tượng**, tối đa **một tin** mỗi lần quét (tự động hoặc thủ công). **Không gửi lại** báo cáo đầy đủ nếu tin đã gửi trước đó.

| Tình huống | Tin gửi đi |
|------------|------------|
| Có **tin mới** lần này (URL chưa gửi Telegram) | **Báo cáo đầy đủ** (một lần), rồi ghi nhớ URL |
| Không tin mới, nhưng vẫn còn hoạt động cũ trong cửa sổ 24h | **Không gửi** (tránh spam) |
| Không tin mới, không hoạt động / biến động trong cửa sổ | Tin **trống** (*Không có hoạt động*) — **một lần** cho đến khi có tin mới |
| Đã gửi tin trống rồi, các lần quét sau vẫn không có gì | **Không gửi lại** |

**Tùy chọn “Chỉ thông báo thay đổi chức vụ”:** chỉ áp dụng khi có **tin mới**; tin trống vẫn gửi khi không có gì trong cửa sổ.

### 8.5.1. Quét tự động nền

- Chu kỳ: `scan_interval_minutes` (tối thiểu **5 phút**), đọc lại từ `config.json` **mỗi vòng**.
- Thời gian chờ tính từ **đầu chu kỳ** (sau khi quét xong, chờ phần còn lại của chu kỳ).
- **Lưu cài đặt** → chu kỳ mới áp dụng ngay (không cần khởi động lại server).
- Một lần quét có thể kéo dài (GNews + AI) — lần quét tiếp theo không bắt đầu cho đến khi hết chu kỳ.

### 8.6. Mẫu nội dung tin nhắn

Tiêu đề chung mỗi tin:

```text
📋 Báo cáo giám sát — 18/05/2026 15:30
```

**Tin trống** (không có hoạt động / biến động trong cửa sổ):

```text
1. Đồng chí Tô Lâm:
- Thay đổi chức vụ: Không
- Hoạt động trong 24 giờ: Không có hoạt động
```

**Báo cáo đầy đủ:**

```text
1. Đồng chí Tô Lâm:
- Thay đổi chức vụ: Có
- Hoạt động trong 24 giờ:
	+ Hoạt động 1: Tóm tắt từ AI hoặc tiêu đề bài
	Link bài: https://...
	+ Hoạt động 2: ...
	Link bài: https://...
```

Một lượt quét: tối đa **một digest gộp** (có thể **chia nhiều tin Telegram** nếu nội dung HTML vượt ~4096 ký tự). Nhiều đối tượng có tin mới → gộp trong cùng digest theo từng block đối tượng.

### 8.7. Log terminal khi gửi Telegram

| Dòng log | Ý nghĩa |
|----------|---------|
| `[TELEGRAM] đã gửi (trống): Tên` | Tin trống đã gửi |
| `[TELEGRAM] đã gửi báo cáo: Tên (N hoạt động / 24h)` | Báo cáo đầy đủ |
| `[TELEGRAM] FAIL ...` | Lỗi API — xem mục 8.4 |

Trên dashboard, sau quét có thể thấy: `Telegram: 2 tin (1 trống)` — số trong ngoặc là tin trống.

---

## 9. API HTTP (tham khảo)

Base: `http://localhost:8000`

| Method | Đường dẫn | Mô tả |
|--------|-----------|--------|
| GET | `/` | Dashboard |
| GET | `/target?name=...&hours=24` | Trang chi tiết |
| GET | `/api/targets` | Danh sách đối tượng (không trả API key) |
| GET | `/config` | Config đã ẩn secret (tương thích) |
| POST | `/config/targets/add` | Thêm/sửa đối tượng (`original_name` khi sửa) |
| POST | `/config/targets/delete` | Xóa đối tượng |
| GET | `/api/data/stats` | Thống kê dữ liệu (xóa có chọn trong Cài đặt) |
| POST | `/api/data/clear` | Xóa dữ liệu (`confirm: "XOA"`) |
| GET | `/notifications` | Đọc notifications.json |
| GET | `/api/targets/summary?hours=24` | Tóm tắt tất cả đối tượng |
| GET | `/api/target/detail?name=...&hours=24` | Chi tiết một đối tượng |
| GET | `/api/target/export.json?name=...&hours=24` | Tải JSON |
| GET | `/api/settings` | Cài đặt + danh sách báo |
| POST | `/api/settings` | Lưu cài đặt; chỉ `ai_scan_mode` → quét lại nếu rảnh |
| POST | `/api/settings/telegram-test` | Gửi tin thử Telegram |
| GET | `/api/monitor/status` | Trạng thái quét (`is_scanning`, chế độ AI, lần cuối…) |
| POST | `/monitor/run` | Quét thủ công. Body: `{ "scan_hours": 24, "target_name": "…", "ignore_history": true }`. **409** nếu đang quét |

Phản hồi quét thành công (rút gọn):

```json
{
  "success": true,
  "processed_new": 0,
  "scanned_target": "Tô Lâm",
  "scanned_targets": ["Tô Lâm"],
  "telegram_sent": 2,
  "telegram_sent_empty": 2,
  "telegram_skipped_dup": 0,
  "telegram_skipped_filter": 0,
  "telegram_errors": [],
  "telegram_enabled": true,
  "skipped_history_dup": 15,
  "history_size": 150,
  "timestamp": "2026-05-18T14:00:00"
}
```

| Trường | Ý nghĩa |
|--------|---------|
| `processed_new` | Số bài **mới** lưu trong lần quét này |
| `scanned_target` | Tên đối tượng khi quét riêng; `null` khi quét tất cả |
| `scanned_targets` | Danh sách đối tượng thực sự được quét |
| `telegram_sent` | Số tin Telegram đã gửi (trống + đầy đủ) |
| `telegram_sent_empty` | Trong đó bao nhiêu tin **trống** |
| `skipped_history_dup` | URL bỏ qua vì đã có trong `history.json` |

**Ví dụ quét riêng (curl):**

```bash
curl -X POST http://localhost:8000/monitor/run ^
  -H "Content-Type: application/json" ^
  -d "{\"scan_hours\": 24, \"target_name\": \"Tô Lâm\"}"
```

---

## 10. Module mã nguồn (tóm tắt)

|         File             |                      Vai trò                         |
|--------------------------|------------------------------------------------------|
| `He_thong.py`            | Khởi chạy Flask `0.0.0.0:8000`                       |
| `src/web.py`             | Route, API, render HTML                              |
| `src/auto_scanner.py`    | Vòng lặp quét nền, khóa tránh quét chồng, `/api/monitor/status` |
| `src/monitor.py`         | `process_once()`, Gemini, GNews, RSS, báo cáo        |
| `src/telegram_notify.py` | `format_target_digest`, `format_target_empty`, `notify_records` |
| `src/press_whitelist.py` | `PressWhitelist.from_file`, `is_allowed_url`         |
| `src/json_io.py`         | `read_json` / `write_json` — khóa theo file, thử lại WinError 32 |
| `src/common.py`          | `as_bool`, `parse_ts`, `article_link_url`, `is_google_news_url` |
| `src/data_store.py`      | Thống kê / xóa `notifications`, `history`, Telegram, cache |
| `src/paths.py`           | Đường dẫn; `migrate_legacy_files()` gọi từ `He_thong.py` |

Kiểm tra hệ thống:

```bash
python scripts/system_check.py
python scripts/system_check.py --live
# hoặc: python health_check.py
```

Chạy thử logic quét từ dòng lệnh (không qua web):

```bash
python -m src.monitor
```

---

## 11. Bảo mật và vận hành

- **Không** chia sẻ `config/config.json` (chứa API key Gemini, token Telegram).
- **Không** commit file config có key thật lên Git công khai.
- Sau khi sửa code Python: **khởi động lại** `python He_thong.py` (chỉ chạy **một** tiến trình trên cổng 8000).
- Sau khi sửa HTML/JS/CSS: **Ctrl+F5** trên trình duyệt (template có tham số `?v=` để bust cache).
- Giao diện sáng/tối: file `static/js/theme.js`, CSS block `html[data-theme="light"]` trong `isr-theme.css`.
- File `emip.v3.js` (nếu có) là script **Qime/Telegram riêng** trên trình duyệt; hệ thống giám sát **không đọc** file đó — cấu hình Telegram hoàn toàn qua UI/`config.json`.

---

## 12. Khắc phục sự cố

|       Triệu chứng      |                         Hướng xử lý                               |
|------------------------|-------------------------------------------------------------------|
| `Thiếu gemini_api_key` | Điền key trong `config/config.json`                               |
| Quét không có tin mới  | Bình thường nếu URL đã trong `history.json`; Telegram vẫn có thể gửi tin trống (mục 8.5) |
| Không thấy tin Telegram | Kiểm tra **Bật gửi Telegram** + token/chat_id; **Gửi thử**; khởi động lại server sau sửa code |
| Chỉ thấy `[SCAN]`, không `[ARTICLE]` | Không có URL mới — xem `telegram_sent_empty` trong phản hồi quét |
| Quét không có tin      | Tăng `max_results_per_target`; tắt tạm lọc báo chính thống để thử |
| UI vẫn 24h dù chọn 1h  | Khởi động lại server; Ctrl+F5; kiểm tra đã bấm ✓ áp dụng giờ      |
| UI cũ (không thấy nút mới) | Nhiều server trùng cổng 8000 — dừng hết (`Ctrl+C`), chạy lại **một** lần `python He_thong.py`; Ctrl+F5 |
| Không thấy **Giao diện sáng** | Nút ở sidebar, **dưới Cài đặt hệ thống**; Ctrl+F5 hoặc tab ẩn danh |
| Quét riêng báo lỗi đối tượng | Tên `target_name` phải khớp chính xác với `config.json` |
| Quét tự động dừng sau 1 lần | Windows lỗi in tiếng Việt (`charmap`) làm thread nền chết — khởi động lại server (bản mới đã sửa); xem `last_scan_ok` / `last_error` tại `/api/monitor/status` |
| Lưu đối tượng lỗi 404  | Khởi động lại server sau khi cập nhật code                        |
| Lưu cài đặt lỗi 500 / PermissionError | Đóng tab đang mở `config.json` trong editor; khởi động lại server (đã có khóa ghi file) |
| Đổi chế độ AI mà danh sách không đổi | Đợi quét lại xong; hoặc bấm **Quét tất cả** sau khi hết trạng thái «Đang quét» |
| Telegram FAIL parse HTML | Báo cáo quá dài — bản mới tự chia nhiều tin; cập nhật code và quét lại |
| Gemini 429             | Hết quota; đợi hoặc đổi model/key                                 |
| Telegram 400           | Xem mục 8.4                                                       |

Log quét in trong terminal khi chạy `He_thong.py` (dòng `[SCAN]`, `[ARTICLE]`, `[AI]`, `[TELEGRAM]`).

---

## 13. Phụ lục — Di chuyển từ bản cũ (file ở thư mục gốc)

Nếu trước đây có `config.json`, `notifications.json` ngay trong `Phan_mem/`:

- Lần chạy đầu, `src/paths.py` **tự copy** sang `config/` và `data/` nếu chưa có file mới.
- Nên dùng đường dẫn mới: `config/config.json`, `data/notifications.json`.

---

*Tài liệu cập nhật: tháng 05/2026 — ba chế độ `ai_scan_mode`, quét lại khi đổi chế độ, khóa nút quét khi `is_scanning`, API `/api/targets`, Telegram chia tin dài, `src/common.py` + `json_io` an toàn Windows.*
