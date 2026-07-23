"""SQLAlchemy models mirroring post-silicon test-data hierarchy.

SQLite by default, but the schema is Postgres-portable: switch the engine URL
and it works unchanged.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class Lot(Base):
    __tablename__ = "lot"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    product: Mapped[str] = mapped_column(String)
    wafers: Mapped[list[Wafer]] = relationship(back_populates="lot")


class Wafer(Base):
    __tablename__ = "wafer"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_pk: Mapped[int] = mapped_column(ForeignKey("lot.id"), index=True)
    wafer_number: Mapped[int] = mapped_column(Integer)
    lot: Mapped[Lot] = relationship(back_populates="wafers")
    dies: Mapped[list[Die]] = relationship(back_populates="wafer")


class Die(Base):
    __tablename__ = "die"
    id: Mapped[int] = mapped_column(primary_key=True)
    die_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    wafer_pk: Mapped[int] = mapped_column(ForeignKey("wafer.id"), index=True)
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    process_corner: Mapped[str] = mapped_column(String)
    final_bin: Mapped[int] = mapped_column(Integer, index=True)
    wafer: Mapped[Wafer] = relationship(back_populates="dies")
    measurements: Mapped[list[Measurement]] = relationship(back_populates="die")
    schmoo: Mapped[list[SchmooPoint]] = relationship(back_populates="die")
    reg_dumps: Mapped[list[RegDump]] = relationship(back_populates="die")


class Test(Base):
    __tablename__ = "test"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    lower_limit: Mapped[float] = mapped_column(Float)
    upper_limit: Mapped[float] = mapped_column(Float)
    measurements: Mapped[list[Measurement]] = relationship(back_populates="test")


class Measurement(Base):
    __tablename__ = "measurement"
    id: Mapped[int] = mapped_column(primary_key=True)
    die_pk: Mapped[int] = mapped_column(ForeignKey("die.id"), index=True)
    test_pk: Mapped[int] = mapped_column(ForeignKey("test.id"), index=True)
    value: Mapped[float] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(Boolean)
    die: Mapped[Die] = relationship(back_populates="measurements")
    test: Mapped[Test] = relationship(back_populates="measurements")


class SchmooPoint(Base):
    __tablename__ = "schmoo"
    id: Mapped[int] = mapped_column(primary_key=True)
    die_pk: Mapped[int] = mapped_column(ForeignKey("die.id"), index=True)
    param_x: Mapped[str] = mapped_column(String)
    param_y: Mapped[str] = mapped_column(String)
    x_val: Mapped[float] = mapped_column(Float)
    y_val: Mapped[float] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(Boolean)
    die: Mapped[Die] = relationship(back_populates="schmoo")


class RegDump(Base):
    __tablename__ = "reg_dump"
    id: Mapped[int] = mapped_column(primary_key=True)
    die_pk: Mapped[int] = mapped_column(ForeignKey("die.id"), index=True)
    reg_name: Mapped[str] = mapped_column(String)
    raw_value: Mapped[int] = mapped_column(Integer)
    die: Mapped[Die] = relationship(back_populates="reg_dumps")


def get_engine(url: str = "sqlite:///sep.db"):
    return create_engine(url, future=True)


def get_session(engine) -> Session:
    return Session(engine, future=True)
