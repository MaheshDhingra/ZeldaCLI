---

# ZeldaCLI

ZeldaCLI is a full-featured, interactive command-line banking application written in Python. It offers personal banking features such as account management, card operations, loans, bill payments, transfers, and more, all from your terminal.

## Features

- **User Registration and Login**
  - Secure password storage with bcrypt
  - User profile management (name, email, phone, address, DOB)
- **Bank Account Operations**
  - Deposit, withdraw, and check balance
  - Transaction history (private and public feeds)
- **Card Management**
  - Generate debit and credit cards with unique numbers, expiry, and CVV
  - View all cards linked to your account
- **Funds Transfer**
  - Transfer money to other accounts by account number
  - Request money from other users and respond to incoming requests
- **Loans**
  - Apply for new loans (amount, interest, term)
  - View outstanding and paid loans
  - Make loan payments
- **Bills**
  - Add new bills, view, and pay them directly from your account
- **User Search**
  - Find other users by username or full name
- **Security**
  - All passwords are hashed
  - Input validation for emails, phone numbers, amounts, and dates
- **Data Storage**
  - All data stored in a PostgreSQL database (connection via `psycopg2`)
  - Uses `.env` for configuration (database credentials, etc.)

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/MaheshDhingra/ZeldaCLI.git
   cd ZeldaCLI
   ```

2. **Install Dependencies**
   - Python 3.8+
   - [psycopg2](https://pypi.org/project/psycopg2/)
   - [bcrypt](https://pypi.org/project/bcrypt/)
   - [python-dotenv](https://pypi.org/project/python-dotenv/)

   Install with pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up the Database**
   - Create a PostgreSQL database.
   - Copy `.env.example` to `.env` and add your database URL as `DATABASE_URL`.

   Example `.env`:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/yourdbname
   ```

4. **Run the Application**
   ```bash
   python main.py
   ```

## Usage

- On startup, you'll be greeted with a menu to register or log in.
- After logging in, you have access to all banking operations via intuitive menus.
- Input is validated and errors are clearly reported.
- All actions (deposits, withdrawals, transfers, loan ops, etc.) are performed securely and logged in the database.

## Project Structure

- `main.py` — main CLI application and all business logic
- `.env` — environment variables (not committed)
- `requirements.txt` — Python dependencies

## Example Workflow

1. **Register a new user**
2. **Log in**
3. **Deposit funds into your account**
4. **Transfer funds to another user**
5. **Generate a debit or credit card**
6. **View or pay bills**
7. **Apply for and pay off a loan**
8. **Request money from another user**

## Security

- Passwords are stored using bcrypt hashing.
- Email and phone formats are validated.
- Database errors and unexpected issues are gracefully handled.

## Contributing

Pull requests and suggestions are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License

---
