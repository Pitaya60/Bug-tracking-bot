import os
import re
import time
import yaml
import requests
from datetime import datetime

class LogMonitorBot:
    def __init__(self, config_file='config.yaml'):
        print("🚀 Инициализация бота...")
        
        self.config = self.load_config(config_file)
        self.bot_token = self.config['telegram']['bot_token']
        self.chat_id = str(self.config['telegram']['chat_id'])
        self.log_file = self.config['log_file']
        self.filters = self.compile_filters()
        
        self.check_interval = self.config.get('monitoring', {}).get('check_interval', 1)
        self.batch_size = self.config.get('monitoring', {}).get('batch_size', 10)
        self.batch_timeout = self.config.get('monitoring', {}).get('batch_timeout', 5)
        
        self.last_position = 0
        self.pending_logs = []
        self.last_send_time = time.time()
        self.total_logs_sent = 0
        
        print("✅ Бот инициализирован")
    
    def load_config(self, config_file):
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Файл {config_file} не найден")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def compile_filters(self):
        filters = []
        for f_config in self.config.get('filters', []):
            if f_config.get('enabled', True):
                try:
                    filters.append({
                        'name': f_config['name'],
                        'pattern': re.compile(f_config['pattern'])
                    })
                    print(f"✅ Фильтр активирован: {f_config['name']}")
                except re.error as e:
                    print(f"❌ Ошибка в фильтре '{f_config['name']}': {e}")
        return filters
    
    def send_telegram_message(self, text):
        """Отправка сообщения БЕЗ Markdown"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                print(f"❌ Ошибка Telegram API: {response.status_code}")
                print(f"Ответ: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            return False
    
    def test_connection(self):
        """Проверка подключения к боту"""
        url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_username = data['result'].get('username', 'unknown')
                    print(f"✅ Подключение к боту @{bot_username} успешно")
                    return True
            print(f"❌ Ошибка подключения: {response.text}")
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def check_log_match(self, log_line):
        for f in self.filters:
            if f['pattern'].search(log_line):
                return True, f['name']
        return False, None
    
    def format_log_batch(self, logs):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        header = f"🔔 Уведомление о логах\n"
        header += f"Время: {timestamp}\n"
        header += f"Записей: {len(logs)}\n"
        header += "=" * 40 + "\n\n"
        
        body = "\n\n".join(logs)
        message = header + body
        
        if len(message) > 4000:
            message = message[:4000] + "\n\n... (обрезано)"
        
        return message
    
    def send_pending_logs(self):
        if not self.pending_logs:
            return True
        
        message = self.format_log_batch(self.pending_logs)
        
        if self.send_telegram_message(message):
            count = len(self.pending_logs)
            self.total_logs_sent += count
            print(f"📤 Отправлено {count} логов (всего: {self.total_logs_sent})")
            self.pending_logs = []
            self.last_send_time = time.time()
            return True
        return False
    
    def process_new_lines(self):
        if not os.path.exists(self.log_file):
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                current_position = f.tell()
                
                for line in new_lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    matched, filter_name = self.check_log_match(line)
                    
                    if matched:
                        formatted = f"[{filter_name}]\n{line}"
                        self.pending_logs.append(formatted)
                        print(f"🔍 Найден: {line[:60]}...")
                
                self.last_position = current_position
                
                if len(self.pending_logs) >= self.batch_size:
                    self.send_pending_logs()
        
        except Exception as e:
            print(f"❌ Ошибка чтения файла: {e}")
    
    def run(self):
        print("=" * 60)
        print("🤖 Бот мониторинга логов запущен")
        print(f"📁 Отслеживаемый файл: {self.log_file}")
        print(f"🔍 Активных фильтров: {len(self.filters)}")
        print(f"⏱️ Интервал проверки: {self.check_interval} сек")
        print("-" * 60)
        
        if not self.test_connection():
            print("❌ Не удалось подключиться к Telegram")
            print("Проверьте:")
            print("1. Правильность токена бота")
            print("2. Интернет-соединение")
            return
        
        test_msg = f"🤖 Бот запущен\n\nФайл: {self.log_file}\nФильтров: {len(self.filters)}\nСтатус: Мониторинг активен"
        if not self.send_telegram_message(test_msg):
            print("❌ Не удалось отправить стартовое сообщение")
            print("Проверьте:")
            print("1. Chat ID правильный")
            print("2. Вы отправили /start боту в Telegram")
            return
        
        print("✅ Стартовое сообщение отправлено")
        print("🟢 Мониторинг запущен. Нажмите Ctrl+C для остановки")
        print("-" * 60)
        
        try:
            while True:
                self.process_new_lines()
                
                time_since_last_send = time.time() - self.last_send_time
                if self.pending_logs and time_since_last_send >= self.batch_timeout:
                    self.send_pending_logs()
                
                time.sleep(self.check_interval)
        
        except KeyboardInterrupt:
            print("\n" + "=" * 60)
            print("⏹️ Остановка бота...")
            print("=" * 60)
            
            if self.pending_logs:
                print("📤 Отправка накопленных логов...")
                self.send_pending_logs()
            
            stop_msg = f"🛑 Бот остановлен\n\nОбнаружено логов: {self.total_logs_sent}\nДо встречи!"
            self.send_telegram_message(stop_msg)
            
            print("✅ Бот остановлен")


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║          TELEGRAM LOG MONITOR BOT                         ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    try:
        bot = LogMonitorBot('config.yaml')
        bot.run()
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        print("💡 Создайте файл config.yaml")
    except KeyError as e:
        print(f"\n❌ Ошибка конфигурации: {e}")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


if __name__ == '__main__':
    main()