from sqlalchemy import Column, Integer, String, Float
from database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    hs_code = Column(String, nullable=True)
    invoice_value = Column(Float, nullable=True)
    currency = Column(String, nullable=True)

    exporter_name = Column(String, nullable=True)
    consignee_name = Column(String, nullable=True)
    consignee_address = Column(String, nullable=True)

    order_date = Column(String, nullable=True)
    order_number = Column(String, nullable=True)

    review_status = Column(String, nullable=True)