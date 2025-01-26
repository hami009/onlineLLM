from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
import os
from dotenv import load_dotenv
from models import Base

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.engine = self.create_engine()
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        
    def create_engine(self):
        """Create SQLAlchemy engine with proper SSL configuration"""
        return create_engine(
            f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('AWS_RDS_END_POINT')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
            connect_args={
                'sslmode': 'verify-full',
                'sslrootcert': 'rds-ca-2019-root.pem',
                'options': f'-c ssl_min_protocol_version=TLSv1.2'
            },
            pool_size=10,
            max_overflow=20
        )

    @contextmanager
    def session_scope(self):
        session = self.Session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def initialize_database(self):
        try:
            Base.metadata.create_all(self.engine)
            print("Database tables created successfully")
        except SQLAlchemyError as e:
            print(f"Database initialization failed: {str(e)}")