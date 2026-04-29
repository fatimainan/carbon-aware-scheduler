"""
worker.py
─────────────────────────────────────────────────────────────────────────────
Redis Queue Worker — carbon-aware task re-executor.

Çalışma mantığı:
  1. carbon_task_queue kuyruğunu dinler (BLPOP — blocking, CPU yakmaz)
  2. Her task için retry_after zamanını kontrol eder
  3. Henüz zamanı gelmediyse kuyruğun sonuna geri koyar, kısa bekler
  4. Zamanı geldiyse OpenWhisk action'ı invoke eder
  5. Hata durumunda 5 saniye bekleyip devam eder

Çalıştırmak için:
  python worker.py
  veya docker-compose'da "command: python worker.py"
"""

import json
import logging
import os
import sys
import time
import traceback

import redis

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append("/app")

from executor.executor import OpenWhiskInvoker

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Redis bağlantısı ──────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
QUEUE_NAME = "carbon_task_queue"

def get_redis_connection() -> redis.Redis:
    """Redis'e bağlan, başarısız olursa yeniden dene."""
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
            # BLPOP — kuyruk boşsa block eder, CPU yakmaz
            raw = r.blpop(QUEUE_NAME, timeout=10)

            if raw is None:
                # timeout doldu, kuyruk boş — döngüye devam
                continue

            _, data = raw
            task = json.loads(data)

            action_name   = task.get("action_name", "data_processor")
            params        = task.get("params", {})
            retry_after   = task.get("retry_after", 0)
            carbon        = task.get("carbon_at_delay", "?")
            threshold     = task.get("threshold", "?")

            now = time.time()

            if now < retry_after:
                # Henüz zamanı gelmedi — kuyruğun sonuna geri koy
                wait_secs = retry_after - now
                logger.info(
                    "[Worker] ⏳ Görev henüz hazır değil (%.0fsn kaldı). "
                    "Kuyruğa geri eklendi.", wait_secs
                )
                r.rpush(QUEUE_NAME, json.dumps(task))
                time.sleep(min(wait_secs, 10))  # max 10sn bekle
                continue

            # ── Zaman geldi, execute et ───────────────────────────────────────
            logger.info(
                "[Worker] 🟢 Görev çalıştırılıyor: action=%s  "
                "carbon_at_delay=%.1f  threshold=%.1f",
                action_name, float(carbon), float(threshold),
            )

            result = ow_invoker.invoke(action_name, params)
            logger.info(
                "[Worker] ✅ Tamamlandı: status=%s  duration=%s ms",
                result.get("status"),
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