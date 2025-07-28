import os
import psycopg2
from dotenv import load_dotenv
import bcrypt
import random
import datetime
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Input, Label, Static
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.screen import Screen

load_dotenv()

class BankAccount:
    def __init__(self, user_id, account_number, balance=0.0):
        self.user_id = user_id
        self.account_number = account_number
        self.balance = balance

    def deposit(self, amount):
        if amount > 0:
            self.balance += amount
            return True
        else:
            return False

    def withdraw(self, amount):
        if 0 < amount <= self.balance:
            self.balance -= amount
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
            type VARCHAR(20) NOT NULL, -- e.g., 'deposit', 'withdraw', 'transfer_in', 'transfer_out', 'public_transfer'
            amount DECIMAL(10, 2) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_public BOOLEAN DEFAULT FALSE
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
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        return BankAccount(user_id, account_data[1], float(account_data[2]))
    return None

def record_transaction(account_id, type, amount, is_public=False):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO transactions (account_id, type, amount, is_public) VALUES (%s, %s, %s, %s);", (account_id, type, amount, is_public))
    conn.commit()
    cur.close()
    conn.close()

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
            if transfer_funds(to_user_id, get_user_account(from_user_id).account_number, amount):
                cur.execute("UPDATE money_requests SET status = 'accepted' WHERE id = %s;", (request_id,))
                conn.commit()
                return True, f"Money request {request_id} accepted. ${amount:.2f} transferred."
            else:
                conn.rollback()
                return False, "Failed to transfer funds for acceptance."
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

class MainScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="main-screen-content"):
            yield Label("--- Welcome to Internet Banking ---", classes="title")
            yield Button("Register", id="register_button", variant="primary")
            yield Button("Login", id="login_button", variant="primary")
            yield Button("Exit", id="exit_button", variant="error")
            yield Label("", id="message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "register_button":
            self.app_instance.push_screen(RegisterScreen(self.app_instance))
        elif event.button.id == "login_button":
            self.app_instance.push_screen(LoginScreen(self.app_instance))
        elif event.button.id == "exit_button":
            self.app_instance.exit("Exiting. Goodbye!")

class RegisterScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Register ---", classes="title")
            yield Label("Username:")
            yield Input(placeholder="Enter desired username", id="reg_username")
            yield Label("Password:")
            yield Input(placeholder="Enter desired password", password=True, id="reg_password")
            yield Label("Full Name:")
            yield Input(placeholder="Enter your full name", id="reg_full_name")
            yield Label("Email:")
            yield Input(placeholder="Enter your email", id="reg_email")
            yield Label("Phone Number:")
            yield Input(placeholder="Enter your phone number", id="reg_phone_number")
            yield Label("Address:")
            yield Input(placeholder="Enter your address", id="reg_address")
            yield Label("Date of Birth (YYYY-MM-DD):")
            yield Input(placeholder="YYYY-MM-DD", id="reg_dob")
            yield Button("Register", id="submit_register", variant="primary")
            yield Button("Back", id="back_to_main", variant="default")
            yield Label("", id="reg_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_register":
            username = self.query_one("#reg_username", Input).value
            password = self.query_one("#reg_password", Input).value
            full_name = self.query_one("#reg_full_name", Input).value
            email = self.query_one("#reg_email", Input).value
            phone_number = self.query_one("#reg_phone_number", Input).value
            address = self.query_one("#reg_address", Input).value
            date_of_birth_str = self.query_one("#reg_dob", Input).value

            try:
                date_of_birth = datetime.datetime.strptime(date_of_birth_str, "%Y-%m-%d").date()
                success, message = register_user(username, password, full_name, email, phone_number, address, date_of_birth)
                self.query_one("#reg_message_label", Label).update(message)
                if success:
                    self.app_instance.pop_screen() # Go back to main menu on success
            except ValueError:
                self.query_one("#reg_message_label", Label).update("Invalid date format. Please use YYYY-MM-DD.")
            except Exception as e:
                self.query_one("#reg_message_label", Label).update(f"Registration failed: {e}")
        elif event.button.id == "back_to_main":
            self.app_instance.pop_screen()

class LoginScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Login ---", classes="title")
            yield Label("Username:")
            yield Input(placeholder="Enter username", id="login_username")
            yield Label("Password:")
            yield Input(placeholder="Enter password", password=True, id="login_password")
            yield Button("Login", id="submit_login", variant="primary")
            yield Button("Back", id="back_to_main", variant="default")
            yield Label("", id="login_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_login":
            username = self.query_one("#login_username", Input).value
            password = self.query_one("#login_password", Input).value
            
            user_id, full_name, message = login_user(username, password)
            self.query_one("#login_message_label", Label).update(message)
            if user_id:
                self.app_instance.logged_in_user_id = user_id
                self.app_instance.logged_in_username = username
                self.app_instance.logged_in_full_name = full_name
                self.app_instance.push_screen(MainMenuScreen(self.app_instance))
        elif event.button.id == "back_to_main":
            self.app_instance.pop_screen()

class MainMenuScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label(f"--- Welcome, {self.app_instance.logged_in_username}! ---", classes="title")
            yield Button("Account Operations", id="account_ops_button", variant="primary")
            yield Button("Card Operations", id="card_ops_button", variant="primary")
            yield Button("View Transaction History", id="view_transactions_button", variant="primary")
            yield Button("Transfer Funds", id="transfer_funds_button", variant="primary")
            yield Button("Loans", id="loans_button", variant="primary")
            yield Button("Search Users", id="search_users_button", variant="primary")
            yield Button("Money Requests", id="money_requests_button", variant="primary")
            yield Button("Logout", id="logout_button", variant="error")
            yield Label("", id="main_menu_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "account_ops_button":
            self.app_instance.push_screen(AccountOperationsScreen(self.app_instance))
        elif event.button.id == "card_ops_button":
            self.app_instance.push_screen(CardOperationsScreen(self.app_instance))
        elif event.button.id == "view_transactions_button":
            transactions_text = view_transaction_history(self.app_instance.logged_in_user_id)
            self.app_instance.push_screen(InfoScreen(self.app_instance, "Transaction History", transactions_text))
        elif event.button.id == "transfer_funds_button":
            self.app_instance.push_screen(TransferFundsScreen(self.app_instance))
        elif event.button.id == "loans_button":
            self.app_instance.push_screen(LoansScreen(self.app_instance))
        elif event.button.id == "search_users_button":
            self.app_instance.push_screen(SearchUsersScreen(self.app_instance))
        elif event.button.id == "money_requests_button":
            self.app_instance.push_screen(MoneyRequestsScreen(self.app_instance))
        elif event.button.id == "logout_button":
            self.app_instance.logged_in_user_id = None
            self.app_instance.logged_in_username = None
            self.app_instance.logged_in_full_name = None
            self.app_instance.pop_screen() # Go back to MainScreen

class AccountOperationsScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Account Operations ---", classes="title")
            yield Button("Deposit", id="deposit_button", variant="primary")
            yield Button("Withdraw", id="withdraw_button", variant="primary")
            yield Button("View Balance", id="view_balance_button", variant="primary")
            yield Button("Back", id="back_to_main_menu", variant="default")
            yield Label("", id="account_ops_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        account = get_user_account(self.app_instance.logged_in_user_id)
        if not account:
            self.query_one("#account_ops_message_label", Label).update("Error: Could not retrieve bank account.")
            return

        if event.button.id == "deposit_button":
            self.app_instance.push_screen(DepositScreen(self.app_instance, account))
        elif event.button.id == "withdraw_button":
            self.app_instance.push_screen(WithdrawScreen(self.app_instance, account))
        elif event.button.id == "view_balance_button":
            self.query_one("#account_ops_message_label", Label).update(f"Current Balance: ${account.get_balance():.2f}")
        elif event.button.id == "back_to_main_menu":
            self.app_instance.pop_screen()

class DepositScreen(Screen):
    def __init__(self, app_instance, account, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance
        self.account = account

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Deposit ---", classes="title")
            yield Label("Amount:")
            yield Input(placeholder="Enter amount to deposit", id="deposit_amount", type="number")
            yield Button("Deposit", id="submit_deposit", variant="primary")
            yield Button("Back", id="back_to_account_ops", variant="default")
            yield Label("", id="deposit_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_deposit":
            try:
                amount = float(self.query_one("#deposit_amount", Input).value)
                if self.account.deposit(amount):
                    record_transaction(get_account_id_by_user_id(self.app_instance.logged_in_user_id), 'deposit', amount)
                    self.query_one("#deposit_message_label", Label).update(f"Successfully deposited ${amount:.2f}.")
                else:
                    self.query_one("#deposit_message_label", Label).update("Deposit amount must be positive.")
            except ValueError:
                self.query_one("#deposit_message_label", Label).update("Invalid amount. Please enter a number.")
        elif event.button.id == "back_to_account_ops":
            self.app_instance.pop_screen()

class WithdrawScreen(Screen):
    def __init__(self, app_instance, account, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance
        self.account = account

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Withdraw ---", classes="title")
            yield Label("Amount:")
            yield Input(placeholder="Enter amount to withdraw", id="withdraw_amount", type="number")
            yield Button("Withdraw", id="submit_withdraw", variant="primary")
            yield Button("Back", id="back_to_account_ops", variant="default")
            yield Label("", id="withdraw_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_withdraw":
            try:
                amount = float(self.query_one("#withdraw_amount", Input).value)
                if self.account.withdraw(amount):
                    record_transaction(get_account_id_by_user_id(self.app_instance.logged_in_user_id), 'withdraw', amount)
                    self.query_one("#withdraw_message_label", Label).update(f"Successfully withdrew ${amount:.2f}.")
                else:
                    self.query_one("#withdraw_message_label", Label).update("Invalid withdrawal amount or insufficient balance.")
            except ValueError:
                self.query_one("#withdraw_message_label", Label).update("Invalid amount. Please enter a number.")
        elif event.button.id == "back_to_account_ops":
            self.app_instance.pop_screen()

class CardOperationsScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Card Operations ---", classes="title")
            yield Button("Generate Debit Card", id="gen_debit_card_button", variant="primary")
            yield Button("Generate Credit Card", id="gen_credit_card_button", variant="primary")
            yield Button("View My Cards", id="view_cards_button", variant="primary")
            yield Button("Back", id="back_to_main_menu", variant="default")
            yield Label("", id="card_ops_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "gen_debit_card_button":
            success, message = generate_card(self.app_instance.logged_in_user_id, 'debit')
            self.query_one("#card_ops_message_label", Label).update(message)
        elif event.button.id == "gen_credit_card_button":
            success, message = generate_card(self.app_instance.logged_in_user_id, 'credit')
            self.query_one("#card_ops_message_label", Label).update(message)
        elif event.button.id == "view_cards_button":
            cards_text = display_cards(self.app_instance.logged_in_user_id)
            self.app_instance.push_screen(InfoScreen(self.app_instance, "Your Cards", cards_text))
        elif event.button.id == "back_to_main_menu":
            self.app_instance.pop_screen()

class TransferFundsScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Transfer Funds ---", classes="title")
            yield Label("Recipient's Account Number:")
            yield Input(placeholder="Enter recipient's account number", id="to_account_number")
            yield Label("Amount:")
            yield Input(placeholder="Enter amount to transfer", id="transfer_amount", type="number")
            yield Button("Transfer", id="submit_transfer", variant="primary")
            yield Button("Back", id="back_to_main_menu", variant="default")
            yield Label("", id="transfer_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_transfer":
            to_account_number = self.query_one("#to_account_number", Input).value
            try:
                amount = float(self.query_one("#transfer_amount", Input).value)
                success, message = transfer_funds(self.app_instance.logged_in_user_id, to_account_number, amount)
                self.query_one("#transfer_message_label", Label).update(message)
            except ValueError:
                self.query_one("#transfer_message_label", Label).update("Invalid amount. Please enter a number.")
        elif event.button.id == "back_to_main_menu":
            self.app_instance.pop_screen()

class LoansScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Loan Operations ---", classes="title")
            yield Button("Apply for Loan", id="apply_loan_button", variant="primary")
            yield Button("View My Loans", id="view_loans_button", variant="primary")
            yield Button("Make Loan Payment", id="make_loan_payment_button", variant="primary")
            yield Button("Back", id="back_to_main_menu", variant="default")
            yield Label("", id="loans_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply_loan_button":
            self.app_instance.push_screen(ApplyLoanScreen(self.app_instance))
        elif event.button.id == "view_loans_button":
            loans_text = view_loans(self.app_instance.logged_in_user_id)
            self.app_instance.push_screen(InfoScreen(self.app_instance, "Your Loans", loans_text))
        elif event.button.id == "make_loan_payment_button":
            self.app_instance.push_screen(MakeLoanPaymentScreen(self.app_instance))
        elif event.button.id == "back_to_main_menu":
            self.app_instance.pop_screen()

class ApplyLoanScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Apply for Loan ---", classes="title")
            yield Label("Loan Amount:")
            yield Input(placeholder="Enter loan amount", id="loan_amount", type="number")
            yield Label("Annual Interest Rate (e.g., 0.05 for 5%):")
            yield Input(placeholder="Enter interest rate", id="interest_rate", type="number")
            yield Label("Loan Term in Months:")
            yield Input(placeholder="Enter loan term", id="term_months", type="number")
            yield Button("Apply", id="submit_loan_application", variant="primary")
            yield Button("Back", id="back_to_loans", variant="default")
            yield Label("", id="apply_loan_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_loan_application":
            try:
                amount = float(self.query_one("#loan_amount", Input).value)
                interest_rate = float(self.query_one("#interest_rate", Input).value)
                term_months = int(self.query_one("#term_months", Input).value)
                success, message = apply_for_loan(self.app_instance.logged_in_user_id, amount, interest_rate, term_months)
                self.query_one("#apply_loan_message_label", Label).update(message)
                if success:
                    self.app_instance.pop_screen()
            except ValueError:
                self.query_one("#apply_loan_message_label", Label).update("Invalid input. Please enter numbers for amount, rate, and term.")
        elif event.button.id == "back_to_loans":
            self.app_instance.pop_screen()

class MakeLoanPaymentScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Make Loan Payment ---", classes="title")
            yield Label("Loan ID:")
            yield Input(placeholder="Enter Loan ID", id="loan_id", type="number")
            yield Label("Payment Amount:")
            yield Input(placeholder="Enter payment amount", id="payment_amount", type="number")
            yield Button("Make Payment", id="submit_loan_payment", variant="primary")
            yield Button("Back", id="back_to_loans", variant="default")
            yield Label("", id="make_payment_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_loan_payment":
            try:
                loan_id = int(self.query_one("#loan_id", Input).value)
                amount = float(self.query_one("#payment_amount", Input).value)
                success, message = make_loan_payment(self.app_instance.logged_in_user_id, loan_id, amount)
                self.query_one("#make_payment_message_label", Label).update(message)
                if success:
                    self.app_instance.pop_screen()
            except ValueError:
                self.query_one("#make_payment_message_label", Label).update("Invalid input. Please enter numbers for loan ID and amount.")
        elif event.button.id == "back_to_loans":
            self.app_instance.pop_screen()

class SearchUsersScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Search Users ---", classes="title")
            yield Label("Search Query (username or full name):")
            yield Input(placeholder="Enter search query", id="search_query")
            yield Button("Search", id="submit_search_users", variant="primary")
            yield Button("Back", id="back_to_main_menu", variant="default")
            yield Label("", id="search_users_message_label", classes="message")
            yield Static("", id="search_results_display", classes="results")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_search_users":
            query = self.query_one("#search_query", Input).value
            results = search_users(query)
            self.query_one("#search_results_display", Static).update(results)
        elif event.button.id == "back_to_main_menu":
            self.app_instance.pop_screen()

class MoneyRequestsScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Money Request Operations ---", classes="title")
            yield Button("Send Money Request", id="send_money_request_button", variant="primary")
            yield Button("View Pending Requests", id="view_pending_requests_button", variant="primary")
            yield Button("Respond to Request", id="respond_to_request_button", variant="primary")
            yield Button("Back", id="back_to_main_menu", variant="default")
            yield Label("", id="money_requests_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send_money_request_button":
            self.app_instance.push_screen(SendMoneyRequestScreen(self.app_instance))
        elif event.button.id == "view_pending_requests_button":
            requests_text = view_money_requests(self.app_instance.logged_in_user_id)
            self.app_instance.push_screen(InfoScreen(self.app_instance, "Pending Money Requests", requests_text))
        elif event.button.id == "respond_to_request_button":
            self.app_instance.push_screen(RespondToMoneyRequestScreen(self.app_instance))
        elif event.button.id == "back_to_main_menu":
            self.app_instance.pop_screen()

class SendMoneyRequestScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Send Money Request ---", classes="title")
            yield Label("Recipient Username:")
            yield Input(placeholder="Enter recipient's username", id="to_username")
            yield Label("Amount:")
            yield Input(placeholder="Enter amount to request", id="request_amount", type="number")
            yield Button("Send Request", id="submit_money_request", variant="primary")
            yield Button("Back", id="back_to_money_requests", variant="default")
            yield Label("", id="send_request_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_money_request":
            to_username = self.query_one("#to_username", Input).value
            try:
                amount = float(self.query_one("#request_amount", Input).value)
                success, message = request_money(self.app_instance.logged_in_user_id, to_username, amount)
                self.query_one("#send_request_message_label", Label).update(message)
                if success:
                    self.app_instance.pop_screen()
            except ValueError:
                self.query_one("#send_request_message_label", Label).update("Invalid amount. Please enter a number.")
        elif event.button.id == "back_to_money_requests":
            self.app_instance.pop_screen()

class RespondToMoneyRequestScreen(Screen):
    def __init__(self, app_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("--- Respond to Money Request ---", classes="title")
            yield Label("Request ID:")
            yield Input(placeholder="Enter Request ID", id="request_id", type="number")
            yield Label("Action (accept/decline):")
            yield Input(placeholder="Type 'accept' or 'decline'", id="request_action")
            yield Button("Submit Response", id="submit_request_response", variant="primary")
            yield Button("Back", id="back_to_money_requests", variant="default")
            yield Label("", id="respond_request_message_label", classes="message")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit_request_response":
            try:
                request_id = int(self.query_one("#request_id", Input).value)
                action = self.query_one("#request_action", Input).value.lower()
                success, message = respond_to_money_request(request_id, self.app_instance.logged_in_user_id, action)
                self.query_one("#respond_request_message_label", Label).update(message)
                if success:
                    self.app_instance.pop_screen()
            except ValueError:
                self.query_one("#respond_request_message_label", Label).update("Invalid Request ID. Please enter a number.")
        elif event.button.id == "back_to_money_requests":
            self.app_instance.pop_screen()

class InfoScreen(Screen):
    def __init__(self, app_instance, title, content, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_instance = app_instance
        self.title = title
        self.content = content

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label(f"--- {self.title} ---", classes="title")
            yield Static(self.content, classes="info_content")
            yield Button("Back", id="back_from_info", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_from_info":
            self.app_instance.pop_screen()

class ZeldaBankApp(App):
    CSS_PATH = "styles.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logged_in_user_id = None
        self.logged_in_username = None
        self.logged_in_full_name = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield MainScreen(self)

    def on_mount(self) -> None:
        create_tables() # Ensure tables are created on app start

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_quit(self) -> None:
        self.exit("Exiting. Goodbye!")

if __name__ == "__main__":
    app = ZeldaBankApp()
    app.run()
