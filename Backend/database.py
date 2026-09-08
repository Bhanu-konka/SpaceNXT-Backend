import os
import mysql.connector
from mysql.connector import Error

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "1781")
DB_NAME = os.environ.get("DB_NAME", "elderly_care_db")

def get_db_connection():
    """Returns a new MySQL database connection."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def init_db():
    """Ensures database and required tables (with proper indexes) exist."""
    try:
        # Initial connection without database selection to ensure DB exists
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        cursor.close()
        conn.close()

        # Connect to target DB to create tables
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            firebase_uid VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            role VARCHAR(50),
            profile_image VARCHAR(500),
            date_of_birth DATE,
            gender VARCHAR(20),
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_users_firebase_uid (firebase_uid)
        )
        """)

        # 2. registered_users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS registered_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            firebase_uid VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_reg_firebase_uid (firebase_uid)
        )
        """)

        # 3. user_connections
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_connections (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_uid VARCHAR(255) NOT NULL,
            target_uid VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_connection (user_uid, target_uid),
            INDEX idx_user_uid (user_uid),
            INDEX idx_target_uid (target_uid)
        )
        """)

        # 4. messages
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            message_id VARCHAR(255) UNIQUE NOT NULL,
            sender_uid VARCHAR(255) NOT NULL,
            receiver_uid VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'queued',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_sender (sender_uid),
            INDEX idx_receiver (receiver_uid),
            INDEX idx_msg_status (status),
            INDEX idx_conv (sender_uid, receiver_uid)
        )
        """)

        # 5. sos_events
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sos_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_id VARCHAR(255) UNIQUE NOT NULL,
            sender_uid VARCHAR(255) NOT NULL,
            latitude DOUBLE NULL,
            longitude DOUBLE NULL,
            message TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'TRIGGERED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_sos_sender (sender_uid),
            INDEX idx_sos_status (status)
        )
        """)

        # 6. medicines
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_uid VARCHAR(255) NOT NULL,
            medicine_name VARCHAR(255) NOT NULL,
            dosage VARCHAR(100),
            reminder_time VARCHAR(50) NOT NULL,
            repeat_type VARCHAR(50) DEFAULT 'Daily',
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_med_user (user_uid)
        )
        """)

        # 7. medicine_logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicine_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            medicine_id INT NOT NULL,
            log_date DATE NOT NULL,
            taken TINYINT(1) DEFAULT 1,
            taken_at VARCHAR(50),
            marked_by VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_med_log_date (medicine_id, log_date),
            INDEX idx_med_id (medicine_id),
            INDEX idx_log_date (log_date)
        )
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("Database schema initialized successfully!")
    except Error as e:
        print(f"Error initializing database: {e}")
