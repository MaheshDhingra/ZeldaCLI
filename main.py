import os
import psycopg2
from dotenv import load_dotenv
import bcrypt
import random
import datetime
load_dotenv()

class BankAccount:
    def __init__(self, account_id, user_id, account_number, balance=0.0):
        self.account_id = account_id
        self.user_id = user_id
        self.account_number = account_number
        self.balance = balance

    def save_balance(self):
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE accounts SET balance = %s WHERE id = %s;", (self.balance, self.account_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error saving balance: {e}")
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
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        -- DROP TABLE IF EXISTS chats CASCADE;
        -- DROP TABLE IF EXISTS money_requests CASCADE;
        -- DROP TABLE IF EXISTS loan_payments CASCADE;
        -- DROP TABLE IF EXISTS loans CASCADE;
        -- DROP TABLE IF EXISTS cards CASCADE;
        -- DROP TABLE IF EXISTS transactions CASCADE;
        -- DROP TABLE IF EXISTS accounts CASCADE;
        -- DROP TABLE IF EXISTS users CASCADE;

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
            type VARCHAR(20) NOT NULL, -- e.g., 'deposit', 'withdraw', 'transfer_in', 'transfer_out', 'public_transfer', 'bill_payment', 'loan_payment'
            amount DECIMAL(10, 2) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_public BOOLEAN DEFAULT FALSE,
            category VARCHAR(50) -- New column for categorization
        );
        CREATE TABLE IF NOT EXISTS recurring_transfers (
            id SERIAL PRIMARY KEY,
            from_account_id INTEGER REFERENCES accounts(id),
            to_account_number VARCHAR(20) NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            frequency VARCHAR(20) NOT NULL, -- e.g., 'daily', 'weekly', 'monthly'
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
            status VARCHAR(20) DEFAULT 'pending' -- 'pending', 'paid', 'overdue'
        );
        CREATE TABLE IF NOT EXISTS cards (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            card_number VARCHAR(16) UNIQUE NOT NULL,
            expiry_date VARCHAR(5) NOT NULL,
            cvv VARCHAR(3) NOT NULL,
            card_type VARCHAR(10) NOT NULL, -- 'credit' or 'debit'
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
        # Deduct from sender
        cur.execute("UPDATE accounts SET balance = balance - %s WHERE user_id = %s;", (amount, from_user_id))
        record_transaction(get_account_id_by_user_id(from_user_id), 'transfer_out', amount)

        # Add to recipient
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
    cur = conn.cursor()
    cur.execute("SELECT id FROM accounts WHERE user_id = %s;", (user_id,))
    account_id = cur.fetchone()
    cur.close()
    conn.close()
    return account_id[0] if account_id else None

def get_account_id_by_account_number(account_number):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM accounts WHERE account_number = %s;", (account_number,))
    account_id = cur.fetchone()
    cur.close()
    conn.close()
    return account_id[0] if account_id else None

def get_user_id_by_username(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s;", (username,))
    user_id = cur.fetchone()
    cur.close()
    conn.close()
    return user_id[0] if user_id else None

def get_username_by_user_id(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id = %s;", (user_id,))
    username = cur.fetchone()
    cur.close()
    conn.close()
    return username[0] if username else None

def get_user_details(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, full_name, email, phone_number, address, date_of_birth FROM users WHERE id = %s;", (user_id,))
    user_details = cur.fetchone()
    cur.close()
    conn.close()
    return user_details

def update_user_details(user_id, full_name, email, phone_number, address, date_of_birth_str):
    conn = get_db_connection()
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
            return False, f"Failed to update profile: {e}"
    except Exception as e:
        conn.rollback()
        return False, f"Failed to update profile: {e}"
    finally:
        cur.close()
        conn.close()

def register_user(username, password, full_name, email, phone_number, address, date_of_birth):
    conn = get_db_connection()
    cur = conn.cursor()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        cur.execute("INSERT INTO users (username, password_hash, full_name, email, phone_number, address, date_of_birth) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;",
                    (username, hashed_password, full_name, email, phone_number, address, date_of_birth))
        user_id = cur.fetchone()[0]
        conn.commit()
        # Create a default bank account for the new user
        account_number = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        cur.execute("INSERT INTO accounts (user_id, account_number, balance) VALUES (%s, %s, %s);", (user_id, account_number, 0.0))
        conn.commit()
        return True, f"User '{username}' registered successfully with account number: {account_number}"
    except psycopg2.errors.UniqueViolation as e:
        if "username" in str(e):
            return False, "Username already exists."
        elif "email" in str(e):
            return False, "Email already registered."
        else:
            return False, f"Registration failed: {e}"
        conn.rollback()
    except Exception as e:
        return False, f"Registration failed: {e}"
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def login_user(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash, full_name FROM users WHERE username = %s;", (username,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        user_id, password_hash, full_name = result
        if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            return user_id, full_name, "Login successful."
    return None, None, "Invalid username or password."

def get_user_account(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, account_number, balance, loan_balance FROM accounts WHERE user_id = %s;", (user_id,))
    account_data = cur.fetchone()
    cur.close()
    conn.close()
    if account_data:
        return BankAccount(account_data[0], user_id, account_data[1], float(account_data[2]))
    return None

def record_transaction(account_id, type, amount, is_public=False, category=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO transactions (account_id, type, amount, is_public, category) VALUES (%s, %s, %s, %s, %s);", (account_id, type, amount, is_public, category))
    conn.commit()
    cur.close()
    conn.close()

def get_public_transactions():
    conn = get_db_connection()
    cur = conn.cursor()
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
    cur.close()
    conn.close()
    return transactions

def generate_card(user_id, card_type):
    conn = get_db_connection()
    cur = conn.cursor()
    card_number = ''.join([str(random.randint(0, 9)) for _ in range(16)])
    expiry_date = (datetime.datetime.now() + datetime.timedelta(days=365*4)).strftime("%m/%y") # 4 years from now
    cvv = ''.join([str(random.randint(0, 9)) for _ in range(3)])

    try:
        cur.execute("INSERT INTO cards (user_id, card_number, expiry_date, cvv, card_type) VALUES (%s, %s, %s, %s, %s);",
                    (user_id, card_number, expiry_date, cvv, card_type))
        conn.commit()
        return True, f"{card_type.capitalize()} card generated successfully for user ID {user_id}:\n  Card Number: {card_number}\n  Expiry Date: {expiry_date}\n  CVV: {cvv}"
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False, "Failed to generate unique card number. Please try again."
    finally:
        cur.close()
        conn.close()

def display_cards(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT card_number, expiry_date, cvv, card_type FROM cards WHERE user_id = %s;", (user_id,))
    cards = cur.fetchall()
    cur.close()
    conn.close()

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

def generate_ascii_art_card(card_number, expiry_date, cvv, card_type):
    card_art = "\n" + "="*40 + "\n"
    card_art += f"|{' ' * 38}|\n"
    card_art += f"|{card_type.upper().ljust(38)}|\n"
    card_art += f"|{' ' * 38}|\n"
    card_art += f"|{'**** **** **** ' + card_number[12:].ljust(22)}|\n"
    card_art += f"|{' ' * 38}|\n"
    card_art += f"|{'EXP: ' + expiry_date.ljust(10)}{'CVV: ' + cvv.ljust(10).rjust(18)}|\n"
    card_art += f"|{' ' * 38}|\n"
    card_art += f"|{'CARDHOLDER NAME'.ljust(38)}|\n"
    card_art += f"|{' ' * 38}|\n"
    card_art += "="*40 + "\n"
    return card_art

def apply_for_loan(user_id, amount, interest_rate, term_months):
    if amount <= 0 or interest_rate <= 0 or term_months <= 0:
        return False, "Invalid loan parameters."

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO loans (user_id, amount, interest_rate, term_months, remaining_balance) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
                    (user_id, amount, interest_rate, term_months, amount))
        loan_id = cur.fetchone()[0]
        conn.commit()
        return True, f"Loan application for ${amount:.2f} approved. Loan ID: {loan_id}"
    except Exception as e:
        conn.rollback()
        return False, f"Loan application failed: {e}"
    finally:
        cur.close()
        conn.close()

def view_loans(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, amount, interest_rate, term_months, start_date, remaining_balance, status FROM loans WHERE user_id = %s;", (user_id,))
    loans = cur.fetchall()
    cur.close()
    conn.close()

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

def make_loan_payment(user_id, loan_id, amount):
    if amount <= 0:
        return False, "Payment amount must be positive."

    conn = get_db_connection()
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
    except Exception as e:
        conn.rollback()
        return False, f"Loan payment failed: {e}"
    finally:
        cur.close()
        conn.close()

def search_users(query):
    conn = get_db_connection()
    cur = conn.cursor()
    search_pattern = f"%{query}%"
    cur.execute("SELECT id, username, full_name FROM users WHERE username ILIKE %s OR full_name ILIKE %s;", (search_pattern, search_pattern))
    users = cur.fetchall()
    cur.close()
    conn.close()

    if users:
        user_info = "\n--- Search Results ---\n"
        for user in users:
            user_info += f"User ID: {user[0]}, Username: {user[1]}, Full Name: {user[2]}\n"
        user_info += "----------------------"
        return user_info
    else:
        return "No users found matching your query."

def request_money(from_user_id, to_username, amount):
    if amount <= 0:
        return False, "Request amount must be positive."

    to_user_id = get_user_id_by_username(to_username)
    if not to_user_id:
        return False, f"User '{to_username}' not found."

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO money_requests (from_user_id, to_user_id, amount) VALUES (%s, %s, %s);",
                    (from_user_id, to_user_id, amount))
        conn.commit()
        return True, f"Money request of ${amount:.2f} sent to '{to_username}'."
    except Exception as e:
        conn.rollback()
        return False, f"Failed to send money request: {e}"
    finally:
        cur.close()
        conn.close()

def view_money_requests(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT mr.id, u.username, mr.amount, mr.status, mr.request_date
        FROM money_requests mr
        JOIN users u ON mr.from_user_id = u.id
        WHERE mr.to_user_id = %s AND mr.status = 'pending'
        ORDER BY mr.request_date DESC;
    """, (user_id,))
    requests = cur.fetchall()
    cur.close()
    conn.close()

    if requests:
        request_info = "\n--- Pending Money Requests ---\n"
        for req in requests:
            request_info += f"Request ID: {req[0]}, From: {req[1]}, Amount: ${req[2]:.2f}, Date: {req[4].strftime('%Y-%m-%d %H:%M:%S')}\n"
        request_info += "------------------------------"
        return request_info
    else:
        return "No pending money requests."

def respond_to_money_request(request_id, user_id, action):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT from_user_id, to_user_id, amount FROM money_requests WHERE id = %s AND to_user_id = %s AND status = 'pending';",
                    (request_id, user_id))
        request_data = cur.fetchone()
        if not request_data:
            return False, "Money request not found or already processed."

        from_user_id, to_user_id, amount = request_data

        if action == 'accept':
            # Get the recipient's account number (from_user_id is the one who requested, so they are the recipient)
            recipient_account = get_user_account(from_user_id)
            if not recipient_account:
                return False, "Recipient account not found."

            # The user responding (to_user_id) is the sender
            sender_account = get_user_account(to_user_id)
            if not sender_account:
                return False, "Your account not found."

            if sender_account.balance < amount:
                return False, "Insufficient balance to accept request."

            # Perform the transfer directly
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
    except Exception as e:
        conn.rollback()
        return False, f"Failed to respond to money request: {e}"
    finally:
        cur.close()
        conn.close()

def add_bill(user_id, bill_name, due_date_str, amount):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
        cur.execute("INSERT INTO bills (user_id, bill_name, due_date, amount, status) VALUES (%s, %s, %s, %s, %s);",
                    (user_id, bill_name, due_date, amount, 'pending'))
        conn.commit()
        return True, f"Bill '{bill_name}' for ${amount:.2f} due on {due_date_str} added successfully."
    except ValueError:
        conn.rollback()
        return False, "Invalid date format. Please use YYYY-MM-DD."
    except Exception as e:
        conn.rollback()
        return False, f"Failed to add bill: {e}"
    finally:
        cur.close()
        conn.close()

def get_user_bills(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, bill_name, due_date, amount, status FROM bills WHERE user_id = %s ORDER BY due_date ASC;", (user_id,))
    bills = cur.fetchall()
    cur.close()
    conn.close()
    return bills

def pay_bill(user_id, bill_id):
    conn = get_db_connection()
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
        if not account:
            return False, "Your account not found."

        if account.balance < amount:
            return False, "Insufficient balance to pay this bill."

        if account.withdraw(amount): # This will also save the balance
            cur.execute("UPDATE bills SET status = 'paid' WHERE id = %s;", (bill_id,))
            record_transaction(account.account_id, 'bill_payment', amount, category='Bill Payment')
            conn.commit()
            return True, f"Successfully paid bill '{bill_name}' for ${amount:.2f}."
        else:
            conn.rollback()
            return False, "Failed to process payment."
    except Exception as e:
        conn.rollback()
        return False, f"Failed to pay bill: {e}"
    finally:
        cur.close()
        conn.close()

def cli_register_user():
    print("\n--- Register ---")
    username = input("Username: ")
    password = input("Password: ")
    full_name = input("Full Name: ")
    email = input("Email: ")
    phone_number = input("Phone Number: ")
    address = input("Address: ")
    date_of_birth_str = input("Date of Birth (YYYY-MM-DD): ")

    try:
        date_of_birth = datetime.datetime.strptime(date_of_birth_str, "%Y-%m-%d").date()
        success, message = register_user(username, password, full_name, email, phone_number, address, date_of_birth)
        print(message)
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
    except Exception as e:
        print(f"Registration failed: {e}")

def cli_login_user():
    print("\n--- Login ---")
    username = input("Username: ")
    password = input("Password: ")
    
    user_id, full_name, message = login_user(username, password)
    print(message)
    return user_id, username, full_name

def cli_account_operations(user_id):
    while True:
        account = get_user_account(user_id)
        if not account:
            print("Error: Could not retrieve bank account.")
            return

        print("\n--- Account Operations ---")
        print("1. Deposit")
        print("2. Withdraw")
        print("3. View Balance")
        print("4. Back to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            try:
                amount = float(input("Enter amount to deposit: "))
                if account.deposit(amount):
                    record_transaction(get_account_id_by_user_id(user_id), 'deposit', amount)
                    print(f"Successfully deposited ${amount:.2f}.")
                else:
                    print("Deposit amount must be positive.")
            except ValueError:
                print("Invalid amount. Please enter a number.")
        elif choice == '2':
            try:
                amount = float(input("Enter amount to withdraw: "))
                if account.withdraw(amount):
                    record_transaction(get_account_id_by_user_id(user_id), 'withdraw', amount)
                    print(f"Successfully withdrew ${amount:.2f}.")
                else:
                    print("Invalid withdrawal amount or insufficient balance.")
            except ValueError:
                print("Invalid amount. Please enter a number.")
        elif choice == '3':
            print(f"Current Balance: ${account.get_balance():.2f}")
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

def cli_public_transaction_feed():
    print("\n--- Public Transaction Feed ---")
    transactions = get_public_transactions()
    if transactions:
        for t in transactions:
            print(f"[{t[2].strftime('%Y-%m-%d %H:%M:%S')}] {t[3]} {t[0]} ${t[1]:.2f}")
    else:
        print("No public transactions available.")

def cli_card_operations(user_id):
    while True:
        print("\n--- Card Operations ---")
        print("1. Generate Debit Card")
        print("2. Generate Credit Card")
        print("3. View My Cards")
        print("4. Back to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            success, message = generate_card(user_id, 'debit')
            print(message)
        elif choice == '2':
            success, message = generate_card(user_id, 'credit')
            print(message)
        elif choice == '3':
            cards_text = display_cards(user_id)
            print(cards_text)
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

def cli_transfer_funds(user_id):
    print("\n--- Transfer Funds ---")
    to_account_number = input("Recipient's Account Number: ")
    try:
        amount = float(input("Enter amount to transfer: "))
        success, message = transfer_funds(user_id, to_account_number, amount)
        print(message)
    except ValueError:
        print("Invalid amount. Please enter a number.")

def cli_loans(user_id):
    while True:
        print("\n--- Loan Operations ---")
        print("1. Apply for Loan")
        print("2. View My Loans")
        print("3. Make Loan Payment")
        print("4. Back to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            cli_apply_for_loan(user_id)
        elif choice == '2':
            loans_text = view_loans(user_id)
            print(loans_text)
        elif choice == '3':
            cli_make_loan_payment(user_id)
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

def cli_apply_for_loan(user_id):
    print("\n--- Apply for Loan ---")
    try:
        amount = float(input("Loan Amount: "))
        interest_rate = float(input("Annual Interest Rate (e.g., 0.05 for 5%): "))
        term_months = int(input("Loan Term in Months: "))
        success, message = apply_for_loan(user_id, amount, interest_rate, term_months)
        print(message)
    except ValueError:
        print("Invalid input. Please enter numbers for amount, rate, and term.")

def cli_make_loan_payment(user_id):
    print("\n--- Make Loan Payment ---")
    try:
        loan_id = int(input("Loan ID: "))
        amount = float(input("Payment Amount: "))
        success, message = make_loan_payment(user_id, loan_id, amount)
        print(message)
    except ValueError:
        print("Invalid input. Please enter numbers for loan ID and amount.")

def cli_search_users():
    print("\n--- Search Users ---")
    query = input("Search Query (username or full name): ")
    results = search_users(query)
    print(results)

def cli_money_requests(user_id):
    while True:
        print("\n--- Money Request Operations ---")
        print("1. Send Money Request")
        print("2. View Pending Requests")
        print("3. Respond to Request")
        print("4. Back to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            cli_send_money_request(user_id)
        elif choice == '2':
            requests_text = view_money_requests(user_id)
            print(requests_text)
        elif choice == '3':
            cli_respond_to_money_request(user_id)
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

def cli_send_money_request(user_id):
    print("\n--- Send Money Request ---")
    to_username = input("Recipient Username: ")
    try:
        amount = float(input("Enter amount to request: "))
        success, message = request_money(user_id, to_username, amount)
        print(message)
    except ValueError:
        print("Invalid amount. Please enter a number.")

def cli_respond_to_money_request(user_id):
    print("\n--- Respond to Money Request ---")
    try:
        request_id = int(input("Request ID: "))
        action = input("Action (accept/decline): ").lower()
        success, message = respond_to_money_request(request_id, user_id, action)
        print(message)
    except ValueError:
        print("Invalid Request ID. Please enter a number.")

def cli_bill_operations(user_id):
    while True:
        print("\n--- Bill Payment Operations ---")
        print("1. Add New Bill")
        print("2. View My Bills")
        print("3. Pay a Bill")
        print("4. Back to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("\n--- Add New Bill ---")
            bill_name = input("Bill Name: ")
            due_date_str = input("Due Date (YYYY-MM-DD): ")
            try:
                amount = float(input("Amount: "))
                success, message = add_bill(user_id, bill_name, due_date_str, amount)
                print(message)
            except ValueError:
                print("Invalid amount. Please enter a number.")
        elif choice == '2':
            print("\n--- My Bills ---")
            bills = get_user_bills(user_id)
            if bills:
                for bill in bills:
                    print(f"ID: {bill[0]}, Name: {bill[1]}, Due: {bill[2]}, Amount: ${bill[3]:.2f}, Status: {bill[4].capitalize()}")
            else:
                print("No bills found.")
        elif choice == '3':
            print("\n--- Pay a Bill ---")
            try:
                bill_id = int(input("Enter Bill ID to pay: "))
                success, message = pay_bill(user_id, bill_id)
                print(message)
            except ValueError:
                print("Invalid Bill ID. Please enter a number.")
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

def main():
    create_tables()
    logged_in_user_id = None
    logged_in_username = None
    logged_in_full_name = None

    while True:
        if logged_in_user_id is None:
            print("\n--- Welcome to Internet Banking ---")
            print("1. Register")
            print("2. Login")
            print("3. Exit")
            choice = input("Enter your choice: ")

            if choice == '1':
                cli_register_user()
            elif choice == '2':
                user_id, username, full_name = cli_login_user()
                if user_id:
                    logged_in_user_id = user_id
                    logged_in_username = username
                    logged_in_full_name = full_name
            elif choice == '3':
                print("Exiting. Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")
        else:
            print(f"\n--- Welcome, {logged_in_username}! ---")
            print("1. Account Operations")
            print("2. Card Operations")
            print("3. View Transaction History")
            print("4. Transfer Funds")
            print("5. Loans")
            print("6. Search Users")
            print("7. Money Requests")
            print("8. Public Transaction Feed") # New Feature 1
            print("9. Bill Payments") # New Feature 2
            print("10. Logout")
            choice = input("Enter your choice: ")

            if choice == '1':
                cli_account_operations(logged_in_user_id)
            elif choice == '2':
                cli_card_operations(logged_in_user_id)
            elif choice == '3':
                transactions_text = view_transaction_history(logged_in_user_id)
                print(transactions_text)
            elif choice == '4':
                cli_transfer_funds(logged_in_user_id)
            elif choice == '5':
                cli_loans(logged_in_user_id)
            elif choice == '6':
                cli_search_users()
            elif choice == '7':
                cli_money_requests(logged_in_user_id)
            elif choice == '8': # New Feature 1
                cli_public_transaction_feed()
            elif choice == '9': # New Feature 2
                cli_bill_operations(logged_in_user_id)
            elif choice == '10':
                logged_in_user_id = None
                logged_in_username = None
                logged_in_full_name = None
                print("Logged out successfully.")
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
