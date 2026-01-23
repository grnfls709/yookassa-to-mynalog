import asyncio
import json
import os
import logging
import httpx
from datetime import datetime, timedelta, timezone
from yookassa import Configuration, Payment
from tenacity import retry, stop_after_attempt, wait_exponential
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sync.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class MoyNalogAPI:
    def __init__(self, login, password):
        self.login = login
        self.password = password
        self.token = None
        self.device_id = "EKlXkCYMIh28msCCrEHVb"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru,en-US;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Origin': 'https://lknpd.nalog.ru',
            'Referer': 'https://lknpd.nalog.ru/',
            'User-Agent': self.user_agent,
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def authenticate(self):
        url = "https://lknpd.nalog.ru/api/v1/auth/lkfl"
        payload = {
            "username": self.login,
            "password": self.password,
            "deviceInfo": {
                "sourceDeviceId": self.device_id,
                "sourceType": "WEB",
                "appVersion": "1.0.0",
                "metaDetails": {
                    "userAgent": self.user_agent
                }
            }
        }
        try:
            response = await self.client.post(url, json=payload)
            if response.status_code != 200:
                logging.error(f"Ошибка авторизации (Код {response.status_code}): {response.text}")
                raise Exception(f"HTTP {response.status_code}")
            
            data = response.json()
            self.token = data.get("token")
            if not self.token:
                raise Exception("Токен не получен в ответе")
            logging.info("✓ Успешная авторизация в Мой Налог.")
            return True
        except Exception as e:
            logging.error(f"Ошибка при авторизации: {e}")
            raise

    async def add_income(self, name, amount, date):
        if not self.token:
            try:
                await self.authenticate()
            except Exception as e:
                logging.error(f"Не удалось авторизоваться: {e}")
                return False

        url = "https://lknpd.nalog.ru/api/v1/income"
        
        if date.tzinfo is None:
            tz = timezone(timedelta(hours=11))
            date = date.replace(tzinfo=tz)
        
        iso_date = date.isoformat(timespec='seconds')
        request_time = datetime.now(date.tzinfo).isoformat(timespec='seconds')
        
        payload = {
            "operationTime": iso_date,
            "requestTime": request_time,
            "services": [
                {
                    "name": name,
                    "amount": amount,
                    "quantity": 1
                }
            ],
            "totalAmount": str(amount),
            "client": {
                "contactPhone": None,
                "displayName": None,
                "inn": None,
                "incomeType": "FROM_INDIVIDUAL"
            },
            "paymentType": "CASH",
            "ignoreMaxTotalIncomeRestriction": False
        }
        
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {self.token}"
        
        try:
            response = await self.client.post(url, json=payload, headers=headers)
            
            if response.status_code == 401: # Токен истек
                logging.warning("Токен истек, обновляем...")
                try:
                    await self.authenticate()
                    headers["Authorization"] = f"Bearer {self.token}"
                    response = await self.client.post(url, json=payload, headers=headers)
                except Exception as e:
                    logging.error(f"Ошибка при переавторизации: {e}")
                    return False
            
            if response.status_code == 200:
                logging.info(f"✓ Доход успешно зарегистрирован: {amount} руб. за '{name}'")
                return True
            else:
                logging.error(f"✗ Ошибка регистрации дохода (Код {response.status_code}): {response.text}")
                return False
        except Exception as e:
            logging.error(f"Исключение при регистрации дохода: {e}")
            return False

    async def close(self):
        await self.client.aclose()

class SyncManager:
    def __init__(self):
        try:
            config.validate_config()
        except ValueError as e:
            logging.error(f"Ошибка конфигурации: {e}")
            raise
        
        Configuration.configure(config.YOOKASSA_SHOP_ID, config.YOOKASSA_API_KEY)
        self.nalog = MoyNalogAPI(config.MOY_NALOG_LOGIN, config.MOY_NALOG_PASSWORD)
        self.state_file = config.STATE_FILE
        self.state = self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        if config.SYNC_START_DATE:
            return {"last_sync_time": f"{config.SYNC_START_DATE}T00:00:00Z", "processed_payments": []}
        
        return {"last_sync_time": (datetime.now() - timedelta(days=1)).isoformat(), "processed_payments": []}

    def save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f)

    async def get_new_yookassa_payments(self):
        new_payments = []
        last_sync = self.state.get("last_sync_time")
        
        params = {
            "status": "succeeded",
            "created_at.gte": last_sync
        }
        
        try:
            res = Payment.list(params)
            for payment in res.items:
                if payment.id not in self.state["processed_payments"]:
                    new_payments.append(payment)
            
            while res.next_cursor:
                params["cursor"] = res.next_cursor
                res = Payment.list(params)
                for payment in res.items:
                    if payment.id not in self.state["processed_payments"]:
                        new_payments.append(payment)
        except Exception as e:
            logging.error(f"Ошибка ЮKassa: {e}")
            
        return new_payments

    async def sync(self):
        logging.info("="*60)
        logging.info("Начало синхронизации...")
        logging.info(f"Последняя синхронизация: {self.state.get('last_sync_time')}")
        
        try:
            new_payments = await self.get_new_yookassa_payments()
            
            if not new_payments:
                logging.info("✓ Новых платежей не найдено.")
                return

            logging.info(f"✓ Найдено новых платежей: {len(new_payments)}")
            
            successful = 0
            failed = 0
            
            for payment in new_payments:
                try:
                    amount = float(payment.amount.value)
                    payment_date = datetime.fromisoformat(payment.created_at.replace('Z', '+00:00'))
                    
                    description = config.INCOME_DESCRIPTION_TEMPLATE.format(
                        description=payment.description or payment.id
                    )
                    
                    success = await self.nalog.add_income(description, amount, payment_date)
                    
                    if success:
                        self.state["processed_payments"].append(payment.id)
                        self.state["last_sync_time"] = payment.created_at
                        self.save_state()
                        successful += 1
                    else:
                        failed += 1
                        logging.warning(f"Пропуск платежа {payment.id} из-за ошибки.")
                except Exception as e:
                    failed += 1
                    logging.error(f"Ошибка при обработке платежа {payment.id}: {e}")

            logging.info(f"Результат: успешно={successful}, ошибок={failed}")
        except Exception as e:
            logging.error(f"Критическая ошибка при синхронизации: {e}", exc_info=True)
        finally:
            await self.nalog.close()
            logging.info("Синхронизация завершена.")
            logging.info("="*60)

async def main():
    try:
        manager = SyncManager()
        await manager.sync()
    except Exception as e:
        logging.critical(f"Критическая ошибка: {e}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
