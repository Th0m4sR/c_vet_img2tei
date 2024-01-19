from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, DateTime, String, Float, create_engine


DeclarativeBase = declarative_base()
with open("db_url.txt", "r") as file:
    db_url = file.read()
engine = create_engine(db_url)


class Regulation(DeclarativeBase):
    __tablename__ = "regulation"
    # Delivered from API
    id = Column(String, primary_key=True)
    kind = Column(String)
    year = Column(Integer)
    number = Column(Integer)
    date = Column(DateTime)
    url = Column(String)
    api_url = Column(String)
    document_url = Column(String)
    order = Column(Integer)
    title = Column(String)
    law_date = Column(DateTime)
    page = Column(Integer)
    pdf_page = Column(Integer)
    num_pages = Column(Integer)
    score = Column(Float)
    # Required by me
    local_filename = Column(String)
    # regulation_type = Column(String)

    def __hash__(self):
        return hash(str(self.id) + str(self.year) + str(self.title))
