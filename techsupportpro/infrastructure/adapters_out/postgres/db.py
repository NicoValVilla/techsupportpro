"""Configuración de base de datos SQLAlchemy."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def crear_engine():
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/techsupportpro"
    )
    return create_engine(url, echo=False, pool_pre_ping=True)

def crear_sesion():
    engine = crear_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
