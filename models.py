from sqlalchemy import Column, Integer, String, Float
from database import Base


class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    hs_code = Column(String)
    goods_description = Column(String)

    invoice_value = Column(Float)
    currency = Column(String)

    country_of_origin = Column(String)

    importer_name = Column(String)
    importer_code = Column(String)

    exporter_name = Column(String)

    port_of_entry = Column(String)
    customs_office_code = Column(String)

    declaration_number = Column(String)

    duty_rate = Column(String)
    consumption_tax = Column(String)
    total_duties = Column(String)

    review_status = Column(String)