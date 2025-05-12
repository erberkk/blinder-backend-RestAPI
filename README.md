# Blinder Backend

[English](#english) | [Türkçe](#turkish)

## English

### Overview
Blinder Backend is a Flask-based REST API service that provides various functionalities including authentication, Spotify integration, restaurant management, matching system, and messaging features.

### Features
- User Authentication with JWT
- Spotify Integration
- Restaurant Management
- Matching System
- Real-time Messaging
- CORS Support
- Automatic JWT Token Refresh

### Technical Stack
- Python
- Flask
- Flask-JWT-Extended
- Flask-CORS

### Project Structure
```
blinder-backend/
├── main.py              # Main application entry point
├── config.py            # Configuration settings
├── auth/               # Authentication related endpoints
├── spotify/            # Spotify integration endpoints
├── restaurants/        # Restaurant management endpoints
├── matches/           # Matching system endpoints
└── message/           # Messaging system endpoints
```

### Setup and Installation
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables in `config.py`
4. Run the application:
   ```bash
   python main.py
   ```

### API Endpoints
- `/auth/*` - Authentication endpoints
- `/spotify/*` - Spotify integration endpoints
- `/restaurant/*` - Restaurant management endpoints
- `/match/*` - Matching system endpoints
- `/message/*` - Messaging system endpoints

### Security
- JWT-based authentication
- CORS enabled with configurable origins
- Automatic token refresh mechanism

---

## Turkish

### Genel Bakış
Blinder Backend, kimlik doğrulama, Spotify entegrasyonu, restoran yönetimi, eşleştirme sistemi ve mesajlaşma özellikleri sunan Flask tabanlı bir REST API servisidir.

### Özellikler
- JWT ile Kullanıcı Kimlik Doğrulama
- Spotify Entegrasyonu
- Restoran Yönetimi
- Eşleştirme Sistemi
- Gerçek Zamanlı Mesajlaşma
- CORS Desteği
- Otomatik JWT Token Yenileme

### Teknik Altyapı
- Python
- Flask
- Flask-JWT-Extended
- Flask-CORS

### Proje Yapısı
```
blinder-backend/
├── main.py              # Ana uygulama giriş noktası
├── config.py            # Yapılandırma ayarları
├── auth/               # Kimlik doğrulama ile ilgili endpoint'ler
├── spotify/            # Spotify entegrasyonu endpoint'leri
├── restaurants/        # Restoran yönetimi endpoint'leri
├── matches/           # Eşleştirme sistemi endpoint'leri
└── message/           # Mesajlaşma sistemi endpoint'leri
```

### Kurulum
1. Projeyi klonlayın
2. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
3. `config.py` dosyasında ortam değişkenlerini yapılandırın
4. Uygulamayı çalıştırın:
   ```bash
   python main.py
   ```

### API Endpoint'leri
- `/auth/*` - Kimlik doğrulama endpoint'leri
- `/spotify/*` - Spotify entegrasyonu endpoint'leri
- `/restaurant/*` - Restoran yönetimi endpoint'leri
- `/match/*` - Eşleştirme sistemi endpoint'leri
- `/message/*` - Mesajlaşma sistemi endpoint'leri

### Güvenlik
- JWT tabanlı kimlik doğrulama
- Yapılandırılabilir origin'ler ile CORS desteği
- Otomatik token yenileme mekanizması 