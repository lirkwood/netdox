"""
This module is a stub. It will contain classes used to gather and manipulate user data.
"""
from __future__ import annotations
from abc import ABC, abstractmethod

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netdox.objs.containers import Network

class User:
    name: str
    """First and last name of the user"""
    email: str
    """Email address for the user"""
    accounts: dict
    """Dictionary of user accounts"""

    def __init__(self, name: str, email: str, accounts: dict = {}) -> None:
        self.name = name
        self.email = email
        self.accounts = defaultdict(lambda: defaultdict(dict)) | accounts

    def registerAccount(self, account: Account) -> None:
        self.accounts[account.environment][account.instance] = account


class Account:
    user: User
    """User owning this account"""
    instance: str
    """The FQDN of the instance to use this account with"""
    network: Network
    """Network the instance belongs to"""
    environment: str
    """The environment this Account belongs to (e.g. PageSeeder). Should be set at the class level."""

    def __init__(self, user: str, instance: str, network: Network) -> None:
        self.user = user
        self.instance = instance
        self.network = network
        self.environment = type(self).environment

class PSAccount(Account):
    projects: defaultdict
    """A dict of the projects / groups this account has access to."""
    environment: str = 'PageSeeder'

    def __init__(self, user: str, instance: str, network: Network, projects: dict = None) -> None:
        super().__init__(user, instance, network)
        self.projects = projects or {}