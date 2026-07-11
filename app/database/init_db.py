from sqlalchemy import inspect, text

from app.database.database import Base, engine
from app.database.models import Donor, Patient


def add_missing_columns():
    inspector = inspect(engine)

    if "conversations" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("conversations")
    }

    if "updated_at" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE conversations ADD COLUMN updated_at DATETIME")
            )


def init_database():
    Base.metadata.create_all(bind=engine)
    add_missing_columns()
    print("✅ Database and tables created successfully!")

if __name__ == "__main__":
    init_database()
