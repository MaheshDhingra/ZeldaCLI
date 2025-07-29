import os
import psycopg2
from dotenv import load_dotenv
import bcrypt
import random
import datetime
import re
load_dotenv()

class BankAccount:
    def __init__(self, account_id, user_id, account_number, balance=0.0):
        self.account_id = account_id
        self.user_id = user_id
        self.account_number = account_number
        self.balance = balance

    def save_balance(self):
        conn = get_db_connection()
        if conn is None:
            return False
        cur = conn.cursor()
        try:
            cur.execute("UPDATE accounts SET balance = %s WHERE id = %s;", (self.balance, self.account_id))
            conn.commit()
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print_message(f"Database error saving balance: {e}", "error")
            return False
        except Exception as e:
            conn.rollback()
            print_message(f"An unexpected error occurred saving balance: {e}", "error")
            return False
        finally:
            cur.close()
            conn.close()

    def deposit(self, amount):
        if amount > 0:
            self.balance += amount
            self.save_balance()
            return True
        else:
            return False

    def withdraw(self, amount):
        if 0 < amount <= self.balance:
            self.balance -= amount
            self.save_balance()
            return True
        else:
            return False

    def get_balance(self):
        return self.balance

class User:
    def __init__(self, user_id, username, password_hash):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash

def get_db_connection():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except psycopg2.Error as e:
        print_message(f"Database connection error: {e}", "error")
        return None

def create_tables():
    conn = get_db_connection()
    if conn is None:
        return False
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                phone_number VARCHAR(20),
                address TEXT,
                date_of_birth DATE
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                account_number VARCHAR(20) UNIQUE NOT NULL,
                balance DECIMAL(10, 2) NOT NULL,
                loan_balance DECIMAL(10, 2) DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                account_id INTEGER REFERENCES accounts(id),
                type VARCHAR(20) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_public BOOLEAN DEFAULT FALSE,
                category VARCHAR(50)
            );
            CREATE TABLE IF NOT EXISTS recurring_transfers (
                id SERIAL PRIMARY KEY,
                from_account_id INTEGER REFERENCES accounts(id),
                to_account_number VARCHAR(20) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                frequency VARCHAR(20) NOT NULL,
                next_transfer_date DATE NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS bills (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                bill_name VARCHAR(100) NOT NULL,
                due_date DATE NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS cards (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                card_number VARCHAR(16) UNIQUE NOT NULL,
                expiry_date VARCHAR(5) NOT NULL,
                cvv VARCHAR(3) NOT NULL,
                card_type VARCHAR(10) NOT NULL,
                issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS loans (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                amount DECIMAL(10, 2) NOT NULL,
                interest_rate DECIMAL(5, 4) NOT NULL,
                term_months INTEGER NOT NULL,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                remaining_balance DECIMAL(10, 2) NOT NULL,
                status VARCHAR(20) DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS loan_payments (
                id SERIAL PRIMARY KEY,
                loan_id INTEGER REFERENCES loans(id),
                amount DECIMAL(10, 2) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_public BOOLEAN DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS money_requests (
                id SERIAL PRIMARY KEY,
                from_user_id INTEGER REFERENCES users(id),
                to_user_id INTEGER REFERENCES users(id),
                amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chats (
                id SERIAL PRIMARY KEY,
                from_user_id INTEGER REFERENCES users(id),
                to_user_id INTEGER REFERENCES users(id),
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return True
    except psycopg2.Error as e:
        conn.rollback()
        print_message(f"Database error during table creation: {e}", "error")
        return False
    finally:
        cur.close()
        conn.close()

def transfer_funds(from_user_id, to_account_number, amount):
    if amount <= 0:
        return False, "Transfer amount must be positive."

    from_account = get_user_account(from_user_id)
    if not from_account:
        return False, "Your account not found."

    if from_account.balance < amount:
        return False, "Insufficient balance."

    to_account_id = get_account_id_by_account_number(to_account_number)
    if not to_account_id:
        return False, "Recipient account not found."

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE accounts SET balance = balance - %s WHERE user_id = %s;", (amount, from_user_id))
        record_transaction(get_account_id_by_user_id(from_user_id), 'transfer_out', amount)

        cur.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s;", (amount, to_account_id))
        record_transaction(to_account_id, 'transfer_in', amount)

        conn.commit()
        return True, f"Successfully transferred ${amount:.2f} to account {to_account_number}."
    except Exception as e:
        conn.rollback()
        return False, f"Transfer failed: {e}"
    finally:
        cur.close()
        conn.close()

def view_transaction_history(user_id):
    account_id = get_account_id_by_user_id(user_id)
    if not account_id:
        return "No account found for this user."

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT type, amount, timestamp FROM transactions WHERE account_id = %s ORDER BY timestamp DESC;", (account_id,))
    transactions = cur.fetchall()
    cur.close()
    conn.close()

    if transactions:
        history = "\n--- Transaction History ---\n"
        for t in transactions:
            history += f"Type: {t[0].capitalize()}, Amount: ${t[1]:.2f}, Date: {t[2].strftime('%Y-%m-%d %H:%M:%S')}\n"
        history += "--------------------------"
        return history
    else:
        return "No transactions found for your account."

def get_account_id_by_user_id(user_id):
    conn = get_db_connection()
    if conn is None:
        return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM accounts WHERE user_id = %s;", (user_id,))
        account_id = cur.fetchone()
        return account_id[0] if account_id else None
    except psycopg2.Error as e:
        print_message(f"Database error getting account ID by user ID: {e}", "error")
        return None
    finally:
        cur.close()
        conn.close()

def get_account_id_by_account_number(account_number):
    conn = get_db_connection()
    if conn is None:
        return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM accounts WHERE account_number = %s;", (account_number,))
        account_id = cur.fetchone()
        return account_id[0] if account_id else None
    except psycopg2.Error as e:
        print_message(f"Database error getting account ID by account number: {e}", "error")
        return None
    finally:
        cur.close()
        conn.close()

def get_user_id_by_username(username):
    conn = get_db_connection()
    if conn is None:
        return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE username = %s;", (username,))
        user_id = cur.fetchone()
        return user_id[0] if user_id else None
    except psycopg2.Error as e:
        print_message(f"Database error getting user ID by username: {e}", "error")
        return None
    finally:
        cur.close()
        conn.close()

def get_username_by_user_id(user_id):
    conn = get_db_connection()
    if conn is None:
        return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT username FROM users WHERE id = %s;", (user_id,))
        username = cur.fetchone()
        return username[0] if username else None
    except psycopg2.Error as e:
        print_message(f"Database error getting username by user ID: {e}", "error")
        return None
    finally:
        cur.close()
        conn.close()

def get_user_details(user_id):
    conn = get_db_connection()
    if conn is None:
        return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT username, full_name, email, phone_number, address, date_of_birth FROM users WHERE id = %s;", (user_id,))
        user_details = cur.fetchone()
        return user_details
    except psycopg2.Error as e:
        print_message(f"Database error getting user details: {e}", "error")
        return None
    finally:
        cur.close()
        conn.close()

def update_user_details(user_id, full_name, email, phone_number, address, date_of_birth_str):
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed."
    cur = conn.cursor()
    try:
        date_of_birth = datetime.datetime.strptime(date_of_birth_str, "%Y-%m-%d").date()
        cur.execute("""
            UPDATE users
            SET full_name = %s, email = %s, phone_number = %s, address = %s, date_of_birth = %s
            WHERE id = %s;
        """, (full_name, email, phone_number, address, date_of_birth, user_id))
        conn.commit()
        return True, "Profile updated successfully."
    except ValueError:
        conn.rollback()
        return False, "Invalid date format. Please use YYYY-MM-DD."
    except psycopg2.errors.UniqueViolation as e:
        conn.rollback()
        if "email" in str(e):
            return False, "Email already registered by another user."
        else:
            return False, f"Database error: {e}"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Database error updating profile: {e}"
    finally:
        cur.close()
        conn.close()

def register_user(username, password, full_name, email, phone_number, address, date_of_birth):
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed."
    cur = conn.cursor()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        cur.execute("INSERT INTO users (username, password_hash, full_name, email, phone_number, address, date_of_birth) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;",
                    (username, hashed_password, full_name, email, phone_number, address, date_of_birth))
        user_id = cur.fetchone()[0]
        conn.commit()
        account_number = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        cur.execute("INSERT INTO accounts (user_id, account_number, balance) VALUES (%s, %s, %s);", (user_id, account_number, 0.0))
        conn.commit()
        return True, f"User '{username}' registered successfully with account number: {account_number}"
    except psycopg2.errors.UniqueViolation as e:
        conn.rollback()
        if "username" in str(e):
            return False, "Username already exists."
        elif "email" in str(e):
            return False, "Email already registered."
        else:
            return False, f"Registration failed due to data conflict: {e}"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Database error during registration: {e}"
    except Exception as e:
        conn.rollback()
        return False, f"An unexpected error occurred during registration: {e}"
    finally:
        cur.close()
        conn.close()

def login_user(username, password):
    conn = get_db_connection()
    if conn is None:
        return None, None, "Database connection failed."
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, password_hash, full_name FROM users WHERE username = %s;", (username,))
        result = cur.fetchone()
        if result:
            user_id, password_hash, full_name = result
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                return user_id, full_name, "Login successful."
        return None, None, "Invalid username or password."
    except psycopg2.Error as e:
        return None, None, f"Database error during login: {e}"
    except Exception as e:
        return None, None, f"An unexpected error occurred during login: {e}"
    finally:
        cur.close()
        conn.close()

def get_user_account(user_id):
    conn = get_db_connection()
    if conn is None:
        return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, account_number, balance, loan_balance FROM accounts WHERE user_id = %s;", (user_id,))
        account_data = cur.fetchone()
        if account_data:
            return BankAccount(account_data[0], user_id, account_data[1], float(account_data[2]))
        return None
    except psycopg2.Error as e:
        print_message(f"Database error getting user account: {e}", "error")
        return None
    finally:
        cur.close()
        conn.close()

def record_transaction(account_id, type, amount, is_public=False, category=None):
    conn = get_db_connection()
    if conn is None:
        print_message("Database connection failed. Cannot record transaction.", "error")
        return
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO transactions (account_id, type, amount, is_public, category) VALUES (%s, %s, %s, %s, %s);", (account_id, type, amount, is_public, category))
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        print_message(f"Database error recording transaction: {e}", "error")
    finally:
        cur.close()
        conn.close()

def get_public_transactions():
    conn = get_db_connection()
    if conn is None:
        print_message("Database connection failed. Cannot retrieve public transactions.", "error")
        return []
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT t.type, t.amount, t.timestamp, u.username
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN users u ON a.user_id = u.id
            WHERE t.is_public = TRUE
            ORDER BY t.timestamp DESC
            LIMIT 20;
        """)
        transactions = cur.fetchall()
        return transactions
    except psycopg2.Error as e:
        print_message(f"Database error retrieving public transactions: {e}", "error")
        return []
    finally:
        cur.close()
        conn.close()

def generate_card(user_id, card_type):
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed."
    cur = conn.cursor()
    card_number = ''.join([str(random.randint(0, 9)) for _ in range(16)])
    expiry_date = (datetime.datetime.now() + datetime.timedelta(days=365*4)).strftime("%m/%y")
    cvv = ''.join([str(random.randint(0, 9)) for _ in range(3)])

    try:
        cur.execute("INSERT INTO cards (user_id, card_number, expiry_date, cvv, card_type) VALUES (%s, %s, %s, %s, %s);",
                    (user_id, card_number, expiry_date, cvv, card_type))
        conn.commit()
        return True, f"{card_type.capitalize()} card generated successfully for user ID {user_id}:\n  Card Number: {card_number}\n  Expiry Date: {expiry_date}\n  CVV: {cvv}"
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False, "Failed to generate unique card number. Please try again."
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Database error generating card: {e}"
    except Exception as e:
        conn.rollback()
        return False, f"An unexpected error occurred during card generation: {e}"
    finally:
        cur.close()
        conn.close()

def display_cards(user_id):
    conn = get_db_connection()
    if conn is None:
        return "Database connection failed. Cannot display cards."
    cur = conn.cursor()
    try:
        cur.execute("SELECT card_number, expiry_date, cvv, card_type FROM cards WHERE user_id = %s;", (user_id,))
        cards = cur.fetchall()
        if cards:
            card_info = "\n--- Your Cards ---\n"
            for i, card in enumerate(cards):
                card_info += f"Card {i+1} ({card[3].capitalize()}):\n"
                card_info += f"  Card Number: {card[0]}\n"
                card_info += f"  Expiry Date: {card[1]}\n"
                card_info += f"  CVV: {card[2]}\n"
            card_info += "-----------------------"
            return card_info
        else:
            return "No cards found for your account."
    except psycopg2.Error as e:
        return f"Database error displaying cards: {e}"
    finally:
        cur.close()
        conn.close()

def apply_for_loan(user_id, amount, interest_rate, term_months):
    if amount <= 0 or interest_rate <= 0 or term_months <= 0:
        return False, "Invalid loan parameters. Amount, interest rate, and term must be positive."

    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed."
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO loans (user_id, amount, interest_rate, term_months, remaining_balance) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
                    (user_id, amount, interest_rate, term_months, amount))
        loan_id = cur.fetchone()[0]
        conn.commit()
        return True, f"Loan application for ${amount:.2f} approved. Loan ID: {loan_id}"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Database error applying for loan: {e}"
    except Exception as e:
        conn.rollback()
        return False, f"An unexpected error occurred during loan application: {e}"
    finally:
        cur.close()
        conn.close()

def view_loans(user_id):
    conn = get_db_connection()
    if conn is None:
        return "Database connection failed. Cannot view loans."
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, amount, interest_rate, term_months, start_date, remaining_balance, status FROM loans WHERE user_id = %s;", (user_id,))
        loans = cur.fetchall()
        if loans:
            loan_info = "\n--- Your Loans ---\n"
            for loan in loans:
                loan_info += f"Loan ID: {loan[0]}\n"
                loan_info += f"  Amount: ${loan[1]:.2f}\n"
                loan_info += f"  Interest Rate: {loan[2]*100:.2f}%\n"
                loan_info += f"  Term: {loan[3]} months\n"
                loan_info += f"  Start Date: {loan[4].strftime('%Y-%m-%d')}\n"
                loan_info += f"  Remaining Balance: ${loan[5]:.2f}\n"
                loan_info += f"  Status: {loan[6].capitalize()}\n"
                loan_info += "--------------------\n"
            return loan_info
        else:
            return "No loans found for your account."
    except psycopg2.Error as e:
        return f"Database error viewing loans: {e}"
    finally:
        cur.close()
        conn.close()

def make_loan_payment(user_id, loan_id, amount):
    if amount <= 0:
        return False, "Payment amount must be positive."

    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed."
    cur = conn.cursor()
    try:
        cur.execute("SELECT remaining_balance FROM loans WHERE id = %s AND user_id = %s;", (loan_id, user_id))
        result = cur.fetchone()
        if not result:
            return False, "Loan not found or does not belong to you."

        remaining_balance = float(result[0])
        if amount > remaining_balance:
            message = f"Payment amount ${amount:.2f} exceeds remaining balance ${remaining_balance:.2f}. Paying full remaining balance."
            amount = remaining_balance
        else:
            message = ""

        new_remaining_balance = remaining_balance - amount
        status = 'paid' if new_remaining_balance <= 0 else 'active'

        cur.execute("UPDATE loans SET remaining_balance = %s, status = %s WHERE id = %s;", (new_remaining_balance, status, loan_id))
        cur.execute("INSERT INTO loan_payments (loan_id, amount) VALUES (%s, %s);", (loan_id, amount))
        conn.commit()
        
        final_message = f"Successfully made payment of ${amount:.2f} for Loan ID {loan_id}."
        if status == 'paid':
            final_message += f"\nLoan ID {loan_id} is now fully paid."
        return True, message + "\n" + final_message if message else final_message
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Database error making loan payment: {e}"
    except Exception as e:
        conn.rollback()
        return False, f"An unexpected error occurred during loan payment: {e}"
    finally:
        cur.close()
        conn.close()

def search_users(query):
    conn = get_db_connection()
    if conn is None:
        return "Database connection failed. Cannot search users."
    cur = conn.cursor()
    try:
        search_pattern = f"%{query}%"
        cur.execute("SELECT id, username, full_name FROM users WHERE username ILIKE %s OR full_name ILIKE %s;", (search_pattern, search_pattern))
        users = cur.fetchall()
        if users:
            user_info = "\n--- Search Results ---\n"
            for user in users:
                user_info += f"User ID: {user[0]}, Username: {user[1]}, Full Name: {user[2]}\n"
            user_info += "----------------------"
            return user_info
        else:
            return "No users found matching your query."
    except psycopg2.Error as e:
        return f"Database error searching users: {e}"
    finally:
        cur.close()
        conn.close()

def request_money(from_user_id, to_username, amount):
    if amount <= 0:
        return False, "Request amount must be positive."

    to_user_id = get_user_id_by_username(to_username)
    if to_user_id is None:
        return False, f"User '{to_username}' not found."

    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed."
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO money_requests (from_user_id, to_user_id, amount) VALUES (%s, %s, %s);",
                    (from_user_id, to_user_id, amount))
        conn.commit()
        return True, f"Money request of ${amount:.2f} sent to '{to_username}'."
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Database error sending money request: {e}"
    except Exception as e:
        conn.rollback()
        return False, f"An unexpected error occurred during money request: {e}"
    finally:
        cur.close()
        conn.close()

def view_money_requests(user_id):
    conn = get_db_connection()
    if conn is None:
        return "Database connection failed. Cannot view money requests."
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT mr.id, u.username, mr.amount, mr.status, mr.request_date
            FROM money_requests mr
            JOIN users u ON mr.from_user_id = u.id
            WHERE mr.to_user_id = %s AND mr.status = 'pending'
            ORDER BY mr.request_date DESC;
        """, (user_id,))
        requests = cur.fetchall()
        if requests:
            request_info = "\n--- Pending Money Requests ---\n"
            for req in requests:
                request_info += f"Request ID: {req[0]}, From: {req[1]}, Amount: ${req[2]:.2f}, Date: {req[4].strftime('%Y-%m-%d %H:%M:%S')}\n"
            request_info += "------------------------------"
            return request_info
        else:
            return "No pending money requests."
    except psycopg2.Error as e:
        return f"Database error viewing money requests: {e}"
    finally:
        cur.close()
        conn.close()

def respond_to_money_request(request_id, user_id, action):
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed."
    cur = conn.cursor()
    try:
        cur.execute("SELECT from_user_id, to_user_id, amount FROM money_requests WHERE id = %s AND to_user_id = %s AND status = 'pending';",
                    (request_id, user_id))
        request_data = cur.fetchone()
        if not request_data:
            return False, "Money request not found or already processed."

        from_user_id, to_user_id, amount = request_data

        if action == 'accept':
            recipient_account = get_user_account(from_user_id)
            if recipient_account is None:
                return False, "Recipient account not found."

            sender_account = get_user_account(to_user_id)
            if sender_account is None:
                return False, "Your account not found."

            if sender_account.balance < amount:
                return False, "Insufficient balance to accept request."

            cur.execute("UPDATE accounts SET balance = balance - %s WHERE user_id = %s;", (amount, to_user_id))
            record_transaction(get_account_id_by_user_id(to_user_id), 'transfer_out', amount, category='Money Request Accepted')

            cur.execute("UPDATE accounts SET balance = balance + %s WHERE user_id = %s;", (amount, from_user_id))
            record_transaction(get_account_id_by_user_id(from_user_id), 'transfer_in', amount, category='Money Request Accepted')

            cur.execute("UPDATE money_requests SET status = 'accepted' WHERE id = %s;", (request_id,))
            conn.commit()
            return True, f"Money request {request_id} accepted. ${amount:.2f} transferred."
        elif action == 'decline':
            cur.execute("UPDATE money_requests SET status = 'declined' WHERE id = %s;", (request_id,))
            conn.commit()
            return True, f"Money request {request_id} declined."
        else:
            return False, "Invalid action. Use 'accept' or 'decline'."
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Database error responding to money request: {e}"
    except Exception as e:
        conn.rollback()
        return False, f"An unexpected error occurred while responding to money request: {e}"
    finally:
        cur.close()
        conn.close()

def add_bill(user_id, bill_name, due_date_obj, amount):
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed."
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO bills (user_id, bill_name, due_date, amount, status) VALUES (%s, %s, %s, %s, %s);",
                    (user_id, bill_name, due_date_obj, amount, 'pending'))
        conn.commit()
        return True, f"Bill '{bill_name}' for ${amount:.2f} due on {due_date_obj.strftime('%Y-%m-%d')} added successfully."
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Database error adding bill: {e}"
    finally:
        cur.close()
        conn.close()

def get_user_bills(user_id):
    conn = get_db_connection()
    if conn is None:
        return []
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, bill_name, due_date, amount, status FROM bills WHERE user_id = %s ORDER BY due_date ASC;", (user_id,))
        bills = cur.fetchall()
        return bills
    except psycopg2.Error as e:
        print_message(f"Database error retrieving user bills: {e}", "error")
        return []
    finally:
        cur.close()
        conn.close()

def pay_bill(user_id, bill_id):
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed."
    cur = conn.cursor()
    try:
        cur.execute("SELECT bill_name, amount, status FROM bills WHERE id = %s AND user_id = %s;", (bill_id, user_id))
        bill_data = cur.fetchone()
        if not bill_data:
            return False, "Bill not found or does not belong to you."

        bill_name, amount, status = bill_data
        if status == 'paid':
            return False, f"Bill '{bill_name}' is already paid."

        account = get_user_account(user_id)
        if account is None:
            return False, "Your account not found."

        if account.balance < amount:
            return False, "Insufficient balance to pay this bill."

        if account.withdraw(amount):
            cur.execute("UPDATE bills SET status = 'paid' WHERE id = %s;", (bill_id,))
            record_transaction(account.account_id, 'bill_payment', amount, category='Bill Payment')
            conn.commit()
            return True, f"Successfully paid bill '{bill_name}' for ${amount:.2f}."
        else:
            conn.rollback()
            return False, "Failed to process payment."
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Database error paying bill: {e}"
    except Exception as e:
        conn.rollback()
        return False, f"An unexpected error occurred during bill payment: {e}"
    finally:
        cur.close()
        conn.close()

LINE_SEP = "=" * 50
SUB_LINE_SEP = "-" * 50
MENU_WIDTH = 50

def print_header(title):
    print(LINE_SEP)
    print(f"{title.center(MENU_WIDTH)}")
    print(LINE_SEP)

def print_menu_item(number, text):
    print(f"{number}. {text}")

def print_footer():
    print(LINE_SEP)

def print_message(message, type="info"):
    if type == "success":
        print(f"\n[SUCCESS] {message}\n")
    elif type == "error":
        print(f"\n[ERROR] {message}\n")
    else:
        print(f"\n[INFO] {message}\n")

def get_validated_string_input(prompt, min_length=1):
    while True:
        value = input(prompt).strip()
        if len(value) >= min_length:
            return value
        else:
            print_message(f"Input cannot be empty and must be at least {min_length} characters.", "error")

def get_validated_float_input(prompt, min_value=0.01):
    while True:
        try:
            value = float(input(prompt))
            if value >= min_value:
                return value
            else:
                print_message(f"Amount must be a positive number (at least {min_value:.2f}).", "error")
        except ValueError:
            print_message("Invalid amount. Please enter a number.", "error")

def get_validated_int_input(prompt, min_value=1):
    while True:
        try:
            value = int(input(prompt))
            if value >= min_value:
                return value
            else:
                print_message(f"Input must be a positive integer (at least {min_value}).", "error")
        except ValueError:
            print_message("Invalid input. Please enter an integer.", "error")

def get_validated_email_input(prompt):
    email_regex = r"^(?:[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-zA-Z0-9-]*[a-zA-Z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x5f-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])$"
    while True:
        email = input(prompt).strip()
        if re.match(email_regex, email):
            return email
        else:
            print_message("Invalid email format. Please enter a valid email address (e.g., user@example.com).", "error")

def get_validated_phone_input(prompt):
    phone_regex = r"^\+?[\d\s\-\(\)]{7,20}$" 
    while True:
        phone = input(prompt).strip()
        if re.match(phone_regex, phone):
            return phone
        else:
            print_message("Invalid phone number format. Please enter a valid phone number (e.g., +1-555-123-4567).", "error")

def get_validated_date_input(prompt):
    while True:
        date_str = input(prompt).strip()
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return date_obj
        except ValueError:
            print_message("Invalid date format. Please use YYYY-MM-DD.", "error")

def get_validated_account_number_input(prompt):
    while True:
        account_number = input(prompt).strip()
        if account_number.isdigit() and len(account_number) == 10:
            return account_number
        else:
            print_message("Invalid account number. Must be a 10-digit number.", "error")

def cli_register_user():
    print_header("REGISTER NEW ACCOUNT")
    username = get_validated_string_input("Enter Username: ", min_length=3)
    password = get_validated_string_input("Enter Password (min 6 chars): ", min_length=6)
    full_name = get_validated_string_input("Enter Full Name: ")
    email = get_validated_email_input("Enter Email: ")
    phone_number = get_validated_phone_input("Enter Phone Number: ")
    address = get_validated_string_input("Enter Address: ")
    date_of_birth = get_validated_date_input("Enter Date of Birth (YYYY-MM-DD): ")
    print(SUB_LINE_SEP)

    success, message = register_user(username, password, full_name, email, phone_number, address, date_of_birth)
    if success:
        print_message(message, "success")
    else:
        print_message(message, "error")
    print_footer()

def cli_login_user():
    print_header("USER LOGIN")
    username = get_validated_string_input("Enter Username: ")
    password = get_validated_string_input("Enter Password: ")
    print(SUB_LINE_SEP)
    
    user_id, full_name, message = login_user(username, password)
    if user_id:
        print_message(message, "success")
    else:
        print_message(message, "error")
    print_footer()
    return user_id, username, full_name

def cli_account_operations(user_id):
    while True:
        account = get_user_account(user_id)
        if not account:
            print_message("Error: Could not retrieve bank account.", "error")
            return

        print_header("ACCOUNT OPERATIONS")
        print_menu_item("1", "Deposit Funds")
        print_menu_item("2", "Withdraw Funds")
        print_menu_item("3", "View Balance")
        print_menu_item("4", "Back to Main Menu")
        print_footer()
        choice = input("Enter your choice: ")
        print(SUB_LINE_SEP)

        if choice == '1':
            amount = get_validated_float_input("Enter amount to deposit: ")
            if account.deposit(amount):
                record_transaction(get_account_id_by_user_id(user_id), 'deposit', amount)
                print_message(f"Successfully deposited ${amount:.2f}.", "success")
            else:
                print_message("Deposit failed.", "error")
        elif choice == '2':
            amount = get_validated_float_input("Enter amount to withdraw: ")
            if account.withdraw(amount):
                record_transaction(get_account_id_by_user_id(user_id), 'withdraw', amount)
                print_message(f"Successfully withdrew ${amount:.2f}.", "success")
            else:
                print_message("Invalid withdrawal amount or insufficient balance.", "error")
        elif choice == '3':
            print_message(f"Current Balance: ${account.get_balance():.2f}", "info")
        elif choice == '4':
            break
        else:
            print_message("Invalid choice. Please try again.", "error")

def cli_public_transaction_feed():
    print_header("PUBLIC TRANSACTION FEED")
    transactions = get_public_transactions()
    if transactions:
        for t in transactions:
            print(f"[{t[2].strftime('%Y-%m-%d %H:%M:%S')}] {t[3]} {t[0].replace('_', ' ').capitalize()} ${t[1]:.2f}")
    else:
        print_message("No public transactions available.", "info")
    print_footer()

def cli_card_operations(user_id):
    while True:
        print_header("CARD OPERATIONS")
        print_menu_item("1", "Generate Debit Card")
        print_menu_item("2", "Generate Credit Card")
        print_menu_item("3", "View My Cards")
        print_menu_item("4", "Back to Main Menu")
        print_footer()
        choice = input("Enter your choice: ")
        print(SUB_LINE_SEP)

        if choice == '1':
            success, message = generate_card(user_id, 'debit')
            if success:
                print_message(message, "success")
            else:
                print_message(message, "error")
        elif choice == '2':
            success, message = generate_card(user_id, 'credit')
            if success:
                print_message(message, "success")
            else:
                print_message(message, "error")
        elif choice == '3':
            cards_text = display_cards(user_id)
            print_message(cards_text, "info")
        elif choice == '4':
            break
        else:
            print_message("Invalid choice. Please try again.", "error")

def cli_transfer_funds(user_id):
    print_header("TRANSFER FUNDS")
    to_account_number = get_validated_account_number_input("Recipient's Account Number (10 digits): ")
    amount = get_validated_float_input("Enter amount to transfer: ")
    success, message = transfer_funds(user_id, to_account_number, amount)
    if success:
        print_message(message, "success")
    else:
        print_message(message, "error")
    print_footer()

def cli_loans(user_id):
    while True:
        print_header("LOAN OPERATIONS")
        print_menu_item("1", "Apply for Loan")
        print_menu_item("2", "View My Loans")
        print_menu_item("3", "Make Loan Payment")
        print_menu_item("4", "Back to Main Menu")
        print_footer()
        choice = input("Enter your choice: ")
        print(SUB_LINE_SEP)

        if choice == '1':
            cli_apply_for_loan(user_id)
        elif choice == '2':
            loans_text = view_loans(user_id)
            print_message(loans_text, "info")
        elif choice == '3':
            cli_make_loan_payment(user_id)
        elif choice == '4':
            break
        else:
            print_message("Invalid choice. Please try again.", "error")

def cli_apply_for_loan(user_id):
    print_header("APPLY FOR LOAN")
    amount = get_validated_float_input("Loan Amount: ")
    interest_rate = get_validated_float_input("Annual Interest Rate (e.g., 0.05 for 5%): ", min_value=0.0001)
    term_months = get_validated_int_input("Loan Term in Months: ")
    success, message = apply_for_loan(user_id, amount, interest_rate, term_months)
    if success:
        print_message(message, "success")
    else:
        print_message(message, "error")
    print_footer()

def cli_make_loan_payment(user_id):
    print_header("MAKE LOAN PAYMENT")
    loan_id = get_validated_int_input("Loan ID: ")
    amount = get_validated_float_input("Payment Amount: ")
    success, message = make_loan_payment(user_id, loan_id, amount)
    if success:
        print_message(message, "success")
    else:
        print_message(message, "error")
    print_footer()

def cli_search_users():
    print_header("SEARCH USERS")
    query = get_validated_string_input("Search Query (username or full name): ")
    results = search_users(query)
    print_message(results, "info")
    print_footer()

def cli_money_requests(user_id):
    while True:
        print_header("MONEY REQUEST OPERATIONS")
        print_menu_item("1", "Send Money Request")
        print_menu_item("2", "View Pending Requests")
        print_menu_item("3", "Respond to Request")
        print_menu_item("4", "Back to Main Menu")
        print_footer()
        choice = input("Enter your choice: ")
        print(SUB_LINE_SEP)

        if choice == '1':
            cli_send_money_request(user_id)
        elif choice == '2':
            requests_text = view_money_requests(user_id)
            print_message(requests_text, "info")
        elif choice == '3':
            cli_respond_to_money_request(user_id)
        elif choice == '4':
            break
        else:
            print_message("Invalid choice. Please try again.", "error")

def cli_send_money_request(user_id):
    print_header("SEND MONEY REQUEST")
    to_username = get_validated_string_input("Recipient Username: ")
    amount = get_validated_float_input("Enter amount to request: ")
    success, message = request_money(user_id, to_username, amount)
    if success:
        print_message(message, "success")
    else:
        print_message(message, "error")
    print_footer()

def cli_respond_to_money_request(user_id):
    print_header("RESPOND TO MONEY REQUEST")
    request_id = get_validated_int_input("Request ID: ")
    action = get_validated_string_input("Action (accept/decline): ").lower()
    if action not in ['accept', 'decline']:
        print_message("Invalid action. Please type 'accept' or 'decline'.", "error")
        return
    success, message = respond_to_money_request(request_id, user_id, action)
    if success:
        print_message(message, "success")
    else:
        print_message(message, "error")
    print_footer()

def cli_bill_operations(user_id):
    while True:
        print_header("BILL PAYMENT OPERATIONS")
        print_menu_item("1", "Add New Bill")
        print_menu_item("2", "View My Bills")
        print_menu_item("3", "Pay a Bill")
        print_menu_item("4", "Back to Main Menu")
        print_footer()
        choice = input("Enter your choice: ")
        print(SUB_LINE_SEP)

        if choice == '1':
            print_header("ADD NEW BILL")
            bill_name = get_validated_string_input("Bill Name: ")
            due_date_obj = get_validated_date_input("Due Date (YYYY-MM-DD): ")
            amount = get_validated_float_input("Amount: ")
            success, message = add_bill(user_id, bill_name, due_date_obj, amount)
            if success:
                print_message(message, "success")
            else:
                print_message(message, "error")
            print_footer()
        elif choice == '2':
            print_header("MY BILLS")
            bills = get_user_bills(user_id)
            if bills:
                for bill in bills:
                    print(f"ID: {bill[0]}, Name: {bill[1]}, Due: {bill[2]}, Amount: ${bill[3]:.2f}, Status: {bill[4].capitalize()}")
            else:
                print_message("No bills found.", "info")
            print_footer()
        elif choice == '3':
            print_header("PAY A BILL")
            bill_id = get_validated_int_input("Enter Bill ID to pay: ")
            success, message = pay_bill(user_id, bill_id)
            if success:
                print_message(message, "success")
            else:
                print_message(message, "error")
            print_footer()
        elif choice == '4':
            break
        else:
            print_message("Invalid choice. Please try again.", "error")

def main():
    create_tables()
    logged_in_user_id = None
    logged_in_username = None
    logged_in_full_name = None

    while True:
        if logged_in_user_id is None:
            print_header("WELCOME TO ZELDABANK")
            print_menu_item("1", "Register New Account")
            print_menu_item("2", "Login to Existing Account")
            print_menu_item("3", "Exit Application")
            print_footer()
            choice = input("Enter your choice: ")
            print(SUB_LINE_SEP)

            if choice == '1':
                cli_register_user()
            elif choice == '2':
                user_id, username, full_name = cli_login_user()
                if user_id:
                    logged_in_user_id = user_id
                    logged_in_username = username
                    logged_in_full_name = full_name
            elif choice == '3':
                print_message("Exiting. Goodbye!", "info")
                break
            else:
                print_message("Invalid choice. Please try again.", "error")
        else:
            print_header(f"WELCOME, {logged_in_username.upper()}!")
            print_menu_item("1", "Account Operations")
            print_menu_item("2", "Card Operations")
            print_menu_item("3", "View Transaction History")
            print_menu_item("4", "Transfer Funds")
            print_menu_item("5", "Loans")
            print_menu_item("6", "Search Users")
            print_menu_item("7", "Money Requests")
            print_menu_item("8", "Public Transaction Feed")
            print_menu_item("9", "Bill Payments")
            print_menu_item("10", "Logout")
            print_footer()
            choice = input("Enter your choice: ")
            print(SUB_LINE_SEP)

            if choice == '1':
                cli_account_operations(logged_in_user_id)
            elif choice == '2':
                cli_card_operations(logged_in_user_id)
            elif choice == '3':
                transactions_text = view_transaction_history(logged_in_user_id)
                print_message(transactions_text, "info")
            elif choice == '4':
                cli_transfer_funds(logged_in_user_id)
            elif choice == '5':
                cli_loans(logged_in_user_id)
            elif choice == '6':
                cli_search_users()
            elif choice == '7':
                cli_money_requests(logged_in_user_id)
            elif choice == '8':
                cli_public_transaction_feed()
            elif choice == '9':
                cli_bill_operations(logged_in_user_id)
            elif choice == '10':
                logged_in_user_id = None
                logged_in_username = None
                logged_in_full_name = None
                print_message("Logged out successfully.", "info")
            else:
                print_message("Invalid choice. Please try again.", "error")

if __name__ == "__main__":
    main()
