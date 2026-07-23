# 📚 Manga & Webtoon Reader Web Application

Modern ve dinamik bir **Manga / Webtoon Okuma Platformu** web uygulaması. Django 6.0 mimarisi ile geliştirilmiş olup Google OAuth girişi, bölüm okuyucu, yorumlar, favoriler ve gelişmiş kullanıcı yönetimi sunar.

---

## 🚀 Özellikler

- 📖 **Manga ve Webtoon Okuma Modu:** Kesintisiz ve responsive okuma deneyimi.
- 🎨 **Modern Arayüz:** Kullanıcı dostu dinamik tasarım ve bölüm takip sistemleri.
- 📧 **E-posta Bildirim Hizmeti:** Şifre sıfırlama ve duyurular için Gmail SMTP desteği.
- 🛠️ **Güvenli Çevre Yapılandırması:** `.env` ile gizli anahtarların korunması.

---

## 🛠️ Kurulum ve Çalıştırma Rehberi

### 1. Repoyu Klonlayın
```bash
git clone https://github.com/KULLANICI_ADI/PROJECT_NAME.git
cd PROJECT_NAME
```

### 2. Sanal Ortamı (Virtual Environment) Oluşturun ve Aktifleştirin
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Çevre Değişkenlerini (`.env`) Hazırlayın
Kök dizinde `.env.example` dosyasını kopyalayarak `.env` adında yeni bir dosya oluşturun ve kendi bilgilerinizi girin:

```ini
SECRET_KEY=your-custom-secret-key
DEBUG=True
ALLOWED_HOSTS=*

EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 5. Veritabanı Migrasyonlarını Çalıştırın
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Süper Kullanıcı (Admin) Oluşturun (Opsiyonel)
```bash
python manage.py createsuperuser
```

### 7. Geliştirme Sunucusunu Başlatın
```bash
python manage.py runserver
```
Uygulamaya tarayıcınızdan `http://127.0.0.1:8000/` adresinden ulaşabilirsiniz.

---

## ⚙️ Proje Yapısı

```text
├── core/              # Django ana proje ayarları (settings, urls, wsgi/asgi)
├── manga/             # Manga uygulaması (views, models, forms, templates, static)
├── media/             # Yüklenen medya ve görsel içerikler (git-ignored)
├── templates/         # Genel şablonlar
├── .env.example       # Örnek çevre değişkenleri dosyası
├── .gitignore         # Git takip dışı dosyalar listesi
├── manage.py          # Django yönetim komut dosyası
└── requirements.txt   # Python paket bağımlılıkları
```

---

## 📝 Lisans
Bu proje açık kaynaklıdır. Dilediğiniz gibi geliştirebilir ve özelleştirebilirsiniz.
