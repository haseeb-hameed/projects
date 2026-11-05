import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, Float, String, Text, ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import declarative_base, sessionmaker
BASE=Path(__file__).resolve().parent
URL=os.getenv('DATABASE_URL', 'sqlite:///'+str(BASE/'roadsense_v2.sqlite'))
engine=create_engine(URL,connect_args={'check_same_thread':False} if URL.startswith('sqlite:') else {},pool_pre_ping=True)
if URL.startswith('sqlite:'):
 @event.listens_for(engine,'connect')
 def setup_sqlite(conn,record):conn.execute('PRAGMA foreign_keys=ON')
Session=sessionmaker(bind=engine,expire_on_commit=False)
Base=declarative_base()
def now():return datetime.now(timezone.utc).timestamp()
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);name=Column(String(60),nullable=False);email=Column(String(160),unique=True,nullable=False);password=Column(Text,nullable=False);created=Column(Float,default=now)
class Hazard(Base):
 __tablename__='hazards'
 id=Column(Integer,primary_key=True);user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
 type=Column(String(40),nullable=False);location=Column(String(160),nullable=False);severity=Column(String(10),nullable=False)
 lat=Column(Float,nullable=False);lon=Column(Float,nullable=False);source=Column(String(20),default='manual');confidence=Column(Float,nullable=True)
 status=Column(String(20),default='reported');created=Column(Float,default=now);updated=Column(Float,default=now);expires=Column(Float,nullable=False)
class Vote(Base):
 __tablename__='votes'
 id=Column(Integer,primary_key=True);user_id=Column(Integer,ForeignKey('users.id'),nullable=False);hazard_id=Column(Integer,ForeignKey('hazards.id'),nullable=False);action=Column(String(10),nullable=False)
 __table_args__=(UniqueConstraint('user_id','hazard_id',name='one_vote_per_user_hazard'),)
class Zone(Base):
 __tablename__='zones'
 id=Column(Integer,primary_key=True);hazard_id=Column(Integer,ForeignKey('hazards.id'),unique=True,nullable=False);radius=Column(Float,default=100)
class MediaAttachment(Base):
 __tablename__='media_attachments'
 id=Column(String(32),primary_key=True);user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
 hazard_id=Column(Integer,ForeignKey('hazards.id'),nullable=True,index=True)
 kind=Column(String(8),nullable=False);mime=Column(String(40),nullable=False);size=Column(Integer,nullable=False)
 duration=Column(Float,nullable=True);created=Column(Float,default=now);analysis=Column(Text,nullable=True)
Base.metadata.create_all(engine)
# PostGIS is optional. Scalar coordinates remain available for a portable local demo.
if URL.startswith('postgresql'):
 from sqlalchemy import text
 with engine.begin() as conn:
  conn.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
  conn.execute(text('CREATE INDEX IF NOT EXISTS hazards_geo_idx ON hazards USING GIST ((ST_SetSRID(ST_MakePoint(lon,lat),4326)::geography))'))
