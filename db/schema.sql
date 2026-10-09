-- Схема БД магазина настольных игр.
-- Повторный запуск безопасен: CREATE TABLE IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    avatar_path TEXT,  -- NULL, если аватар не задан
    role TEXT NOT NULL CHECK (role IN ('client', 'employee', 'admin')),
    status TEXT NOT NULL CHECK (status IN ('active', 'blocked')),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_idx
    ON users (LOWER(email));

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);
