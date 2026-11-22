"""Игровые сущности с наследованием и полиморфным сбором предметов."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING
from .models import Position

if TYPE_CHECKING:
    from .engine import GameEngine


@dataclass
class Entity(ABC):
    position: Position

    @property
    @abstractmethod
    def color(self) -> str:
        """Цвет объекта на игровом поле."""

    @property
    @abstractmethod
    def glyph(self) -> str:
        """Символ в клетке."""

    @abstractmethod
    def on_collect(self, engine: GameEngine) -> str:
        """Полиморфная реакция на взаимодействие со змейкой."""


@dataclass
class Food(Entity):
    @property
    def color(self) -> str:
        return "#2CE7AE"

    @property
    def glyph(self) -> str:
        return "●"

    def on_collect(self, engine: GameEngine) -> str:
        engine.add_score(10)
        engine.foods_eaten += 1
        return "Вкусно! +10"


@dataclass
class GoldenFood(Food):
    @property
    def color(self) -> str:
        return "#FFC857"

    @property
    def glyph(self) -> str:
        return "★"

    def on_collect(self, engine: GameEngine) -> str:
        engine.add_score(50)
        return "Золотая еда! +50"


@dataclass
class PowerUp(Entity, ABC):
    expires_at: int = 0

    def on_collect(self, engine: GameEngine) -> str:
        self.activate(engine)
        return self.message

    @property
    @abstractmethod
    def message(self) -> str:
        pass

    @abstractmethod
    def activate(self, engine: GameEngine) -> None:
        pass


@dataclass
class DoublePoints(PowerUp):
    @property
    def color(self) -> str:
        return "#C27CFF"

    @property
    def glyph(self) -> str:
        return "2×"

    @property
    def message(self) -> str:
        return "Удвоение очков: 18 ходов"

    def activate(self, engine: GameEngine) -> None:
        engine.apply_effect("double", 18)


@dataclass
class GhostMode(PowerUp):
    @property
    def color(self) -> str:
        return "#56B8FF"

    @property
    def glyph(self) -> str:
        return "◇"

    @property
    def message(self) -> str:
        return "Призрак: проходи сквозь препятствия 14 ходов"

    def activate(self, engine: GameEngine) -> None:
        engine.apply_effect("ghost", 14)


@dataclass
class SlowMotion(PowerUp):
    @property
    def color(self) -> str:
        return "#FF85BA"

    @property
    def glyph(self) -> str:
        return "◷"

    @property
    def message(self) -> str:
        return "Замедление: 15 ходов"

    def activate(self, engine: GameEngine) -> None:
        engine.apply_effect("slow", 15)


@dataclass
class Obstacle(Entity):
    @property
    def color(self) -> str:
        return "#E65E77"

    @property
    def glyph(self) -> str:
        return "×"

    def on_collect(self, engine: GameEngine) -> str:
        return "Столкновение с препятствием"


@dataclass
class Portal(Entity):
    @property
    def color(self) -> str:
        return "#4AD8DE"

    @property
    def glyph(self) -> str:
        return "↻"

    def on_collect(self, engine: GameEngine) -> str:
        return "Телепортация"
