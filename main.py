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

def cli_user_profile_management(user_id):
    while True:
        print("\n--- User Profile Management ---")
        print("1. View Profile")
        print("2. Update Profile")
        print("3. Back to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            user_details = get_user_details(user_id)
            if user_details:
                print("\n--- Your Profile ---")
                print(f"Username: {user_details[0]}")
                print(f"Full Name: {user_details[1] if user_details[1] else 'N/A'}")
                print(f"Email: {user_details[2] if user_details[2] else 'N/A'}")
                print(f"Phone Number: {user_details[3] if user_details[3] else 'N/A'}")
                print(f"Address: {user_details[4] if user_details[4] else 'N/A'}")
                print(f"Date of Birth: {user_details[5].strftime('%Y-%m-%d') if user_details[5] else 'N/A'}")
                print("--------------------")
            else:
                print("Could not retrieve profile details.")
        elif choice == '2':
            print("\n--- Update Profile ---")
            print("Enter new details (leave blank to keep current value):")
            current_details = get_user_details(user_id)
            
            full_name = input(f"Full Name ({current_details[1] if current_details[1] else 'N/A'}): ")
            email = input(f"Email ({current_details[2] if current_details[2] else 'N/A'}): ")
            phone_number = input(f"Phone Number ({current_details[3] if current_details[3] else 'N/A'}): ")
            address = input(f"Address ({current_details[4] if current_details[4] else 'N/A'}): ")
            date_of_birth_str = input(f"Date of Birth (YYYY-MM-DD) ({current_details[5].strftime('%Y-%m-%d') if current_details[5] else 'N/A'}): ")

            # Use current values if new input is blank
            full_name = full_name if full_name else current_details[1]
            email = email if email else current_details[2]
            phone_number = phone_number if phone_number else current_details[3]
            address = address if address else current_details[4]
            date_of_birth_str = date_of_birth_str if date_of_birth_str else (current_details[5].strftime('%Y-%m-%d') if current_details[5] else None)

            success, message = update_user_details(user_id, full_name, email, phone_number, address, date_of_birth_str)
            print(message)
        elif choice == '3':
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
            print("10. User Profile") # New Feature 3
            print("11. Logout")
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
            elif choice == '10': # New Feature 3
                cli_user_profile_management(logged_in_user_id)
            elif choice == '11':
                logged_in_user_id = None
                logged_in_username = None
                logged_in_full_name = None
                print("Logged out successfully.")
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

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

def get_account_statement(user_id, start_date_str, end_date_str):
    account_id = get_account_id_by_user_id(user_id)
    if not account_id:
        return False, "No account found for this user."

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()

        cur.execute("""
            SELECT type, amount, timestamp, category
            FROM transactions
            WHERE account_id = %s AND timestamp::date BETWEEN %s AND %s
            ORDER BY timestamp ASC;
        """, (account_id, start_date, end_date))
        transactions = cur.fetchall()
        
        statement = f"\n--- Account Statement for {start_date_str} to {end_date_str} ---\n"
        if transactions:
            for t in transactions:
                statement += f"Date: {t[2].strftime('%Y-%m-%d %H:%M:%S')}, Type: {t[0].capitalize()}, Amount: ${t[1]:.2f}, Category: {t[3] if t[3] else 'N/A'}\n"
        else:
            statement += "No transactions found for this period."
        statement += "--------------------------------------------------\n"
        return True, statement
    except ValueError:
        return False, "Invalid date format. Please use YYYY-MM-DD."
    except Exception as e:
        return False, f"Failed to generate statement: {e}"
    finally:
        cur.close()
        conn.close()

def get_loan_repayment_schedule(loan_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT amount, interest_rate, term_months, start_date, remaining_balance FROM loans WHERE id = %s;", (loan_id,))
        loan_data = cur.fetchone()
        if not loan_data:
            return False, "Loan not found."

        total_amount, interest_rate, term_months, start_date, remaining_balance = loan_data
        total_amount = float(total_amount)
        interest_rate = float(interest_rate)
        term_months = int(term_months)
        remaining_balance = float(remaining_balance)

        if interest_rate == 0:
            monthly_payment = total_amount / term_months
        else:
            monthly_interest_rate = interest_rate / 12
            monthly_payment = (total_amount * monthly_interest_rate) / (1 - (1 + monthly_interest_rate)**(-term_months))

        schedule = f"\n--- Loan Repayment Schedule for Loan ID {loan_id} ---\n"
        schedule += f"Loan Amount: ${total_amount:.2f}\n"
        schedule += f"Interest Rate: {interest_rate*100:.2f}%\n"
        schedule += f"Term: {term_months} months\n"
        schedule += f"Monthly Payment: ${monthly_payment:.2f}\n"
        schedule += "--------------------------------------------------\n"
        schedule += "{:<5} {:<15} {:<15} {:<15} {:<15}\n".format("Month", "Payment", "Interest", "Principal", "Balance")
        schedule += "-"*75 + "\n"

        current_balance = total_amount
        for month in range(1, term_months + 1):
            if current_balance <= 0:
                break
            
            interest_payment = current_balance * monthly_interest_rate
            principal_payment = monthly_payment - interest_payment
            
            if principal_payment > current_balance:
                principal_payment = current_balance
                monthly_payment = interest_payment + principal_payment

            current_balance -= principal_payment
            
            schedule += "{:<5} {:<15.2f} {:<15.2f} {:<15.2f} {:<15.2f}\n".format(
                month, monthly_payment, interest_payment, principal_payment, max(0, current_balance)
            )
        schedule += "--------------------------------------------------\n"
        return True, schedule
    except Exception as e:
        return False, f"Failed to generate repayment schedule: {e}"
    finally:
        cur.close()
        conn.close()

def change_password(user_id, old_password, new_password):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT password_hash FROM users WHERE id = %s;", (user_id,))
        result = cur.fetchone()
        if not result:
            return False, "User not found."

        stored_password_hash = result[0]
        if not bcrypt.checkpw(old_password.encode('utf-8'), stored_password_hash.encode('utf-8')):
            return False, "Incorrect old password."

        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("UPDATE users SET password_hash = %s WHERE id = %s;", (new_password_hash, user_id))
        conn.commit()
        return True, "Password changed successfully."
    except Exception as e:
        conn.rollback()
        return False, f"Failed to change password: {e}"
    finally:
        cur.close()
        conn.close()

def search_transactions(user_id, transaction_type=None, min_amount=None, max_amount=None, start_date=None, end_date=None, category=None):
    account_id = get_account_id_by_user_id(user_id)
    if not account_id:
        return False, "No account found for this user."

    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT type, amount, timestamp, category, is_public
        FROM transactions
        WHERE account_id = %s
    """
    params = [account_id]

    if transaction_type:
        query += " AND type ILIKE %s"
        params.append(f"%{transaction_type}%")
    if min_amount is not None:
        query += " AND amount >= %s"
        params.append(min_amount)
    if max_amount is not None:
        query += " AND amount <= %s"
        params.append(max_amount)
    if start_date:
        query += " AND timestamp::date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND timestamp::date <= %s"
        params.append(end_date)
    if category:
        query += " AND category ILIKE %s"
        params.append(f"%{category}%")

    query += " ORDER BY timestamp DESC;"

    try:
        cur.execute(query, tuple(params))
        transactions = cur.fetchall()
        
        if transactions:
            results = "\n--- Search Results ---\n"
            for t in transactions:
                results += f"Date: {t[2].strftime('%Y-%m-%d %H:%M:%S')}, Type: {t[0].capitalize()}, Amount: ${t[1]:.2f}, Category: {t[3] if t[3] else 'N/A'}, Public: {t[4]}\n"
            results += "----------------------"
            return True, results
        else:
            return True, "No transactions found matching your criteria."
    except Exception as e:
        return False, f"Failed to search transactions: {e}"
    finally:
        cur.close()
        conn.close()

def update_transaction_category(transaction_id, user_id, category):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Verify the transaction belongs to the user's account
        account_id = get_account_id_by_user_id(user_id)
        if not account_id:
            return False, "User account not found."

        cur.execute("SELECT id FROM transactions WHERE id = %s AND account_id = %s;", (transaction_id, account_id))
        if not cur.fetchone():
            return False, "Transaction not found or does not belong to your account."

        cur.execute("UPDATE transactions SET category = %s WHERE id = %s;", (category, transaction_id))
        conn.commit()
        return True, f"Transaction {transaction_id} categorized as '{category}'."
    except Exception as e:
        conn.rollback()
        return False, f"Failed to update transaction category: {e}"
    finally:
        cur.close()
        conn.close()

def cli_loan_repayment_schedule(user_id):
    print("\n--- Loan Repayment Schedule ---")
    loans = view_loans(user_id)
    print(loans) # Display user's loans to help them choose
    try:
        loan_id = int(input("Enter Loan ID to view repayment schedule: "))
        success, message = get_loan_repayment_schedule(loan_id)
        print(message)
    except ValueError:
        print("Invalid Loan ID. Please enter a number.")

def cli_search_transactions(user_id):
    while True:
        print("\n--- Search Transactions ---")
        print("1. Search by Type")
        print("2. Search by Amount Range")
        print("3. Search by Date Range")
        print("4. Search by Category")
        print("5. Back to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            transaction_type = input("Enter transaction type (e.g., deposit, withdraw, transfer_in): ")
            success, message = search_transactions(user_id, transaction_type=transaction_type)
            print(message)
        elif choice == '2':
            try:
                min_amount = float(input("Enter minimum amount: "))
                max_amount = float(input("Enter maximum amount: "))
                success, message = search_transactions(user_id, min_amount=min_amount, max_amount=max_amount)
                print(message)
            except ValueError:
                print("Invalid amount. Please enter a number.")
        elif choice == '3':
            start_date_str = input("Enter start date (YYYY-MM-DD): ")
            end_date_str = input("Enter end date (YYYY-MM-DD): ")
            success, message = search_transactions(user_id, start_date=start_date_str, end_date=end_date_str)
            print(message)
        elif choice == '4':
            category = input("Enter category: ")
            success, message = search_transactions(user_id, category=category)
            print(message)
        elif choice == '5':
            break
        else:
            print("Invalid choice. Please try again.")

def cli_change_password(user_id):
    print("\n--- Change Password ---")
    old_password = input("Enter old password: ")
    new_password = input("Enter new password: ")
    confirm_new_password = input("Confirm new password: ")

    if new_password != confirm_new_password:
        print("New passwords do not match.")
        return

    success, message = change_password(user_id, old_password, new_password)
    print(message)

def cli_transaction_categorization(user_id):
    while True:
        print("\n--- Transaction Categorization ---")
        print("1. View My Transactions (to get IDs)")
        print("2. Categorize a Transaction")
        print("3. Back to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            transactions_text = view_transaction_history(user_id)
            print(transactions_text)
        elif choice == '2':
            try:
                transaction_id = int(input("Enter Transaction ID to categorize: "))
                category = input("Enter Category (e.g., Food, Transport, Bills): ")
                success, message = update_transaction_category(transaction_id, user_id, category)
                print(message)
            except ValueError:
                print("Invalid Transaction ID. Please enter a number.")
        elif choice == '3':
            break
        else:
            print("Invalid choice. Please try again.")

def cli_atm_locator():
    print("\n--- ATM Locator ---")
    print("This is a conceptual feature. In a real application, this would integrate with a map service.")
    print("Searching for nearby ATMs...")
    print("ATM 1: 123 Main St, Anytown")
    print("ATM 2: 456 Oak Ave, Anytown")
    print("ATM 3: 789 Pine Ln, Anytown")
    print("-------------------")

def add_recurring_transfer(from_account_id, to_account_number, amount, frequency, next_transfer_date_str, description):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        next_transfer_date = datetime.datetime.strptime(next_transfer_date_str, "%Y-%m-%d").date()
        cur.execute("""
            INSERT INTO recurring_transfers (from_account_id, to_account_number, amount, frequency, next_transfer_date, description, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (from_account_id, to_account_number, amount, frequency, next_transfer_date, description, 'active'))
        conn.commit()
        return True, "Recurring transfer added successfully."
    except ValueError:
        conn.rollback()
        return False, "Invalid date format. Please use YYYY-MM-DD."
    except Exception as e:
        conn.rollback()
        return False, f"Failed to add recurring transfer: {e}"
    finally:
        cur.close()
        conn.close()

def get_user_recurring_transfers(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    account_id = get_account_id_by_user_id(user_id)
    if not account_id:
        return []
    cur.execute("""
        SELECT id, to_account_number, amount, frequency, next_transfer_date, description, status
        FROM recurring_transfers
        WHERE from_account_id = %s
        ORDER BY next_transfer_date ASC;
    """, (account_id,))
    transfers = cur.fetchall()
    cur.close()
    conn.close()
    return transfers

def process_recurring_transfers():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, from_account_id, to_account_number, amount, frequency, next_transfer_date
        FROM recurring_transfers
        WHERE status = 'active' AND next_transfer_date <= CURRENT_DATE;
    """)
    pending_transfers = cur.fetchall()

    for transfer in pending_transfers:
        transfer_id, from_account_id, to_account_number, amount, frequency, next_transfer_date = transfer
        
        from_user_id = get_user_id_by_account_id(from_account_id)
        if not from_user_id:
            print(f"Error processing recurring transfer {transfer_id}: Sender user not found.")
            continue

        success, message = transfer_funds(from_user_id, to_account_number, amount)
        if success:
            # Update next_transfer_date
            new_next_transfer_date = next_transfer_date
            if frequency == 'daily':
                new_next_transfer_date += datetime.timedelta(days=1)
            elif frequency == 'weekly':
                new_next_transfer_date += datetime.timedelta(weeks=1)
            elif frequency == 'monthly':
                new_next_transfer_date = (new_next_transfer_date + datetime.timedelta(days=30)).replace(day=min(new_next_transfer_date.day, (new_next_transfer_date + datetime.timedelta(days=30)).day)) # Simple monthly increment
            
            cur.execute("UPDATE recurring_transfers SET next_transfer_date = %s WHERE id = %s;", (new_next_transfer_date, transfer_id))
            print(f"Processed recurring transfer {transfer_id}: {message}")
        else:
            print(f"Failed to process recurring transfer {transfer_id}: {message}")
            # Optionally, update status to 'failed' or 'pending_retry'
            # cur.execute("UPDATE recurring_transfers SET status = 'failed' WHERE id = %s;", (transfer_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_user_id_by_account_id(account_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM accounts WHERE id = %s;", (account_id,))
    user_id = cur.fetchone()
    cur.close()
    conn.close()
    return user_id[0] if user_id else None

def cli_account_statement(user_id):
    print("\n--- Generate Account Statement ---")
    start_date_str = input("Enter Start Date (YYYY-MM-DD): ")
    end_date_str = input("Enter End Date (YYYY-MM-DD): ")
    
    success, message = get_account_statement(user_id, start_date_str, end_date_str)
    print(message)

def cli_recurring_transfers(user_id):
    while True:
        print("\n--- Recurring Transfers ---")
        print("1. Add New Recurring Transfer")
        print("2. View My Recurring Transfers")
        print("3. Process Pending Recurring Transfers (Admin/System Only)") # For demonstration, user can trigger
        print("4. Back to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("\n--- Add New Recurring Transfer ---")
            to_account_number = input("Recipient Account Number: ")
            try:
                amount = float(input("Amount: "))
                frequency = input("Frequency (daily, weekly, monthly): ").lower()
                next_transfer_date_str = input("Next Transfer Date (YYYY-MM-DD): ")
                
                account_id = get_account_id_by_user_id(user_id)
                if account_id:
                    success, message = add_recurring_transfer(account_id, to_account_number, amount, frequency, next_transfer_date_str, "Recurring Transfer")
                    print(message)
                else:
                    print("Error: Your account not found.")
            except ValueError:
                print("Invalid amount. Please enter a number.")
        elif choice == '2':
            print("\n--- My Recurring Transfers ---")
            transfers = get_user_recurring_transfers(user_id)
            if transfers:
                for t in transfers:
                    print(f"ID: {t[0]}, To: {t[1]}, Amount: ${t[2]:.2f}, Freq: {t[3].capitalize()}, Next Date: {t[4]}, Status: {t[6].capitalize()}")
            else:
                print("No recurring transfers found.")
        elif choice == '3':
            print("\n--- Processing Recurring Transfers ---")
            process_recurring_transfers()
            print("Recurring transfers processed.")
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
            print("10. User Profile") # New Feature 3
            print("11. Account Statement") # New Feature 4
            print("12. Recurring Transfers") # New Feature 5
            print("13. Loan Repayment Schedule") # New Feature 6
            print("14. Transaction Categorization") # New Feature 7
            print("15. Search Transactions") # New Feature 8
            print("16. Change Password") # New Feature 9
            print("17. ATM Locator") # New Feature 10
            print("18. Logout")
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
            elif choice == '10': # New Feature 3
                cli_user_profile_management(logged_in_user_id)
            elif choice == '11': # New Feature 4
                cli_account_statement(logged_in_user_id)
            elif choice == '12': # New Feature 5
                cli_recurring_transfers(logged_in_user_id)
            elif choice == '13': # New Feature 6
                cli_loan_repayment_schedule(logged_in_user_id)
            elif choice == '14': # New Feature 7
                cli_transaction_categorization(logged_in_user_id)
            elif choice == '15': # New Feature 8
                cli_search_transactions(logged_in_user_id)
            elif choice == '16': # New Feature 9
                cli_change_password(logged_in_user_id)
            elif choice == '17': # New Feature 10
                cli_atm_locator()
            elif choice == '18':
                logged_in_user_id = None
                logged_in_username = None
                logged_in_full_name = None
                print("Logged out successfully.")
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
