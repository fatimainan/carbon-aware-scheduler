
**İzole 3 Mod:** Simülasyon, Sandbox ve Live olmak üzere 3 farklı mod vardır. Her modun karbon durumları, logları, grafikleri ve arayüzleri tamamen birbirinden izole çalışır (birbirine karışmaz).

---

## 📊 Dashboard Arayüz Linkleri

* **Simülasyon Dashboard'u:** http://localhost:5173/?mode=sim
* **Sandbox (Geliştirme) Dashboard'u:** http://localhost:5173/?mode=sandbox
* **Canlı (Live) Dashboard:** http://localhost:5173/?mode=live

---

## 🚀 Örnek Ülke Çalıştırma Komutları (3 Farklı Mod)

### 🇨🇭 1. İsviçre (Bölge Kodu: `CH`)

* **Simülasyon Modu (`sim`):**
  *(Hazır senaryo verilerini kullanarak test etmenizi sağlar. API Key gerektirmez).*
  ```bash
  python3 main.py --mode sim --zone CH --cycles 5
  ```
* **Sandbox Modu (`sandbox`):**
  *(Gerçek zamanlı İsviçre şebeke verisini çeker. Geliştirme ortamıdır, her çalıştırmada logları temizler).*
  ```bash
  python3 main.py --mode sandbox --zone CH --cycles 5 --interval 1
  ```
* **Canlı Mod (`live`):**
  *(Gerçek zamanlı İsviçre şebeke verisini çeker. Raporlama için geçmiş logları asla silmez).*
  ```bash
  python3 main.py --mode live --zone CH --cycles 5 --interval 1
  ```

---

### 🇩🇪 2. Almanya (Bölge Kodu: `DE`)

* **Simülasyon Modu (`sim`):**
  ```bash
  python3 main.py --mode sim --zone DE --cycles 5
  ```
* **Sandbox Modu (`sandbox`):**
  ```bash
  python3 main.py --mode sandbox --zone DE --cycles 5 --interval 1
  ```
* **Canlı Mod (`live`):**
  ```bash
  python3 main.py --mode live --zone DE --cycles 5 --interval 1
  ```
