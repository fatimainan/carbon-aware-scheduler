# Python'ın hafif bir versiyonunu kullanıyoruz
FROM python:3.11-slim

# Konteyner içindeki çalışma dizinini belirle
WORKDIR /app

# Önce sadece gereksinim dosyasını kopyalıyoruz (Docker build'i hızlandırmak için)
COPY requirements.txt .

# Kütüphaneleri yükle
RUN pip install --no-cache-dir -r requirements.txt

# Şimdi tüm proje dosyalarını kopyala
COPY . .

# Worker'ı başlat
CMD ["python", "worker.py"]