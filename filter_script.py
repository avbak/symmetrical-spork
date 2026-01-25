#!/usr/bin/env python3
import hashlib
import os
import sys
import subprocess
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime

# Конфигурация
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
HASH_DIR = os.path.join(REPO_PATH, ".last_check")

SOURCES = [
    {
        "url": "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-checked.txt",
        "output": "filtered_configs.txt",
        "header": "# Filtered VLESS list based on igareck/vpn-configs-for-russia"
    }
]

EXCLUDE_PATTERNS = [
    "sni=github.com",
    "ads.x5.ru",
    "chat.speedload.ru",
    "sso.passport.yandex.ru",
    "sberbank.ru",
    "serverstats.ru",
    "nodesecure.ru"
]

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def download_file(url):
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8')
    except (URLError, HTTPError) as e:
        log(f"❌ Ошибка загрузки {url}: {e}")
        raise

def filter_lines(content):
    filtered = []
    for line in content.split('\n'):
        line_lower = line.lower()
        if 'vless' in line_lower and 'russia' in line_lower:
            if not any(pattern.lower() in line_lower for pattern in EXCLUDE_PATTERNS):
                filtered.append(line)
    return filtered

def git_command(command, cwd=REPO_PATH):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        log(f"❌ Git ошибка: {e.stderr}")
        raise

def main():
    log("🚀 Начало работы")

    # СНАЧАЛА делаем pull
    try:
        log("🔄 Обновление репозитория...")
        git_command(['git', 'pull', '--rebase', 'origin', 'main'])
    except Exception as e:
        log(f"⚠️ Pull не удался (возможно первый запуск): {e}")

    os.makedirs(HASH_DIR, exist_ok=True)

    any_changes = False

    for source in SOURCES:
        url = source['url']
        output_file = os.path.join(REPO_PATH, source['output'])
        header = source['header']
        hash_file = os.path.join(HASH_DIR, f"{source['output']}.hash")

        log(f"📥 Обработка: {url}")

        try:
            content = download_file(url)
            current_hash = get_sha256(content)

            if os.path.exists(hash_file):
                with open(hash_file, 'r') as f:
                    last_hash = f.read().strip()

                if current_hash == last_hash:
                    log(f"✅ Хеш совпал, изменений нет")
                    continue
                else:
                    log(f"🔄 Хеш изменился")
            else:
                log(f"🆕 Первая проверка")

            filtered_lines = filter_lines(content)
            log(f"📊 Отфильтровано: {len(filtered_lines)} строк")

            result = header + "\n" + "\n".join(filtered_lines)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)

            with open(hash_file, 'w') as f:
                f.write(current_hash)

            log(f"💾 Сохранено: {source['output']}")
            any_changes = True

        except Exception as e:
            log(f"❌ Ошибка обработки {url}: {e}")
            continue

    if any_changes:
        log("📤 Отправка в GitHub...")
        try:
            git_command(['git', 'add', '.'])
            git_command(['git', 'config', 'user.email', 'vps-bot@localhost'])
            git_command(['git', 'config', 'user.name', 'VPS Filter Bot'])
            git_command(['git', 'commit', '-m', 'chore: update filtered configs [automated]'])
            git_command(['git', 'push', 'origin', 'main'])

            log("✅ Изменения отправлены в GitHub")
        except Exception as e:
            log(f"❌ Ошибка Git: {e}")
            sys.exit(1)
    else:
        log("✅ Изменений нет, коммит не требуется")

    log("🎉 Работа завершена")

if __name__ == "__main__":
    main()
