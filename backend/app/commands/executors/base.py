"""
Base Command Executor

Abstract base class for all command executors (IR, Network, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.orm import Session

from ..models import Command, ExecutionResult


class CommandExecutor(ABC):
    """
    Base class for all command executors

    Each executor type (IR, Samsung, LG, etc.) extends this class
    and implements the execute method for their specific protocol.
    """

    def __init__(self, db: Session):
        self.db = db

    @abstractmethod
    async def execute(self, command: Command) -> ExecutionResult:
        """
        Execute a command

        Args:
            command: Command object from queue

        Returns:
            ExecutionResult with success status and any data/errors
        """
        pass

    @abstractmethod
    def can_execute(self, command: Command) -> bool:
        """
        Check if this executor can handle the given command

        Args:
            command: Command to check

        Returns:
            True if this executor can handle the command
        """
        pass

    def get_name(self) -> str:
        """Get executor name for logging"""
        return self.__class__.__name__
