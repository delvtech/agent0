"""Database Schemas for Basic Blockchain Datatypes.  These include things like Transactions, Accounts Etc."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

# Schema file doesn't need any methods in these dataclasses
# pylint: disable=too-few-public-methods

# solidity returns things in camelCase.  Keeping the formatting to indicate the source.
# pylint: disable=invalid-name

# Ideally, we'd use `Mapped[str | None]`, but this breaks using Python 3.9:
# https://github.com/sqlalchemy/sqlalchemy/issues/9110
# Currently using `Mapped[Union[str, None]]` for backwards compatibility


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class to subclass from to define the schema"""


class AddrToUsername(Base):
    """Maps an address to a username. This mapping should be many addresses to one username."""

    __tablename__ = "addr_to_username"

    address: Mapped[str] = mapped_column(String, primary_key=True)
    """The wallet address"""
    username: Mapped[str] = mapped_column(String, index=True)
    """The logical username"""


class UsernameToUser(Base):
    """Maps a per wallet username to a user. This mapping should be many usernames to one user.
    The primary usecase is to map multiple usernames to one user,
    e.g., Sheng Lundquist (click) and slundquist (bots) -> Sheng Lundquist
    """

    __tablename__ = "username_to_user"

    username: Mapped[str] = mapped_column(String, primary_key=True)
    """The logical username."""
    user: Mapped[str] = mapped_column(String, index=True)
    """The user."""
