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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Yapılandırma ─────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
QUEUE_NAME = "carbon_task_queue"

def get_redis_connection() -> redis.Redis:
    """Redis'e bağlanır, başarısız olursa 5 saniyede bir yeniden dener."""
    while True:
        try:
            r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
            r.ping()
            logger.info("[Worker] Redis connected at %s:6379", REDIS_HOST)
            return r
        except Exception as e:
            logger.warning("[Worker] Redis bağlantısı başarısız: %s — 5sn sonra tekrar.", e)
            time.sleep(5)

def run_worker() -> None:
    logger.info("[Worker] ═══════════════════════════════════════")
    logger.info("[Worker] Carbon-Aware Queue Worker başlatıldı.")
    logger.info("[Worker] Kuyruk: %s", QUEUE_NAME)
    logger.info("[Worker] ═══════════════════════════════════════")

    r          = get_redis_connection()
    ow_invoker = OpenWhiskInvoker()

    while True:
        try:
            # 1. Kuyruktan iş al (Zaman aşımı 10sn)
            raw = r.blpop(QUEUE_NAME, timeout=10)
            if raw is None:
                continue

            _, data = raw
            task = json.loads(data)

            action_name   = task.get("action_name", "data_processor")
            params        = task.get("params", {})
            retry_after   = task.get("retry_after", 0)
            orig_carbon   = task.get("carbon_at_delay", "?")
            orig_thresh   = task.get("threshold", "?")

            now = time.time()

            # 2. Zaman Kontrolü (Gecikme süresi doldu mu?)
            if now < retry_after:
                wait_secs = retry_after - now
                logger.info("[Worker] ⏳ Zamanı gelmedi (%.0fsn kaldı). Geri itildi.", wait_secs)
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
                        "[Worker] ⏸️ Karbon hala yüksek (%.1f > %.1f). Kuyruğa geri itildi.",
                        curr_intensity, curr_threshold
                    )
                    r.rpush(QUEUE_NAME, json.dumps(task))
                    time.sleep(5)  # Karbonun düşmesi için kısa bir mola
                    continue
                
                # Karbon uygunsa, log için güncel veriyi hazırla
                display_carbon = curr_intensity
            else:
                # Redis'te state yoksa orijinal veriyi kullan (fallback)
                logger.warning("[Worker] ⚠️ Güncel karbon verisi Redis'te bulunamadı, bekletiliyor.")
                r.rpush(QUEUE_NAME, json.dumps(task))
                time.sleep(5)
                continue

            # 4. Çalıştırma (Hem zaman hem karbon uygun)
            logger.info(
                "[Worker] 🟢 Koşullar uygun, çalıştırılıyor: action=%s (Karbon: %.1f)",
                action_name, display_carbon
            )
            
            result = ow_invoker.invoke(action_name, params)

            # Sonuç Loglama
            logger.info(
                "[Worker] ✅ Tamamlandı: status=%s  duration=%s ms",
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