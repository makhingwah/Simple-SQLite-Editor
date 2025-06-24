# MS Access to Python Migration Utilities

This project provides two lightweight utility applications designed to assist in migrating Microsoft Access databases to Python-based applications using SQLite. These tools offer core functionality similar to **DB Browser for SQLite**, but are simplified for ease of use in minimal environments.

## Overview

The goal is to provide a migration platform that allows users to transfer their MS Access programs into Python with SQLite as the database backend.

Both tools support:
- Creating and modifying SQLite databases
- Managing multiple tables
- Editing table records
- Importing and exporting CSV data

---

## Requirements

- **Python**: Version 3.11
- **SQLite3**
- **PyQt6**: Version 6.9.0

Install PyQt6 using pip:

```bash
pip install PyQt6
```

> **Note**: Always create a backup of your SQLite database file before opening it with these tools.

---

## Utility Applications

### 1. Table Creator  
**File**: `TableCreatorApp_V5_3.py`  
**Purpose**:  
- Create new SQLite database files  
- Define or modify table structures in existing databases  

### 2. SQLite Editor  
**File**: `SQLite_Editor_V1_51.py`  
**Purpose**:  
- Edit records in existing SQLite database tables  
- Import/export table data as CSV files  

---

## Usage Tips

- These tools are intended for basic database file manipulation and are not full-featured database management systems.
- Ideal for developers transitioning MS Access projects to Python applications using SQLite.
