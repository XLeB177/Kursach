"""Подготовка и запуск отдельного PostgreSQL для проекта на Windows."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
from tempfile import NamedTemporaryFile

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".postgres"
ENV_FILE = ROOT / ".env"
HOST = "127.0.0.1"
PORT = "55473"
DB_NAME = "board_games"
DB_USER = "board_shop"


def run(bin_dir, tool, *args, check=True, extra_env=None):
    env = {**os.environ, **(extra_env or {})}
    return subprocess.run(
        [str(bin_dir / f"{tool}.exe"), *map(str, args)],
        cwd=ROOT, env=env, check=check, creationflags=subprocess.CREATE_NO_WINDOW,
    )


def discover_bin(path=None):
    if path:
        candidates = [Path(path)]
    else:
        base = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "PostgreSQL"
        candidates = [entry / "bin" for entry in base.iterdir() if all(part.isdigit() for part in entry.name.split("."))] if base.is_dir() else []
        candidates.sort(key=lambda p: tuple(map(int, p.parent.name.split("."))), reverse=True)
    for candidate in candidates:
        if (candidate / "pg_ctl.exe").is_file() and (candidate / "initdb.exe").is_file():
            return candidate
    raise ValueError("PostgreSQL не найден. Укажите папку bin через --bin.")


def start(bin_dir, port):
    active = run(bin_dir, "pg_ctl", "-D", DATA, "status", check=False)
    if active.returncode != 0:
        run(bin_dir, "pg_ctl", "-D", DATA, "-l", DATA / "server.log",
            "-o", f"-h {HOST} -p {port}", "-w", "start")


def prepare(bin_dir):
    if ENV_FILE.exists() or (DATA / "PG_VERSION").exists():
        raise ValueError("Локальная база или конфигурация уже существуют.")
    password = secrets.token_urlsafe(32)
    password_path = None
    try:
        with NamedTemporaryFile(mode="w", encoding="ascii", delete=False) as file:
            password_path = Path(file.name)
            file.write(password + "\n")
        run(bin_dir, "initdb", "-D", DATA, "-U", DB_USER, "-A", "scram-sha-256",
            "--encoding=UTF8", "--locale=C", "--locale-provider=icu", "--icu-locale=ru-RU",
            f"--pwfile={password_path}")
    finally:
        if password_path:
            password_path.unlink(missing_ok=True)
    start(bin_dir, PORT)
    run(bin_dir, "createdb", "-h", HOST, "-p", PORT, "-U", DB_USER, DB_NAME,
        extra_env={"PGPASSWORD": password})
    with ENV_FILE.open("x", encoding="utf-8") as file:
        file.write(f'DB_HOST={HOST}\nDB_PORT={PORT}\nDB_NAME={DB_NAME}\nDB_USER={DB_USER}\n'
                   f'DB_PASSWORD={password}\nTEST_DB_NAME=board_games_test\nPOSTGRES_BIN="{bin_dir.as_posix()}"\n')

    from db.connection import execute_sql_file
    execute_sql_file(ROOT / "db" / "schema.sql")
    execute_sql_file(ROOT / "db" / "seed.sql")
    print("Локальная база и демонстрационный каталог готовы.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "start", "stop"))
    parser.add_argument("--bin", help="Папка bin установленного PostgreSQL")
    args = parser.parse_args()
    if os.name != "nt":
        parser.exit(1, "Этот скрипт предназначен для Windows. См. инструкции для внешней базы.\n")
    config = dotenv_values(ENV_FILE)
    try:
        bin_dir = discover_bin(args.bin or config.get("POSTGRES_BIN"))
        if args.action == "prepare":
            prepare(bin_dir)
        elif not (DATA / "PG_VERSION").is_file():
            raise ValueError("Локальная база ещё не подготовлена.")
        elif args.action == "start":
            port = int(config.get("DB_PORT") or PORT)
            if not 1 <= port <= 65535:
                raise ValueError("Некорректный порт PostgreSQL.")
            start(bin_dir, port)
        else:
            run(bin_dir, "pg_ctl", "-D", DATA, "-m", "fast", "-w", "stop")
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        detail = str(exc) if isinstance(exc, ValueError) else "См. вывод PostgreSQL или .postgres/server.log."
        parser.exit(1, f"Не удалось выполнить операцию. {detail}\n")


if __name__ == "__main__":
    main()
