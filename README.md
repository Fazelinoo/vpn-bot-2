# 🤖 ربات فروش VPN — fazelino.lol

ربات تلگرامی فروش کانفیگ VPN با **Python 3.11+** و **aiogram 3.x** (async)، متصل به پنل **3x-ui** با API Token.

## ✨ قابلیت‌ها

### کاربر
- 🎁 **تست رایگان**: ۱ گیگ / ۱ روز — هر ۲۴ ساعت یک‌بار
- 🛒 **خرید پلن** بر اساس حجم (۱۰، ۲۰، ۵۰، ۱۰۰ گیگ و ...)
- 💳 **پرداخت دستی** (کارت به کارت)
- 📤 ارسال فیش و تایید دستی توسط ادمین
- 🔗 ارسال **Subscription Link** + **QR Code**
- 📊 مشاهده حجم باقی‌مانده، انقضا و وضعیت

### ادمین (`/admin`)
- 📊 آمار: کاربران، فروش، درآمد
- 💰 تنظیم قیمت هر گیگ
- 🛒 فعال/غیرفعال فروش
- 🎁 فعال/غیرفعال تست رایگان
- 📡 انتخاب Inbound
- 🧾 تایید/رد فیش‌ها
- ⛔ متوقف کردن اکانت
- 👥 لیست و جستجوی کاربران

---

## 📁 ساختار پروژه

```
vpn-bot/
├── main.py                 # نقطه ورود
├── requirements.txt
├── .env.example
├── ecosystem.config.js     # PM2
├── deploy/
│   └── vpn-bot.service     # systemd
├── bot/
│   ├── config.py           # تنظیمات
│   ├── database/           # SQLAlchemy models + CRUD
│   ├── services/           # 3x-ui + QR
│   ├── handlers/           # user + admin handlers
│   ├── keyboards/          # inline keyboards
│   ├── middlewares/        # throttling + DB session
│   ├── filters/            # admin filter
│   ├── states/             # FSM
│   └── utils/              # helpers + logging
├── data/                   # SQLite DB (auto-created)
└── logs/                   # log files
```

---

## 1️⃣ ساخت ربات در BotFather

1. در تلگرام به [@BotFather](https://t.me/BotFather) بروید.
2. دستور `/newbot` را بزنید.
3. یک **نام** (مثلاً `Fazelino VPN Shop`) و **username** (مثلاً `FazelinoVPN_bot`) انتخاب کنید.
4. **Token** دریافتی را کپی کنید — در `.env` قرار می‌دهید.
5. (اختیاری) `/setdescription` و `/setabouttext` برای توضیحات ربات.
6. (اختیاری) `/setcommands`:

```
start - شروع ربات
admin - پنل مدیریت (فقط ادمین)
```

---

## 2️⃣ نصب پیش‌نیازها

### Ubuntu / Debian

```bash
# به‌روزرسانی سیستم
sudo apt update && sudo apt upgrade -y

# Python 3.11+ و pip
sudo apt install -y python3 python3-pip python3-venv git

# بررسی نسخه
python3 --version   # باید 3.11 یا بالاتر باشد
```

### کلون و نصب

```bash
# آپلود پروژه به سرور (یا git clone)
cd /opt
sudo mkdir -p vpn-bot
sudo chown $USER:$USER vpn-bot
cd vpn-bot

# کپی فایل‌های پروژه به این مسیر...

# محیط مجازی
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3️⃣ تنظیم `.env`

```bash
cp .env.example .env
nano .env
```

| متغیر | توضیح |
|--------|--------|
| `BOT_TOKEN` | توکن ربات از BotFather |
| `ADMIN_IDS` | آیدی عددی ادمین‌ها (با کاما) — از [@userinfobot](https://t.me/userinfobot) بگیرید |
| `XUI_HOST` | آدرس پنل بدون `/panel` — مثال: `https://vp2.fazelino.lol:2053/DX9BkswG96YruEosP4` |
| `XUI_TOKEN` | API Token پنل 3x-ui |
| `XUI_USE_TLS_VERIFY` | `false` برای گواهی self-signed |
| `SUBSCRIPTION_BASE_URL` | پایه URL سابscription (معمولاً همان XUI_HOST) |
| `CARD_NUMBER` | شماره کارت برای پرداخت |
| `DATABASE_URL` | SQLite یا PostgreSQL |

### مثال `.env`

```env
BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ADMIN_IDS=123456789

XUI_HOST=https://vp2.fazelino.lol:2053/DX9BkswG96YruEosP4
XUI_TOKEN=aotyFQPLQOpFfuzScqyUbTVS2dWYQ8B4NSSmqvKY6zfPBmD6
XUI_USE_TLS_VERIFY=false

SUBSCRIPTION_BASE_URL=https://vp2.fazelino.lol:2053/DX9BkswG96YruEosP4
SUBSCRIPTION_DOMAIN=fazelino.lol

CARD_NUMBER=6037997501682950
CARD_HOLDER=فروشگاه VPN

DATABASE_URL=sqlite+aiosqlite:///./data/bot.db
DEFAULT_PLAN_DAYS=30
```

### تست محلی

```bash
source venv/bin/activate
python main.py
```

---

## 4️⃣ اجرا روی سرور Ubuntu

### روش A: PM2 (پیشنهادی)

```bash
# نصب Node.js و PM2
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2

cd /opt/vpn-bot
source venv/bin/activate

# ویرایش مسیر در ecosystem.config.js
nano ecosystem.config.js

# اجرا
pm2 start ecosystem.config.js
pm2 save
pm2 startup   # دستور خروجی را اجرا کنید

# مانیتورینگ
pm2 status
pm2 logs vpn-bot
```

### روش B: systemd

```bash
sudo cp deploy/vpn-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/vpn-bot.service   # User و مسیر را تنظیم کنید

sudo systemctl daemon-reload
sudo systemctl enable vpn-bot
sudo systemctl start vpn-bot
sudo systemctl status vpn-bot

# لاگ
journalctl -u vpn-bot -f
```

---

## 5️⃣ آپدیت و بکاپ

### بکاپ

```bash
# دیتابیس SQLite
cp /opt/vpn-bot/data/bot.db /opt/vpn-bot/backups/bot_$(date +%Y%m%d).db

# PostgreSQL
pg_dump -U user vpnbot > backup_$(date +%Y%m%d).sql

# فایل .env (مهم!)
cp /opt/vpn-bot/.env /opt/vpn-bot/backups/env_backup
```

**Cron بکاپ روزانه:**

```bash
crontab -e
# هر شب ساعت ۳
0 3 * * * cp /opt/vpn-bot/data/bot.db /opt/vpn-bot/backups/bot_$(date +\%Y\%m\%d).db
```

### آپدیت ربات

```bash
cd /opt/vpn-bot

# PM2
pm2 stop vpn-bot

# systemd
sudo systemctl stop vpn-bot

# بکاپ
cp data/bot.db backups/bot_before_update.db

# دریافت کد جدید
# git pull  یا  آپلود فایل‌های جدید

source venv/bin/activate
pip install -r requirements.txt --upgrade

# PM2
pm2 restart vpn-bot

# systemd
sudo systemctl start vpn-bot
```

---

## 🔧 تنظیمات اولیه پس از نصب

1. ربات را `/start` کنید.
2. با اکانت ادمین `/admin` بزنید.
3. **Inbound** مناسب را انتخاب کنید.
4. **قیمت هر گیگ** را تنظیم کنید.
5. **پلن‌ها** را تنظیم کنید (مثلاً `10,20,50,100`).

---

## 🗄️ PostgreSQL (اختیاری)

```bash
sudo apt install -y postgresql postgresql-contrib
sudo -u postgres createuser vpnbot -P
sudo -u postgres createdb vpnbot -O vpnbot
```

در `.env`:

```env
DATABASE_URL=postgresql+asyncpg://vpnbot:PASSWORD@localhost:5432/vpnbot
```

---

## 🐛 عیب‌یابی

| مشکل | راه‌حل |
|------|--------|
| خطای اتصال به پنل | `XUI_HOST` و `XUI_TOKEN` را بررسی کنید؛ `XUI_USE_TLS_VERIFY=false` |
| ربات پاسخ نمی‌دهد | `pm2 logs` یا `journalctl -u vpn-bot` |
| ادمین دسترسی ندارد | `ADMIN_IDS` را با آیدی عددی خودتان تنظیم کنید |
| Subscription کار نمی‌کند | `SUBSCRIPTION_BASE_URL` و `sub_id` در پنل را بررسی کنید |

---

## 📜 لایسنس

MIT — استفاده آزاد با ذکر منبع.

## 🔗 منابع

- [aiogram 3.x](https://docs.aiogram.dev/)
- [py3xui](https://github.com/iwatkot/py3xui)
- [3x-ui](https://github.com/MHSanaei/3x-ui)
- [نمونه: 3xui-shop](https://github.com/snoups/3xui-shop)
