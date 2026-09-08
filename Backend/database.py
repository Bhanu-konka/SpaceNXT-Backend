import os
import mysql.connector
from mysql.connector import Error

# ==========================================
# TiDB / MySQL Configuration
# ==========================================
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 4000))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "elderly_care_db")


# ==========================================
# Database Connection
# ==========================================
def get_db_connection():
    """Returns a TiDB/MySQL database connection."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )


# ==========================================
# Initialize Tables
# ==========================================
def init_db():
    """Create required tables only if they don't already exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # =====================================================
        # USERS TABLE (Matches TiDB schema)
        # =====================================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
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

        # =====================================================
        # REGISTERED USERS
        # =====================================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS registered_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            firebase_uid VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_registered_uid (firebase_uid)
        )
        """)

        # =====================================================
        # USER CONNECTIONS
        # =====================================================
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

        # =====================================================
        # CHAT MESSAGES
        # =====================================================
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
            INDEX idx_status (status),
            INDEX idx_conversation (sender_uid, receiver_uid)
        )
        """)

        # =====================================================
        # SOS EVENTS
        # =====================================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sos_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_id VARCHAR(255) UNIQUE NOT NULL,
            sender_uid VARCHAR(255) NOT NULL,
            latitude DOUBLE,
            longitude DOUBLE,
            message TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'TRIGGERED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_sender (sender_uid),
            INDEX idx_status (status)
        )
        """)

        # =====================================================
        # MEDICINES
        # =====================================================
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
            INDEX idx_user_uid (user_uid)
        )
        """)

        # =====================================================
        # MEDICINE LOGS
        # =====================================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicine_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            medicine_id INT NOT NULL,
            log_date DATE NOT NULL,
            taken TINYINT(1) DEFAULT 1,
            taken_at VARCHAR(50),
            marked_by VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_medicine_day (medicine_id, log_date),
            INDEX idx_medicine (medicine_id),
            INDEX idx_log_date (log_date)
        )
        """)

        conn.commit()
        cursor.close()
        conn.close()

        print("Database schema initialized successfully!")

    except Error as e:
        print(f"Error initializing database: {e}")