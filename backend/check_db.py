"""
Database connection check script for run.bat startup verification.
"""

import sys
from backend.database import check_database_connection, DB_HOST, DB_PORT, DB_NAME, DB_USER

if __name__ == "__main__":
    ok = check_database_connection()
    if ok:
        print(f"[OK] Successfully connected to MySQL at {DB_HOST}:{DB_PORT} (User: {DB_USER}, DB: {DB_NAME}).")
        sys.exit(0)
    else:
        print(f"[ERROR] Could not connect to MySQL at {DB_HOST}:{DB_PORT}.")
        print(f"        Please verify that MySQL Server is running and credentials in .env are correct.")
        print(f"        Target Host: {DB_HOST}:{DB_PORT} | Database: {DB_NAME} | User: {DB_USER}")
        sys.exit(1)

