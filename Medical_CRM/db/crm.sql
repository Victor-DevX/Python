-- Очистка таблиц
DROP TABLE IF EXISTS appointment_files CASCADE;
DROP TABLE IF EXISTS medical_records CASCADE;
DROP TABLE IF EXISTS appointments CASCADE;
DROP TABLE IF EXISTS specialties CASCADE;
DROP TABLE IF EXISTS patients CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS roles CASCADE;

-- 1. Роли
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20) UNIQUE NOT NULL
);

INSERT INTO roles (name)
SELECT LOWER(v.name)
FROM (VALUES ('admin'), ('doctor'), ('patient')) AS v(name)
ON CONFLICT (name) DO NOTHING;

-- 2. Пользователи
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL CHECK (email LIKE '%@%'),
    password_hash TEXT NOT NULL,
    role_id INT REFERENCES roles(id) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE users
    ADD CONSTRAINT users_username_unique UNIQUE (username),
    ADD CONSTRAINT users_email_unique UNIQUE (email),
    ADD CONSTRAINT users_role_fk
        FOREIGN KEY (role_id) REFERENCES roles(id)
        ON DELETE RESTRICT;

ALTER TABLE users
ALTER COLUMN role_id SET NOT NULL,
ALTER COLUMN password_hash DROP NOT NULL;


-- 3. Специальности
CREATE TABLE specialties (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

INSERT INTO specialties (name) VALUES
('Терапевт'), ('Хирург'), ('Кардиолог'), ('Невролог'),
('Офтальмолог'), ('ЛОР'), ('Травматолог'),
('Эндокринолог'), ('Педиатр'), ('Психиатр');

-- 4. Врачи
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    middle_name TEXT,
    specialty_id INT REFERENCES specialties(id),
    phone VARCHAR(20)
);

-- 5. Пациенты
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    middle_name TEXT,
    phone VARCHAR(20),
    birth_date DATE,
    city TEXT
);

-- 6. Прием пациентов
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    doctor_id INT REFERENCES employees(id) ON DELETE CASCADE,
    patient_id INT REFERENCES patients(id) ON DELETE CASCADE,
    appointment_datetime TIMESTAMPTZ NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_doctor_time UNIQUE(doctor_id, appointment_datetime)
);

CREATE INDEX idx_appointments_doctor_time 
ON appointments(doctor_id, appointment_datetime);

-- 7. Медкарта (FIX #6: timezone)
CREATE TABLE medical_records (
    id SERIAL PRIMARY KEY,
    appointment_id INT UNIQUE REFERENCES appointments(id) ON DELETE CASCADE,
    doctor_id INT REFERENCES employees(id),
    patient_id INT REFERENCES patients(id),

    visit_datetime TIMESTAMPTZ NOT NULL,
    next_visit_datetime TIMESTAMPTZ,

    diagnosis TEXT,
    medication TEXT,
    recommendations TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_appointments_date ON appointments(appointment_datetime);

-- 8. Файлы
CREATE TABLE appointment_files (
    id SERIAL PRIMARY KEY,
    appointment_id INT REFERENCES appointments(id) ON DELETE CASCADE,

    file_id VARCHAR(24) NOT NULL UNIQUE,
    filename TEXT,

    uploaded_by VARCHAR(20),
    uploader_id INT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);



-- индекс для скорости
CREATE INDEX idx_appointment_files_app_id 
ON appointment_files(appointment_id);
