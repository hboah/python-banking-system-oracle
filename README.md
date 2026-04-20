# Python Banking System with Oracle Database

A robust **Banking System** built in Python that connects to **Oracle Database** for all core business logic, data storage, and transaction processing.

This project demonstrates clean architecture: Python for the application layer and **Oracle Database** handling accounts, transactions, validation rules, and persistence.

![System Architecture](screenshots/architecture.png)  
*(Add a simple diagram later showing Python ↔ Oracle)*

## ✨ Features

- Create and manage customer accounts
- Deposit, withdraw, and transfer funds
- View real-time balance and transaction history
- Secure PIN/authentication
- Full data persistence and business rules enforced in Oracle
- Input validation and error handling
- (Future) Kivy-based mobile/desktop GUI

## 🛠️ Technologies & Architecture

- **Python 3.10+**
- **Oracle Database** (12c or later) — Handles **all business logic** via tables, PL/SQL procedures, functions, and triggers
- **python-oracledb** (official Oracle driver – successor to cx_Oracle)
- Object-Oriented Design (separation of concerns)
- Environment-based configuration for security

## 📁 Project Structure
