"""
Flip a student's subscription_status directly in the database (Decision
034) -- the stubbed stand-in for a parent actually paying, until real
billing exists. Unlike the other scripts in this directory, this one
takes a CLI argument rather than a hardcoded list: it acts on a
different, arbitrary target every time it's run, not a fixed dataset.

Run with: python -m scripts.set_subscription_status <student-email> <free|premium>
"""

import os
import sys

import psycopg
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[2] not in ("free", "premium"):
        print(__doc__)
        raise SystemExit(1)
    email, status = sys.argv[1], sys.argv[2]

    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update profiles set subscription_status = %s
                where id = (select id from auth.users where email = %s) and role = 'student'
                returning id
                """,
                (status, email),
            )
            row = cur.fetchone()
        if row is None:
            print(f"No student profile found for {email}")
            raise SystemExit(1)
        conn.commit()
    print(f"{email} -> subscription_status = {status}")


if __name__ == "__main__":
    main()
