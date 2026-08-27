# 🔧 Desktop Production Scheduling App (Sharpening Line)

Enterprise production application built using PySide6 and SQLite designed to synchronize ERP orders from SQL Server database lines, allowing interactive management and queue optimizations.

---

## 🚀 Execution & Setup Guide

### 1. Configure the SQL Server Connection
- Copy the `config.ini` file template to the root directory of the application.
- Fill in the production database credentials:
  - `Server`: Production database server IP or hostname.
  - `UID` / `PWD`: Read-only credentials assigned for system authentication.

### 2. Local Environment Execution
- Set up a virtual environment:
  ```bash
  python -m venv venv
  source venv/Scripts/activate
