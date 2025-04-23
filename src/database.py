from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from urllib.parse import quote_plus

IS_DEBUG=True
IS_DEBUG_ECHO=False

# db_user = "admin"
# db_password = "admin_password"
# db_host = "localhost"
# db_name = "my_database"
DB_HOST="localhost"
DB_PORT=5555
DB_USER="postgres_user"
DB_PASSWORD="postgres_password"
DB_BASE="postgres_db"


# encoded_password = quote_plus(db_password)
encoded_password = quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_BASE}"

engine = create_engine(DATABASE_URL, echo=IS_DEBUG_ECHO)

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
