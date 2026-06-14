"""
worker.py
─────────────────────────────────────────────────────────────────────────────
Redis Queue Worker — Carbon-Aware Task Re-Executor.

Çalışma mantığı:
  1. Kuyruktan iş alır (BLPOP).
  2. Zaman kontrolü yapar (retry_after).
  3. Redis'ten güncel karbon durumunu okur (current_carbon_state).
  4. Karbon eşiğin üzerindeyse görevi kuyruğa geri itip bekler.
  5. Koşullar uygunsa OpenWhisk action'ı tetikler.
"""

import json
import logging
import os
import sys
import time
import traceback
import redis

# Proje kök dizinini path'e ekle (Executor'a erişim için)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append("/app")

from executor.executor import OpenWhiskInvoker

# ── Logging Yapılandırması ──────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/worker.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Yapılandırma ─────────────────────────────────────────────────────────────
IS_DOCKER = os.path.exists("/.dockerenv")
DEFAULT_REDIS_HOST = "redis" if IS_DOCKER else "localhost"
REDIS_HOST = os.getenv("REDIS_HOST", DEFAULT_REDIS_HOST)
QUEUE_NAME = "carbon_task_queue"

def get_redis_connection() -> redis.Redis:
    """Redis'e bağlanır, başarısız olursa 5 saniyede bir yeniden dener."""
    while True:
        try:
            r = redis.Redis(
                host=REDIS_HOST,
                port=6379,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            r.ping()
            logger.info("[Worker] Redis connected at %s:6379", REDIS_HOST)
            return r
        except Exception as e:
            logger.warning("[Worker] Redis bağlantısı başarısız: %s — 5sn sonra tekrar.", e)
            time.sleep(5)

def log_execution_event(task_name: str, zone: str, carbon: float, threshold: float, duration_ms: float) -> None:
    from config import LOG_FILE_JSON, LOG_FILE_CSV
    import csv
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).isoformat()

    # Log to JSON
    record = {
        "timestamp":        timestamp,
        "zone":             zone,
        "carbon_intensity": carbon,
        "threshold":        threshold,
        "decision":         "execute",
        "reason":           "Delayed task execution",
        "execution_status": "executed",
        "duration_ms":      duration_ms,
        "action_name":      "data_processor",
        "task_name":        task_name,
        "error":            None,
    }
    try:
        with open(LOG_FILE_JSON, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        logger.warning("[Worker] JSON loglama hatası: %s", e)

    # Log to CSV
    _CSV_FIELDS = [
        "timestamp", "zone", "carbon_intensity", "threshold", "decision",
        "delay_seconds", "execution_status", "execution_duration_ms",
        "action_name", "task_name", "error"
    ]
    row = {
        "timestamp":             timestamp,
        "zone":                  zone,
        "carbon_intensity":      carbon,
        "threshold":             threshold,
        "decision":              "execute",
        "delay_seconds":         "",
        "execution_status":      "executed",
        "execution_duration_ms": duration_ms,
        "action_name":           "data_processor",
        "task_name":             task_name,
        "error":                 "",
    }
    try:
        with open(LOG_FILE_CSV, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=_CSV_FIELDS).writerow(row)
    except Exception as e:
        logger.warning("[Worker] CSV loglama hatası: %s", e)

def check_and_clear_logs(r: redis.Redis) -> None:
    try:
        if r.get("clear_worker_logs") == "true":
            r.delete("clear_worker_logs")
            with open("logs/worker.log", "w", encoding="utf-8") as f:
                pass
            logger.info("[Worker] Log dosyası sıfırlandı.")
    except Exception as e:
        logger.warning("[Worker] Log sıfırlama hatası: %s", e)

def run_worker() -> None:
    logger.info("[Worker] ═══════════════════════════════════════")
    logger.info("[Worker] Carbon-Aware Queue Worker başlatıldı.")
    logger.info("[Worker] Kuyruk: %s", QUEUE_NAME)
    logger.info("[Worker] ═══════════════════════════════════════")

    r          = get_redis_connection()
    ow_invoker = OpenWhiskInvoker()

    while True:
        try:
            check_and_clear_logs(r)

            # 1. Kuyruktan iş al (Zaman aşımı 1sn)
            raw = r.blpop(QUEUE_NAME, timeout=1)

            check_and_clear_logs(r)

            if raw is None:
                continue

            _, data = raw
            task = json.loads(data)

            action_name   = task.get("action_name", "data_processor")
            params        = task.get("params", {})
            retry_after   = task.get("retry_after", 0)
            orig_carbon   = task.get("carbon_at_delay", "?")
            orig_thresh   = task.get("threshold", "?")
            task_name     = params.get("task_name", "N/A")

            now = time.time()

            # 2. Zaman Kontrolü (Gecikme süresi doldu mu?)
            if now < retry_after:
                wait_secs = retry_after - now
                logger.info("[Worker] ⏳ [%s] Zamanı gelmedi (%.0fsn kaldı). Geri itildi.", task_name, wait_secs)
                r.rpush(QUEUE_NAME, json.dumps(task))
                time.sleep(min(wait_secs, 5))
                continue

            # 3. Karbon Kontrolü (Anlık karbon verisi uygun mu?)
            raw_state = r.get("current_carbon_state")
            if raw_state:
                state = json.loads(raw_state)
                curr_intensity = float(state["intensity"])
                curr_threshold = float(state["threshold"])

                if curr_intensity > curr_threshold:
                    logger.info(
                        "[Worker] ⏸️ [%s] Karbon hala yüksek (%.1f > %.1f). Kuyruğa geri itildi.",
                        task_name, curr_intensity, curr_threshold
                    )
                    r.rpush(QUEUE_NAME, json.dumps(task))
                    time.sleep(5)  # Karbonun düşmesi için kısa bir mola
                    continue
                
                # Karbon uygunsa, log için güncel veriyi hazırla
                display_carbon = curr_intensity
            else:
                # Redis'te state yoksa orijinal veriyi kullan (fallback)
                logger.warning("[Worker] ⚠️ [%s] Güncel karbon verisi Redis'te bulunamadı, bekletiliyor.", task_name)
                r.rpush(QUEUE_NAME, json.dumps(task))
                time.sleep(5)
                continue

            # 4. Çalıştırma (Hem zaman hem karbon uygun)
            logger.info(
                "[Worker] 🟢 Koşullar uygun, [%s] çalıştırılıyor: action=%s (Karbon: %.1f)",
                task_name, action_name, display_carbon
            )
            
            result = ow_invoker.invoke(action_name, params)
            
            duration_ms = result.get("duration_ms", 0.0)
            if duration_ms in (None, "", "N/A"):
                duration_ms = 0.0
            else:
                try:
                    duration_ms = float(duration_ms)
                except (TypeError, ValueError):
                    duration_ms = 0.0

            task_zone = task.get("zone", "DE")
            log_execution_event(task_name, task_zone, display_carbon, curr_threshold, duration_ms)

            # Sonuç Loglama
            logger.info(
                "[Worker] ✅ [%s] Tamamlandı: status=%s  duration=%s ms",
                task_name,
                result.get("status", "ok"),
                result.get("duration_ms", "N/A"),
            )

        except json.JSONDecodeError as e:
            logger.error("[Worker] JSON parse hatası: %s", e)
        except redis.ConnectionError as e:
            logger.error("[Worker] Redis bağlantısı kesildi: %s — yeniden bağlanılıyor.", e)
            r = get_redis_connection()
        except Exception as e:
            logger.error("[Worker] Beklenmedik hata: %s", e)
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    run_worker()