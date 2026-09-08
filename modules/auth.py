"""
modules/auth.py — SCMS Authentication Module
=============================================
Handles all password and login operations for SCMS.

This module is a DOMAIN module — it contains only data/logic functions.
It does NOT contain:
  - input()
  - print() (except for internal errors that need visibility)
  - menus
  - role routing

It provides four public functions:
  - hash_password(password)         → (hash_hex, salt_hex)
  - verify_password(password, stored_hash, stored_salt) → bool
  - create_user(name, role, username, password) → (True, None) | (False, reason)
  - authenticate_user(username, password)       → sqlite3.Row | None

Password hashing uses PBKDF2-HMAC-SHA256 (Python standard library).
Passwords are NEVER stored in plain text.

Standard-library modules used:
  - hashlib   — PBKDF2-HMAC-SHA256 hashing
  - secrets   — cryptographically secure random salt generation
  - hmac      — timing-safe string comparison
  - sqlite3   — via database.get_connection()
"""

import hashlib
import hmac
import secrets
import sqlite3

from database import get_connection

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Number of PBKDF2 iterations.
# 260,000 is the OWASP-recommended minimum for PBKDF2-SHA256 as of 2023.
# It makes each hash take ~0.1 seconds on a normal CPU — unnoticeable for
# a single login, but 260,000x harder for an attacker brute-forcing a
# stolen database.
_PBKDF2_ITERATIONS = 260_000

# Allowed user roles — must match the CHECK constraint in the users table.
_VALID_ROLES = {"admin", "teacher", "student"}


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> tuple[str, str]:
    """
    Hash a plain-text password using PBKDF2-HMAC-SHA256 with a random salt.

    Steps:
      1. Generate a random 32-byte salt using secrets.token_hex().
         (token_hex(32) gives 64 hex characters — plenty of entropy.)
      2. Encode both the password and salt to bytes (UTF-8).
      3. Run PBKDF2-HMAC-SHA256 with _PBKDF2_ITERATIONS rounds.
      4. Convert the resulting bytes to a hex string for safe SQLite storage.

    Returns:
        (password_hash, password_salt)
        Both are hex strings — safe to store directly in TEXT columns.

    The original password is NOT returned and is not stored anywhere.

    Example:
        ph, ps = hash_password("mypassword")
        # ph → "3f8a9c..."   (64 hex chars)
        # ps → "a1b2c3..."   (64 hex chars)
    """
    # Generate a unique random salt for this password.
    # Using secrets (not random) because secrets is cryptographically secure.
    salt_hex = secrets.token_hex(32)

    # Hash the password: encode both to bytes first, then run PBKDF2.
    raw_hash = hashlib.pbkdf2_hmac(
        "sha256",                        # hash algorithm
        password.encode("utf-8"),        # password as bytes
        salt_hex.encode("utf-8"),        # salt as bytes
        _PBKDF2_ITERATIONS               # iteration count
    )

    # Convert the bytes result to a hex string for database storage.
    hash_hex = raw_hash.hex()

    return hash_hex, salt_hex


def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """
    Verify a plain-text password against a stored hash and salt.

    Re-hashes the given password using the same stored salt and iteration
    count, then compares the result to the stored hash.

    Why hmac.compare_digest instead of ==?
    ----------------------------------------
    Python's == operator short-circuits: it stops comparing the moment it
    finds a character that differs. This leaks timing information that an
    attacker could exploit. hmac.compare_digest always takes the same amount
    of time regardless of where (or whether) the strings differ — this
    prevents timing attacks.

    Returns:
        True  if the password matches the stored hash.
        False if the password is incorrect.
    """
    # Recompute the hash using the stored salt (same parameters as hashing).
    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        stored_salt.encode("utf-8"),
        _PBKDF2_ITERATIONS
    ).hex()

    # Timing-safe comparison.
    return hmac.compare_digest(candidate_hash, stored_hash)


# ---------------------------------------------------------------------------
# User creation
# ---------------------------------------------------------------------------

def create_user(name: str, role: str, username: str, password: str) -> tuple[bool, str | None]:
    """
    Create a new user in the `users` table.

    Validates inputs, hashes the password, and inserts the user.
    Does NOT commit until the insert succeeds — the transaction is atomic.

    Parameters:
        name     — Full display name (e.g. "Priya Sharma")
        role     — Must be one of: "admin", "teacher", "student"
        username — Unique login identifier (e.g. "priya_s")
        password — Plain-text password (hashed before storage)

    Returns:
        (True,  None)           on success
        (False, error_message)  on failure

    The caller decides what to do with the result (print a message, retry,
    etc.). This function never calls input() or print().

    Why return a tuple instead of raising an exception?
    ----------------------------------------------------
    For a college project, returning (success, reason) keeps calling code
    simple and readable — the caller just checks the boolean.
    Exceptions are still caught for unexpected database errors.
    """
    # ── Input validation ─────────────────────────────────────────────────────

    # Strip whitespace to avoid accidental spaces in stored values.
    name     = name.strip()
    role     = role.strip().lower()
    username = username.strip()
    # Do NOT strip password — spaces in passwords are intentional.

    if not name:
        return False, "Name cannot be empty."

    if not username:
        return False, "Username cannot be empty."

    if not password:
        return False, "Password cannot be empty."

    if role not in _VALID_ROLES:
        return False, f"Invalid role '{role}'. Must be one of: {', '.join(sorted(_VALID_ROLES))}."

    # ── Hash the password ────────────────────────────────────────────────────

    password_hash, password_salt = hash_password(password)

    # ── Insert into database ─────────────────────────────────────────────────

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO users (name, role, username, password_hash, password_salt)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, role, username, password_hash, password_salt)
            # ^ Parameterized query with ? placeholders.
            #   SQLite substitutes the values safely — no SQL injection possible.
        )
        conn.commit()
        return True, None

    except sqlite3.IntegrityError:
        # The UNIQUE constraint on username was violated.
        # We do not distinguish between "username taken" and other integrity
        # errors here — the only UNIQUE field on this insert is username.
        return False, f"Username '{username}' is already taken."

    except sqlite3.Error as e:
        # Unexpected database error — surface a clean message.
        return False, f"Database error: {e}"

    finally:
        # Always close the connection, even if an exception was raised.
        conn.close()


# ---------------------------------------------------------------------------
# Login / authentication
# ---------------------------------------------------------------------------

def authenticate_user(username: str, password: str):
    """
    Verify login credentials and return the user record on success.

    Looks up the user by username, then calls verify_password() to check
    the provided password against the stored hash.

    Security note — generic failure message:
    -----------------------------------------
    We return None for BOTH "username not found" and "wrong password".
    This prevents username enumeration: an attacker should not be able to
    tell whether a username exists just by trying to log in with it.
    The caller should always display a single generic message such as:
        "Invalid username or password."

    Parameters:
        username — The login identifier to look up.
        password — The plain-text password entered by the user.

    Returns:
        sqlite3.Row  — the full user row (id, name, role, username, ...)
                       on successful login.
        None         — if the username does not exist or the password
                       is wrong.

    The returned sqlite3.Row supports column-name access:
        user = authenticate_user("admin1", "pass")
        if user:
            print(user["role"])   # → "admin"
            print(user["name"])   # → "Admin User"
    """
    if not username or not password:
        # Fail fast for empty inputs without hitting the database.
        return None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()  # Returns sqlite3.Row or None.

        if user is None:
            # Username not found — return None (same response as wrong password).
            return None

        # Verify the entered password against the stored hash + salt.
        if verify_password(password, user["password_hash"], user["password_salt"]):
            return user   # Login successful — return the full user row.
        else:
            return None   # Wrong password.

    except sqlite3.Error:
        # On any unexpected database error, treat it as a failed login.
        return None

    finally:
        conn.close()
