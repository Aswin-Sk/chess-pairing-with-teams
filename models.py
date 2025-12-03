from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import os

DB_PATH = os.path.join(os.getcwd(), "swiss.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
Base = declarative_base()

def get_session():
    return Session()

class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    team = Column(String)
    rating = Column(Integer)

class Round(Base):
    __tablename__ = 'rounds'
    id = Column(Integer, primary_key=True)
    number = Column(Integer)

class Match(Base):
    __tablename__ = 'matches'
    id = Column(Integer, primary_key=True)
    round_id = Column(Integer, ForeignKey('rounds.id'))
    p1_id = Column(Integer, ForeignKey('players.id'))
    p2_id = Column(Integer, ForeignKey('players.id'), nullable=True)
    p1_score = Column(Float)
    p2_score = Column(Float)
    finished = Column(Boolean, default=False)

    p1 = relationship("Player", foreign_keys=[p1_id])
    p2 = relationship("Player", foreign_keys=[p2_id])

Base.metadata.create_all(engine)
