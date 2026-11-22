"""Независимая от Tkinter игровая механика и хранение рекордов."""
from __future__ import annotations
import json
import random
from datetime import datetime
from pathlib import Path
from .models import Difficulty, Direction, GameMode, GameSettings, GameState, Position, Snake
from .entities import (DoublePoints, Entity, Food, GhostMode, GoldenFood,
                       Obstacle, Portal, PowerUp, SlowMotion)
from .world import CollisionSystem, LevelGenerator


class ScoreManager:
    """Рекорды сохраняются отдельно от игрового движка (JSON)."""

    def __init__(self, filepath: Path | None = None):
        self._path = filepath or Path.home() / ".snake_max" / "records.json"

    def load(self) -> list[dict]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            return [x for x in data if isinstance(x, dict) and isinstance(x.get("score"), int)]
        except (OSError, ValueError, TypeError):
            return []

    def save(self, name: str, score: int, mode: GameMode, difficulty: Difficulty) -> None:
        record = {
            "name": (name.strip()[:18] or "Игрок"), "score": score,
            "mode": mode.value, "difficulty": difficulty.value,
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
        records = self.load()
        records.append(record)
        records.sort(key=lambda r: r["score"], reverse=True)
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(records[:20], ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass  # Игра остаётся доступной, даже если запись рекордов запрещена.


class GameEngine:
    """Управляет состоянием игры; UI только вызывает методы и читает свойства."""

    def __init__(self, settings: GameSettings | None = None, seed: int | None = None):
        self.settings = settings or GameSettings()
        self._rng = random.Random(seed)
        self._generator = LevelGenerator(self._rng)
        self._collisions = CollisionSystem()
        self.reset()

    def reset(self) -> None:
        s = self.settings
        self.snake = Snake(Position(s.width // 2, s.height // 2))
        self.obstacles: list[Obstacle] = self._generator.initial_obstacles(s, self.snake)
        self.portals: list[Portal] = []
        self.powerups: list[PowerUp] = []
        self.golden_food: GoldenFood | None = None
        self._golden_expires_at = 0
        self.foods_eaten = 0
        self.score = 0
        self.ticks = 0
        self.effects: dict[str, int] = {}
        self.state = GameState.READY
        self.last_event = "Нажмите «Играть» или Enter"
        self.food: Food | None = None
        self._spawn_food()
        if self.settings.mode != GameMode.ZEN:
            self._spawn_portals()

    def start(self) -> None:
        if self.state == GameState.READY:
            self.state = GameState.RUNNING
            self.last_event = "Удачной игры!"

    def toggle_pause(self) -> None:
        if self.state == GameState.RUNNING:
            self.state = GameState.PAUSED
            self.last_event = "Пауза"
        elif self.state == GameState.PAUSED:
            self.state = GameState.RUNNING
            self.last_event = "Продолжаем!"

    def set_direction(self, direction: Direction) -> bool:
        if self.state != GameState.RUNNING:
            return False
        return self.snake.turn(direction)

    def effect_active(self, name: str) -> bool:
        return self.effects.get(name, 0) > 0

    def apply_effect(self, name: str, duration: int) -> None:
        self.effects[name] = max(duration, self.effects.get(name, 0))

    def add_score(self, points: int) -> None:
        self.score += points * (2 if self.effect_active("double") else 1)

    @property
    def tick_interval_ms(self) -> int:
        speed_up = min(48, (self.foods_eaten // 4) * 6)
        value = max(65, self.settings.base_interval_ms - speed_up)
        return int(value * 1.6) if self.effect_active("slow") else value

    @property
    def entities(self) -> tuple[Entity, ...]:
        result: list[Entity] = [*self.obstacles, *self.portals, *self.powerups]
        if self.food:
            result.append(self.food)
        if self.golden_food:
            result.append(self.golden_food)
        return tuple(result)

    def _occupied(self) -> set[Position]:
        positions = set(self.snake.segments)
        positions.update(entity.position for entity in self.entities)
        return positions

    def _free_cell(self) -> Position | None:
        return self._generator.free_cell(self.settings, self._occupied())

    def _spawn_food(self) -> None:
        pos = self._free_cell()
        if pos is None:
            self._end_game("Победа: всё поле заполнено!")
        else:
            self.food = Food(pos)

    def _spawn_portals(self) -> None:
        # Два связанных портала находятся на свободных клетках.
        cells = []
        for _ in range(2):
            pos = self._free_cell()
            if pos is None:
                return
            self.portals.append(Portal(pos))
            cells.append(pos)

    def _spawn_golden(self) -> None:
        if self.golden_food is not None:
            return
        pos = self._free_cell()
        if pos is not None:
            self.golden_food = GoldenFood(pos)
            self._golden_expires_at = self.ticks + 36

    def _spawn_powerup(self) -> None:
        if self.powerups or self._rng.random() > 0.65:
            return
        pos = self._free_cell()
        if pos is not None:
            cls = self._rng.choice([DoublePoints, GhostMode, SlowMotion])
            self.powerups.append(cls(pos, expires_at=self.ticks + 50))

    def _grow_level(self) -> None:
        if self.settings.mode != GameMode.SURVIVAL or self.foods_eaten % 6 != 0:
            return
        for _ in range(2):
            pos = self._free_cell()
            if pos:
                self.obstacles.append(Obstacle(pos))
        self.last_event += " | +2 препятствия"

    def _end_game(self, reason: str) -> None:
        self.state = GameState.GAME_OVER
        self.last_event = reason

    def step(self) -> None:
        if self.state != GameState.RUNNING:
            return
        self.ticks += 1
        next_head = self._collisions.normalize(self.snake.next_head, self.settings)
        if next_head is None:
            self._end_game("Игра окончена: стена!")
            return

        for i, portal in enumerate(self.portals):
            if next_head == portal.position:
                next_head = self.portals[1 - i].position
                self.last_event = "Прыжок через портал!"
                break

        growing = ((self.food is not None and next_head == self.food.position) or
                   (self.golden_food is not None and next_head == self.golden_food.position))
        if not self.effect_active("ghost"):
            if self._collisions.obstacle_hit(next_head, self.obstacles):
                self._end_game("Игра окончена: препятствие!")
                return
            if self._collisions.body_hit(next_head, self.snake, growing):
                self._end_game("Игра окончена: столкновение с собой!")
                return

        self.snake.move(next_head, grow=growing)
        if self.food is not None and next_head == self.food.position:
            self.last_event = self.food.on_collect(self)
            # Занятая клетка старой еды уже находится в теле змеи.
            self.food = None
            self._spawn_food()
            if self.state == GameState.GAME_OVER:
                return
            if self.foods_eaten % 5 == 0:
                self._spawn_golden()
            self._grow_level()
        elif self.golden_food is not None and next_head == self.golden_food.position:
            self.last_event = self.golden_food.on_collect(self)
            self.golden_food = None

        for item in list(self.powerups):
            if item.position == next_head:
                self.last_event = item.on_collect(self)
                self.powerups.remove(item)

        if self.golden_food is not None and self.ticks >= self._golden_expires_at:
            self.golden_food = None
        self.powerups = [p for p in self.powerups if p.expires_at > self.ticks]
        if self.ticks % 28 == 0:
            self._spawn_powerup()
        for key in list(self.effects):
            self.effects[key] -= 1
            if self.effects[key] <= 0:
                del self.effects[key]
