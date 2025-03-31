from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Act(Base):
    __tablename__ = 'acts'
    act_id = Column(Integer, primary_key=True)
    name = Column(String)

class Building(Base):
    __tablename__ = 'buildings'
    building_id = Column(Integer, primary_key=True)
    name = Column(String)

class Department(Base):
    __tablename__ = 'departments'
    department_id = Column(Integer, primary_key=True)
    name = Column(String)

class BuildingDepartment(Base):
    __tablename__ = 'building_departments'
    builddep_id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey('buildings.building_id'))
    department_id = Column(Integer, ForeignKey('departments.department_id'))
    building = relationship("Building", back_populates="building_departments")
    department = relationship("Department", back_populates="building_departments")

Building.building_departments = relationship("BuildingDepartment", back_populates="building")
Department.building_departments = relationship("BuildingDepartment", back_populates="department")

class Manufacturer(Base):
    __tablename__ = 'manufacturers'
    manufacturer_id = Column(Integer, primary_key=True)
    name = Column(String)

class Model(Base):
    __tablename__ = 'models'
    model_id = Column(Integer, primary_key=True)
    name = Column(String)

class Status(Base):
    __tablename__ = 'statuses'
    status_id = Column(Integer, primary_key=True)
    name = Column(String)

class SuperCart(Base):
    __tablename__ = 'super_carts'
    superCart_id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    img = Column(Text)

class Service(Base):
    __tablename__ = 'services'
    service_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    barCode = Column(String(13), ForeignKey('cartridge_entries.barCode'), nullable=False)
    date_in = Column(DateTime, nullable=True)
    date_out = Column(DateTime, nullable=True)
    date_recieve = Column(DateTime, nullable=True)
    date_get = Column(DateTime, nullable=True)
    weight_in = Column(Float, nullable=True)
    weight_out = Column(Float, nullable=True)
    who_get = Column(String, nullable=True)
    act_id = Column(Integer, ForeignKey('acts.act_id'), nullable=True)
    cartridge_entry = relationship("CartridgeEntry", back_populates="services")

class Cartridge(Base):
    __tablename__ = 'cartridges'
    cartridge_id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey('models.model_id'))
    manufacturer_id = Column(Integer, ForeignKey('manufacturers.manufacturer_id'))
    superCart_id = Column(Integer, ForeignKey('super_carts.superCart_id'))
    model = relationship("Model")
    manufacturer = relationship("Manufacturer")
    super_cart = relationship("SuperCart")

class CartridgeEntry(Base):
    __tablename__ = 'cartridge_entries'
    barCode = Column(String(13), primary_key=True, index=True)
    cartridge_id = Column(Integer, ForeignKey('cartridges.cartridge_id'))
    description = Column(Text)
    date_in = Column(DateTime)
    builddep_id = Column(Integer, ForeignKey('building_departments.builddep_id'))
    status_id = Column(Integer, ForeignKey('statuses.status_id'))
    cartridge = relationship("Cartridge")
    services = relationship("Service", back_populates="cartridge_entry")
    building_department = relationship("BuildingDepartment")
