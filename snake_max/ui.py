"""Графический интерфейс Tkinter: отрисовка вынесена из игровой логики."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from .engine import GameEngine, ScoreManager
from .entities import Food, GoldenFood, Obstacle, Portal, PowerUp
from .models import Difficulty, Direction, GameMode, GameSettings, GameState

BG = "#080F1F"
SURFACE = "#111D32"
SURFACE_ALT = "#16263E"
BORDER = "#263953"
TEXT = "#E9F3FF"
MUTED = "#8FA5BE"
NEON = "#35F2BB"
BLUE = "#58BBFA"
CELL = 26


class GameRenderer:
    """Отрисовка объектов через их общие интерфейсы color и glyph."""

    def __init__(self, cell_size: int = CELL):
        self._size = cell_size

    def draw(self, canvas: tk.Canvas, engine: GameEngine, show_grid: bool = True) -> None:
        canvas.delete("all")
        cell = self._size
        width = engine.settings.width * cell
        height = engine.settings.height * cell
        canvas.create_rectangle(0, 0, width, height, outline="", fill="#0B1729")
        # Лёгкая шахматная структура и сетка для ориентации игрока.
        for y in range(engine.settings.height):
            for x in range(engine.settings.width):
                if (x + y) % 2 == 0:
                    canvas.create_rectangle(x * cell, y * cell, (x + 1) * cell,
                                            (y + 1) * cell, fill="#0E1C30", outline="")
        if show_grid:
            for x in range(1, engine.settings.width):
                canvas.create_line(x * cell, 0, x * cell, height, fill="#15283F", width=1)
            for y in range(1, engine.settings.height):
                canvas.create_line(0, y * cell, width, y * cell, fill="#15283F", width=1)

        for entity in engine.entities:
            x, y = entity.position.x * cell, entity.position.y * cell
            color = entity.color
            if isinstance(entity, Obstacle):
                canvas.create_rectangle(x + 4, y + 4, x + cell - 4, y + cell - 4,
                                        fill="#53253C", outline=color, width=2)
                canvas.create_text(x + cell / 2, y + cell / 2 - 1,
                                   text=entity.glyph, fill=color, font=("Arial", 17, "bold"))
            elif isinstance(entity, Portal):
                canvas.create_oval(x + 3, y + 3, x + cell - 3, y + cell - 3,
                                   outline=color, width=3)
                canvas.create_oval(x + 9, y + 9, x + cell - 9, y + cell - 9,
                                   fill="#144552", outline="")
            elif isinstance(entity, (Food, GoldenFood)):
                canvas.create_oval(x + 3, y + 3, x + cell - 3, y + cell - 3,
                                   fill=color, outline="#C9FFF0" if isinstance(entity, Food)
                                   and not isinstance(entity, GoldenFood) else "#FFE2A1", width=1)
                if isinstance(entity, GoldenFood):
                    canvas.create_text(x + cell / 2, y + cell / 2,
                                       text=entity.glyph, fill="#4E3107", font=("Arial", 15, "bold"))
            elif isinstance(entity, PowerUp):
                canvas.create_oval(x + 2, y + 2, x + cell - 2, y + cell - 2,
                                   fill="#26334C", outline=color, width=2)
                canvas.create_text(x + cell / 2, y + cell / 2,
                                   text=entity.glyph, fill=color, font=("Arial", 12, "bold"))

        segments = engine.snake.segments
        ghost = engine.effect_active("ghost")
        for i in range(len(segments) - 1, -1, -1):
            pos = segments[i]
            x, y = pos.x * cell, pos.y * cell
            color = "#5BBDFF" if ghost else ("#BAFFE8" if i == 0 else "#27C99E")
            if i > 0 and i % 3 == 0 and not ghost:
                color = "#1DAA89"
            canvas.create_rectangle(x + 2, y + 2, x + cell - 2, y + cell - 2,
                                    fill=color, outline="#0C544A" if not ghost else "#165986", width=1)
            if i == 0:
                dx, dy = engine.snake.direction.value
                if dx:
                    eyes = [(0.66 if dx > 0 else 0.34, 0.31),
                            (0.66 if dx > 0 else 0.34, 0.69)]
                else:
                    eyes = [(0.31, 0.66 if dy > 0 else 0.34),
                            (0.69, 0.66 if dy > 0 else 0.34)]
                for ex, ey in eyes:
                    px, py = x + cell * ex, y + cell * ey
                    canvas.create_oval(px - 2.3, py - 2.3, px + 2.3, py + 2.3, fill="#0A2132", outline="")

        if engine.state != GameState.RUNNING:
            canvas.create_rectangle(0, 0, width, height,
                                    fill="#060E1C", stipple="gray50", outline="")
            heading = {
                GameState.READY: "SNAKE MAX",
                GameState.PAUSED: "ПАУЗА",
                GameState.GAME_OVER: "ИГРА ОКОНЧЕНА",
            }.get(engine.state, "")
            desc = {
                GameState.READY: "Змейка нового уровня",
                GameState.PAUSED: "Пробел — продолжить",
                GameState.GAME_OVER: f"Ваш счёт: {engine.score}",
            }.get(engine.state, "")
            canvas.create_text(width / 2, height / 2 - 49,
                               text=heading, fill=NEON, font=("Arial", 31, "bold"))
            canvas.create_text(width / 2, height / 2 + 3,
                               text=desc, fill=TEXT, font=("Arial", 17, "bold"))
            canvas.create_text(width / 2, height / 2 + 39,
                               text="Enter — начать заново" if engine.state == GameState.GAME_OVER
                               else "Нажмите «Играть»" if engine.state == GameState.READY
                               else "Управление: WASD / стрелки",
                               fill=MUTED, font=("Arial", 11))


class SnakeGameApp(tk.Tk):
    """Окно приложения, управление и наблюдение за GameEngine."""

    def __init__(self):
        super().__init__()
        self.title("SNAKE MAX — Змейка на максималках")
        self.configure(bg=BG)
        self.geometry("1100x755")
        self.minsize(1035, 725)
        self.engine = GameEngine()
        self._renderer = GameRenderer()
        self._scores = ScoreManager()
        self._show_grid = True
        self._recorded = False
        self._mode = tk.StringVar(value=GameMode.ARCADE.value)
        self._difficulty = tk.StringVar(value=Difficulty.MEDIUM.value)
        self._player = tk.StringVar(value="Игрок")
        self._create_widgets()
        self._render()
        self.bind("<KeyPress>", self._handle_key)
        self.after(130, self._game_loop)

    def _label(self, parent: tk.Widget, text: str, *, size: int = 11,
               color: str = TEXT, bold: bool = False, **kwargs) -> tk.Label:
        label = tk.Label(parent, text=text, bg=kwargs.pop("bg", BG), fg=color,
                         font=("Arial", size, "bold" if bold else "normal"), **kwargs)
        return label

    def _button(self, parent: tk.Widget, text: str, command, *, primary: bool = False,
                small: bool = False) -> tk.Button:
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0,
                         bg=NEON if primary else SURFACE_ALT,
                         fg="#06211E" if primary else TEXT,
                         activebackground="#86FFDE" if primary else "#27405E",
                         activeforeground="#06211E" if primary else TEXT,
                         cursor="hand2", pady=9 if small else 12,
                         font=("Arial", 10 if small else 12, "bold"))

    def _create_widgets(self) -> None:
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=35, pady=(22, 14))
        self._label(header, "▣  SNAKE", size=24, bold=True, color=TEXT).pack(side="left")
        self._label(header, " MAX", size=24, bold=True, color=NEON).pack(side="left")
        self._label(header, "ARCADE EDITION  /  PYTHON + TKINTER", size=10, color=MUTED).pack(side="right", pady=12)

        content = tk.Frame(self, bg=BG)
        content.pack(fill="both", expand=True, padx=35)
        left = tk.Frame(content, bg=BG)
        left.pack(side="left", fill="y")
        left_head = tk.Frame(left, bg=BG)
        left_head.pack(fill="x", pady=(0, 9))
        self._label(left_head, "АРЕНА", size=12, bold=True).pack(side="left")
        self._state_label = self._label(left_head, "● ГОТОВ К ИГРЕ", size=10, color=NEON)
        self._state_label.pack(side="right")
        border = tk.Frame(left, bg=BORDER, padx=2, pady=2)
        border.pack()
        self._canvas = tk.Canvas(border, width=26 * CELL, height=19 * CELL,
                                 highlightthickness=0, bg="#0B1729")
        self._canvas.pack()
        help_row = tk.Frame(left, bg=BG)
        help_row.pack(fill="x", pady=(12, 0))
        self._label(help_row, "●", color="#2CE7AE", size=12).pack(side="left")
        self._label(help_row, "еда", size=10, color=MUTED).pack(side="left", padx=(2, 14))
        self._label(help_row, "★", color="#FFC857", size=12).pack(side="left")
        self._label(help_row, "золото", size=10, color=MUTED).pack(side="left", padx=(2, 14))
        self._label(help_row, "◇", color=BLUE, size=12).pack(side="left")
        self._label(help_row, "бонусы", size=10, color=MUTED).pack(side="left", padx=(2, 14))
        self._label(help_row, "↻", color="#4AD8DE", size=12).pack(side="left")
        self._label(help_row, "порталы", size=10, color=MUTED).pack(side="left")
        self._hint = self._label(left, "Стрелки / WASD — движение · Space — пауза · G — сетка",
                                 size=10, color=MUTED, anchor="w")
        self._hint.pack(fill="x", pady=(13, 0))
        self._event = self._label(left, "Нажмите «Играть» или Enter", size=11, color=NEON,
                                  anchor="w", wraplength=650)
        self._event.pack(fill="x", pady=(10, 0))

        right = tk.Frame(content, bg=BG, width=302)
        right.pack(side="left", fill="both", expand=True, padx=(25, 0))
        right.pack_propagate(False)
        self._label(right, "НАСТРОЙКИ", size=12, bold=True).pack(anchor="w", pady=(0, 11))

        tk.Label(right, text="РЕЖИМ", bg=BG, fg=MUTED, font=("Arial", 9, "bold")).pack(anchor="w")
        self._mode_combo = self._combo(right, self._mode, [m.value for m in GameMode])
        self._mode_combo.pack(fill="x", pady=(5, 10), ipady=4)
        tk.Label(right, text="СЛОЖНОСТЬ", bg=BG, fg=MUTED, font=("Arial", 9, "bold")).pack(anchor="w")
        self._difficulty_combo = self._combo(right, self._difficulty, [m.value for m in Difficulty])
        self._difficulty_combo.pack(fill="x", pady=(5, 10), ipady=4)
        tk.Label(right, text="ИМЯ ИГРОКА", bg=BG, fg=MUTED, font=("Arial", 9, "bold")).pack(anchor="w")
        name_entry = tk.Entry(right, textvariable=self._player, bg=SURFACE_ALT, fg=TEXT,
                              insertbackground=TEXT, font=("Arial", 11), relief="flat", bd=0)
        name_entry.pack(fill="x", pady=(5, 12), ipady=8)
        self._button(right, "▶  ИГРАТЬ / ЗАНОВО", self._new_game, primary=True).pack(fill="x")
        self._pause_btn = self._button(right, "Ⅱ  ПАУЗА", self._toggle_pause, small=True)
        self._pause_btn.pack(fill="x", pady=(8, 0))

        stats = tk.Frame(right, bg=SURFACE, padx=17, pady=14)
        stats.pack(fill="x", pady=(15, 0))
        self._label(stats, "ТЕКУЩИЙ СЧЁТ", size=9, color=MUTED, bold=True, bg=SURFACE).pack(anchor="w")
        self._score_label = self._label(stats, "0000", size=28, bold=True, color=NEON, bg=SURFACE)
        self._score_label.pack(anchor="w", pady=(1, 3))
        stats_2 = tk.Frame(stats, bg=SURFACE)
        stats_2.pack(fill="x")
        self._food_label = self._label(stats_2, "Еда: 0", size=10, color=TEXT, bg=SURFACE)
        self._food_label.pack(side="left")
        self._speed_label = self._label(stats_2, "Шаг: 135 мс", size=10, color=MUTED, bg=SURFACE)
        self._speed_label.pack(side="right")
        self._effects_label = self._label(stats, "Бонусы: нет", size=10, color=BLUE,
                                         bg=SURFACE, anchor="w")
        self._effects_label.pack(fill="x", pady=(10, 0))

        board_head = tk.Frame(right, bg=BG)
        board_head.pack(fill="x", pady=(13, 7))
        self._label(board_head, "ТОП РЕКОРДОВ", size=11, bold=True).pack(side="left")
        self._button(board_head, "?", self._help, small=True).pack(side="right")
        self._records_box = tk.Frame(right, bg=SURFACE)
        self._records_box.pack(fill="x")
        self._refresh_records()
        self._label(right, "Змейка на максималках • версия 1.0", size=9, color=MUTED).pack(side="bottom", anchor="w", pady=(9, 0))

    def _combo(self, parent, variable, values):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Snake.TCombobox", background=SURFACE_ALT, fieldbackground=SURFACE_ALT,
                        foreground=TEXT, selectbackground=SURFACE_ALT,
                        selectforeground=TEXT, arrowcolor=NEON, bordercolor=SURFACE_ALT,
                        lightcolor=SURFACE_ALT, darkcolor=SURFACE_ALT)
        style.map("Snake.TCombobox", fieldbackground=[("readonly", SURFACE_ALT)],
                  foreground=[("readonly", TEXT)],
                  selectforeground=[("readonly", TEXT)],
                  selectbackground=[("readonly", SURFACE_ALT)])
        return ttk.Combobox(parent, textvariable=variable, values=values, state="readonly",
                            font=("Arial", 11), style="Snake.TCombobox")

    def _refresh_records(self) -> None:
        for widget in self._records_box.winfo_children():
            widget.destroy()
        records = self._scores.load()[:5]
        if not records:
            self._label(self._records_box, "Рекордов пока нет — станьте первым!",
                        size=10, color=MUTED, bg=SURFACE).pack(padx=13, pady=17)
            return
        for index, record in enumerate(records, start=1):
            item = tk.Frame(self._records_box, bg=SURFACE, padx=12)
            item.pack(fill="x", pady=5)
            self._label(item, f"{index:02d}", color=NEON if index == 1 else MUTED,
                        size=10, bold=True, bg=SURFACE).pack(side="left", padx=(0, 9))
            self._label(item, str(record.get("name", "Игрок"))[:14], color=TEXT,
                        size=10, bg=SURFACE).pack(side="left")
            self._label(item, str(record.get("score", 0)), color=NEON, size=10,
                        bold=True, bg=SURFACE).pack(side="right")

    def _new_game(self) -> None:
        self.engine = GameEngine(GameSettings(mode=GameMode(self._mode.get()),
                                              difficulty=Difficulty(self._difficulty.get())))
        self.engine.start()
        self._recorded = False
        self._render()
        self.focus_set()

    def _toggle_pause(self) -> None:
        self.engine.toggle_pause()
        self._render()
        self.focus_set()

    def _help(self) -> None:
        messagebox.showinfo("SNAKE MAX — правила", "РЕЖИМЫ\n"
                            "Аркада: препятствия, стены и порталы.\n"
                            "Выживание: препятствий больше, после каждых 6 яблок +2.\n"
                            "Дзен: без препятствий; выход за границу переносит на противоположную сторону.\n\n"
                            "БОНУСЫ\nЗелёный круг: +10 очков (растёт длина).\n"
                            "Золотая звезда: +50 очков.\n"
                            "2×: удвоение очков на 18 ходов.\n"
                            "◇: режим призрака на 14 ходов.\n"
                            "◷: замедление на 15 ходов.\n\n"
                            "УПРАВЛЕНИЕ\nWASD/стрелки — перемещение, Space — пауза, "
                            "Enter — начать/перезапустить, G — сетка, R — перезапуск.")
        self.focus_set()

    def _handle_key(self, event) -> None:
        # При вводе имени WASD должны вводить текст, а не управлять змейкой.
        is_entry = isinstance(event.widget, (tk.Entry, ttk.Combobox))
        key = event.keysym.lower()
        if is_entry and key not in ("escape",):
            return
        arrows = {"up": Direction.UP, "w": Direction.UP,
                  "down": Direction.DOWN, "s": Direction.DOWN,
                  "left": Direction.LEFT, "a": Direction.LEFT,
                  "right": Direction.RIGHT, "d": Direction.RIGHT}
        if key in arrows:
            self.engine.set_direction(arrows[key])
        elif key == "space":
            self._toggle_pause()
        elif key == "g":
            self._show_grid = not self._show_grid
            self._render()
        elif key == "r" or (key == "return" and self.engine.state in
                             (GameState.READY, GameState.GAME_OVER)):
            self._new_game()
        elif key == "return" and self.engine.state == GameState.PAUSED:
            self._toggle_pause()

    def _game_loop(self) -> None:
        if self.engine.state == GameState.RUNNING:
            self.engine.step()
            if self.engine.state == GameState.GAME_OVER and not self._recorded:
                self._scores.save(self._player.get(), self.engine.score,
                                  self.engine.settings.mode, self.engine.settings.difficulty)
                self._recorded = True
                self._refresh_records()
        self._render()
        self.after(self.engine.tick_interval_ms, self._game_loop)

    def _render(self) -> None:
        engine = self.engine
        self._renderer.draw(self._canvas, engine, self._show_grid)
        self._score_label.configure(text=f"{engine.score:04d}")
        self._food_label.configure(text=f"Еда: {engine.foods_eaten}")
        self._speed_label.configure(text=f"Шаг: {engine.tick_interval_ms} мс")
        self._state_label.configure(text="● " + engine.state.value.upper(),
                                    fg="#E65E77" if engine.state == GameState.GAME_OVER else NEON)
        labels = {"double": "2×", "ghost": "Призрак", "slow": "Замедление"}
        effects = ", ".join(f"{labels[k]} ({v})" for k, v in engine.effects.items())
        self._effects_label.configure(text="Бонусы: " + (effects or "нет"))
        self._event.configure(text=engine.last_event,
                              fg="#FF8E9E" if engine.state == GameState.GAME_OVER else NEON)
        self._pause_btn.configure(text="▶  ПРОДОЛЖИТЬ" if engine.state == GameState.PAUSED
                                  else "Ⅱ  ПАУЗА")
