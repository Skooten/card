from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from urllib.parse import quote_plus

db_user = "admin"
db_password = "admin_password"
db_host = "localhost"
db_name = "my_database"

encoded_password = quote_plus(db_password)
DATABASE_URL = f"postgresql+psycopg2://{db_user}:{encoded_password}@{db_host}/{db_name}"

engine = create_engine(DATABASE_URL, echo=False)

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
