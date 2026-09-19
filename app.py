import json
import random
import sys
import tkinter as tk
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from tkinter import font as tkfont
from tkinter import ttk
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


class TriviaQuestion(BaseModel):
    """A single generated question with four choices and its answer key."""

    question: str
    choices: list[str] = Field(min_length=4, max_length=4)
    correct_answer: Literal["A", "B", "C", "D"]


class TriviaQuiz(BaseModel):
    """The validated 15-question payload returned by the OpenAI API."""

    questions: list[TriviaQuestion] = Field(min_length=15, max_length=15)


class TriviaApp:
    """Manage the user interface, game state, persistence, and quiz generation."""

    CHOICE_LETTERS = "ABCD"
    HIGH_SCORE_FILE = Path(__file__).with_name("high_score.json")
    QUESTION_HISTORY_FILE = Path(__file__).with_name("question_history.json")
    LOGO_FILE = Path(__file__).parent / "assets" / "music-millionaire-logo-ui.png"
    MAX_HISTORY_PER_CATEGORY = 200
    PROMPT_HISTORY_LIMIT = 60
    NAVY = "#05062D"
    INDIGO = "#111052"
    DEEP_BLUE = "#17146B"
    CYAN = "#22D3EE"
    VIOLET = "#7C3AED"
    GOLD = "#F6C453"
    WHITE = "#F8FAFC"
    MUTED = "#A5B4FC"
    CORRECT = "#34D399"
    INCORRECT = "#FB7185"
    PRIZE_LADDER = (
        100,
        200,
        300,
        500,
        1_000,
        2_000,
        4_000,
        8_000,
        16_000,
        32_000,
        64_000,
        125_000,
        250_000,
        500_000,
        1_000_000,
    )
    CATEGORIES = {
        "Rock Music": "rock music",
        "Punk Music": "punk music",
        "Blues": "blues music",
        "2000+ Pop": "pop music released from the year 2000 to the present",
    }
    VARIETY_ANGLES = (
        "artists and bands",
        "albums and songs",
        "music history and major milestones",
        "live performances, instruments, and recording facts",
    )

    def __init__(self, root: tk.Tk) -> None:
        """Initialize window settings, saved data, game state, and UI widgets."""

        self.root = root
        self.root.title("Who Wants to Be a Music Millionaire?")
        self.root.geometry("760x780")
        self.root.minsize(500, 520)

        available_fonts = set(tkfont.families(self.root))
        self.display_font = self._pick_font(
            available_fonts, "Copperplate", "Palatino", "Georgia", "Times New Roman"
        )
        self.body_font = self._pick_font(
            available_fonts,
            "Avenir Next",
            "Helvetica Neue",
            "Segoe UI",
            "Helvetica",
            "Arial",
        )

        self.quiz: TriviaQuiz | None = None
        self.question_number = 0
        self.score = 0
        self.current_category = ""
        self.lifeline_used = False
        self.high_score = self.load_high_score()
        self.question_history = self.load_question_history()
        self.paused_game_state = ""
        self.game_snapshot: dict[str, object] = {}
        self.screen_state = "category"
        self.answer_var = tk.StringVar()
        self.results: Queue[tuple[str, object]] = Queue()

        self._configure_styles()
        self._build_interface()
        self.show_category_selection()

    @staticmethod
    def _pick_font(available_fonts: set[str], *preferred_fonts: str) -> str:
        """Return the first installed preferred font or Tk's default font."""

        return next(
            (font for font in preferred_fonts if font in available_fonts),
            "TkDefaultFont",
        )

    def _configure_styles(self) -> None:
        """Define the shared colors, fonts, and interaction styles for widgets."""

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background=self.NAVY)
        style.configure(
            "Option.TRadiobutton",
            background=self.INDIGO,
            foreground=self.WHITE,
            font=(self.body_font, 13),
            padding=12,
            indicatorcolor=self.NAVY,
            bordercolor=self.CYAN,
        )
        style.map(
            "Option.TRadiobutton",
            background=[("active", self.DEEP_BLUE), ("selected", self.VIOLET)],
            foreground=[("disabled", self.MUTED)],
        )
        style.configure(
            "Action.TButton",
            background=self.VIOLET,
            foreground=self.WHITE,
            bordercolor=self.CYAN,
            font=(self.body_font, 12, "bold"),
            padding=(12, 12),
        )
        style.map(
            "Action.TButton",
            background=[("active", self.DEEP_BLUE), ("pressed", self.INDIGO)],
            foreground=[("disabled", self.MUTED)],
        )
        style.configure(
            "HomeIcon.TButton",
            background=self.INDIGO,
            foreground=self.GOLD,
            bordercolor=self.CYAN,
            font=(self.body_font, 20, "bold"),
            padding=(8, 5),
        )
        style.map(
            "HomeIcon.TButton",
            background=[("active", self.VIOLET), ("pressed", self.DEEP_BLUE)],
            foreground=[("active", self.WHITE)],
        )
        style.configure(
            "Category.TButton",
            background=self.DEEP_BLUE,
            foreground=self.WHITE,
            bordercolor=self.GOLD,
            font=(self.display_font, 14, "bold"),
            padding=(14, 14),
        )
        style.map(
            "Category.TButton",
            background=[
                ("disabled", self.INDIGO),
                ("active", self.VIOLET),
                ("pressed", self.INDIGO),
            ],
            foreground=[("disabled", self.MUTED)],
        )
        style.configure(
            "Game.Vertical.TScrollbar",
            background=self.VIOLET,
            troughcolor=self.NAVY,
            bordercolor=self.NAVY,
            arrowcolor=self.GOLD,
            lightcolor=self.VIOLET,
            darkcolor=self.VIOLET,
            gripcount=0,
            arrowsize=11,
            width=10,
        )
        style.map(
            "Game.Vertical.TScrollbar",
            background=[("active", self.CYAN), ("pressed", self.GOLD)],
        )

    def _add_logo(self, container: ttk.Frame) -> None:
        """Load the project logo and place it at the top of the main content."""

        self.logo_image = tk.PhotoImage(file=str(self.LOGO_FILE))
        tk.Label(
            container,
            image=self.logo_image,
            bg=self.NAVY,
            borderwidth=0,
        ).pack(pady=(0, 8))

    def _build_interface(self) -> None:
        """Create every screen, label, option, button, and scrolling container."""

        self.root.configure(background=self.NAVY)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.scrollbar = ttk.Scrollbar(
            self.root,
            orient="vertical",
            style="Game.Vertical.TScrollbar",
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.canvas = tk.Canvas(
            self.root,
            bg=self.NAVY,
            highlightthickness=0,
            yscrollcommand=self._set_scrollbar,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.config(command=self.canvas.yview)

        self.credit_label = tk.Label(
            self.root,
            text="Constructed by ChatGPT (GPT-5)",
            bg=self.INDIGO,
            fg=self.MUTED,
            font=(self.body_font, 9),
            pady=6,
        )
        self.credit_label.grid(row=1, column=0, columnspan=2, sticky="ew")

        container = ttk.Frame(self.canvas, padding=24, style="App.TFrame")
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=container, anchor="nw"
        )
        container.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_content)
        self.canvas.bind_all("<MouseWheel>", self._scroll_with_mouse, add="+")
        self.canvas.bind_all("<Button-4>", self._scroll_up, add="+")
        self.canvas.bind_all("<Button-5>", self._scroll_down, add="+")

        self._add_logo(container)

        self.progress_label = tk.Label(
            container,
            bg=self.NAVY,
            fg=self.MUTED,
            font=(self.body_font, 11),
        )
        self.progress_label.pack(pady=(0, 18))

        self.prize_label = tk.Label(
            container,
            bg=self.NAVY,
            fg=self.GOLD,
            font=(self.display_font, 12, "bold"),
        )
        self.prize_label.pack(pady=(0, 12))

        self.high_score_label = tk.Label(
            container,
            text=f"Highest cash prize: ${self.high_score:,}",
            bg=self.NAVY,
            fg=self.CORRECT,
            font=(self.body_font, 11, "bold"),
        )
        self.high_score_label.pack(pady=(0, 12))

        self.question_label = tk.Label(
            container,
            bg=self.NAVY,
            fg=self.WHITE,
            font=(self.body_font, 17, "bold"),
            justify="left",
            wraplength=640,
        )
        self.question_label.pack(fill="x", pady=(0, 18))

        self.category_frame = ttk.Frame(container, style="App.TFrame")
        self.category_frame.columnconfigure(0, weight=1)
        self.category_frame.columnconfigure(1, weight=1)

        self.category_buttons: list[ttk.Button] = []
        for index, category in enumerate(self.CATEGORIES):
            button = ttk.Button(
                self.category_frame,
                text=category,
                command=lambda selected=category: self.load_quiz(selected),
                style="Category.TButton",
            )
            button.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=6,
                pady=6,
            )
            self.category_buttons.append(button)

        self.home_menu_frame = ttk.Frame(container, style="App.TFrame")
        self.home_menu_frame.columnconfigure(0, weight=1)

        ttk.Button(
            self.home_menu_frame,
            text="Leave Game\n(All Progress Will Be Lost)",
            command=self.leave_game,
            style="Category.TButton",
        ).grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        ttk.Button(
            self.home_menu_frame,
            text="Pause Game",
            command=self.pause_game,
            style="Category.TButton",
        ).grid(row=1, column=0, sticky="ew", padx=6, pady=6)

        self.options_frame = ttk.Frame(container, style="App.TFrame")

        self.option_buttons: list[ttk.Radiobutton] = []
        for letter in self.CHOICE_LETTERS:
            button = ttk.Radiobutton(
                self.options_frame,
                variable=self.answer_var,
                value=letter,
                style="Option.TRadiobutton",
            )
            button.pack(fill="x", pady=3)
            self.option_buttons.append(button)

        self.feedback_label = tk.Label(
            container,
            bg=self.NAVY,
            fg=self.WHITE,
            font=(self.body_font, 12, "bold"),
            wraplength=640,
        )
        self.feedback_label.pack(pady=16)

        self.action_button = ttk.Button(
            container,
            text="Submit Answer",
            command=self.handle_action,
            style="Action.TButton",
        )
        self.action_button.pack(side="bottom", fill="x")

        self.walk_away_button = ttk.Button(
            container,
            text="Walk Away",
            command=self.walk_away,
            style="Action.TButton",
        )
        self.walk_away_button.pack(side="bottom", fill="x", pady=(8, 0))

        self.lifeline_button = ttk.Button(
            container,
            text="Use 50:50 Lifeline",
            command=self.use_fifty_fifty,
            style="Action.TButton",
        )
        self.lifeline_button.pack(side="bottom", fill="x", pady=(8, 0))

        self.home_button = ttk.Button(
            self.root,
            text="⌂",
            command=self.open_home_menu,
            style="HomeIcon.TButton",
            width=3,
            cursor="hand2",
        )
        self.home_button.place_forget()

    def _update_scroll_region(self, _event: tk.Event) -> None:
        """Update the canvas boundaries whenever its inner content changes size."""

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _set_scrollbar(self, first: str, last: str) -> None:
        """Synchronize the scrollbar and hide it when all content already fits."""

        self.scrollbar.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            self.scrollbar.grid_remove()
        else:
            self.scrollbar.grid()

    def _resize_content(self, event: tk.Event) -> None:
        """Match content width to the window and re-wrap long text responsively."""

        self.canvas.itemconfigure(self.canvas_window, width=event.width)
        wrap_width = max(300, event.width - 80)
        self.question_label.config(wraplength=wrap_width)
        self.feedback_label.config(wraplength=wrap_width)

    def _scroll_with_mouse(self, event: tk.Event) -> None:
        """Translate mouse-wheel or trackpad movement into smooth pixel scrolling."""

        if not event.delta:
            return

        if sys.platform == "darwin":
            pixel_delta = -event.delta * 3
        else:
            pixel_delta = -(event.delta / 120) * 40
        self._scroll_pixels(pixel_delta)

    def _scroll_pixels(self, pixel_delta: float) -> None:
        """Move the canvas by a pixel-based amount while respecting its limits."""

        scroll_region = self.canvas.bbox("all")
        if scroll_region is None:
            return

        content_height = scroll_region[3] - scroll_region[1]
        if content_height <= self.canvas.winfo_height():
            return

        first, _last = self.canvas.yview()
        new_position = first + (pixel_delta / content_height)
        self.canvas.yview_moveto(max(0.0, min(1.0, new_position)))

    def _scroll_up(self, _event: tk.Event) -> None:
        """Handle Linux-style upward mouse-wheel events."""

        self._scroll_pixels(-40)

    def _scroll_down(self, _event: tk.Event) -> None:
        """Handle Linux-style downward mouse-wheel events."""

        self._scroll_pixels(40)

    def _scroll_to_top(self) -> None:
        """Schedule the current screen to return to its topmost scroll position."""

        self.canvas.after_idle(self.canvas.yview_moveto, 0)

    def load_high_score(self) -> int:
        """Read the highest completed cash prize from disk, defaulting to zero."""

        try:
            data = json.loads(self.HIGH_SCORE_FILE.read_text(encoding="utf-8"))
            high_score = data["highest_cash_prize"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            return 0

        if not isinstance(high_score, int) or high_score < 0:
            return 0
        return high_score

    def load_question_history(self) -> dict[str, list[str]]:
        """Load and validate the bounded per-category question history from disk."""

        try:
            data = json.loads(self.QUESTION_HISTORY_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        if not isinstance(data, dict):
            return {}

        history: dict[str, list[str]] = {}
        for category in self.CATEGORIES:
            questions = data.get(category, [])
            if isinstance(questions, list):
                history[category] = [
                    question.strip()
                    for question in questions
                    if isinstance(question, str) and question.strip()
                ][-self.MAX_HISTORY_PER_CATEGORY :]
        return history

    def remember_questions(self, category: str, quiz: TriviaQuiz) -> None:
        """Add new unique questions to category history and persist it as JSON."""

        previous_questions = self.question_history.setdefault(category, [])
        normalized_questions = {
            question.casefold().strip() for question in previous_questions
        }

        for trivia_question in quiz.questions:
            question = trivia_question.question.strip()
            normalized_question = question.casefold()
            if question and normalized_question not in normalized_questions:
                previous_questions.append(question)
                normalized_questions.add(normalized_question)

        self.question_history[category] = previous_questions[
            -self.MAX_HISTORY_PER_CATEGORY :
        ]
        try:
            self.QUESTION_HISTORY_FILE.write_text(
                json.dumps(self.question_history, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def record_cash_prize(self, winnings: int) -> None:
        """Persist winnings only when they exceed the existing highest prize."""

        if winnings <= self.high_score:
            return

        self.high_score = winnings
        self.high_score_label.config(
            text=f"Highest cash prize: ${self.high_score:,}"
        )
        try:
            self.HIGH_SCORE_FILE.write_text(
                json.dumps({"highest_cash_prize": winnings}, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def open_home_menu(self) -> None:
        """Snapshot the active game and show the leave-or-pause decision screen."""

        if self.screen_state not in {"answering", "feedback"}:
            return

        self.paused_game_state = self.screen_state
        self.game_snapshot = {
            "progress": self.progress_label.cget("text"),
            "prize": self.prize_label.cget("text"),
            "question": self.question_label.cget("text"),
            "feedback": self.feedback_label.cget("text"),
            "feedback_color": self.feedback_label.cget("foreground"),
            "action_text": self.action_button.cget("text"),
            "action_state": self.action_button.cget("state"),
            "walk_state": self.walk_away_button.cget("state"),
            "lifeline_text": self.lifeline_button.cget("text"),
            "lifeline_state": self.lifeline_button.cget("state"),
        }

        self.screen_state = "home_prompt"
        self.progress_label.config(text="Game in progress")
        self.prize_label.config(text="Choose what happens to your current run")
        self.question_label.config(text="Return to the main menu?")
        self.feedback_label.config(text="", fg=self.WHITE)
        self.options_frame.pack_forget()
        self.action_button.pack_forget()
        self.walk_away_button.pack_forget()
        self.lifeline_button.pack_forget()
        self.home_button.place_forget()
        self.home_menu_frame.pack(fill="x", before=self.feedback_label)
        self._scroll_to_top()

    def pause_game(self) -> None:
        """Show a disabled main menu while retaining the current game in memory."""

        if self.screen_state != "home_prompt":
            return

        self.screen_state = "paused"
        self.home_menu_frame.pack_forget()
        for button in self.category_buttons:
            button.config(state="disabled")

        self.progress_label.config(text="Game paused")
        self.prize_label.config(text="Your current run is waiting for you")
        self.question_label.config(text="Main Menu")
        self.feedback_label.config(
            text="Category buttons are unavailable while a game is paused.",
            fg=self.MUTED,
        )
        self.category_frame.pack(fill="x", before=self.feedback_label)
        self.action_button.pack(side="bottom", fill="x")
        self.action_button.config(text="Resume Game", state="normal")
        self._scroll_to_top()

    def resume_game(self) -> None:
        """Restore the exact question, feedback, controls, and state saved on pause."""

        if self.screen_state != "paused" or not self.game_snapshot:
            return

        self.category_frame.pack_forget()
        for button in self.category_buttons:
            button.config(state="normal")

        self.progress_label.config(text=self.game_snapshot["progress"])
        self.prize_label.config(text=self.game_snapshot["prize"])
        self.question_label.config(text=self.game_snapshot["question"])
        self.feedback_label.config(
            text=self.game_snapshot["feedback"],
            fg=self.game_snapshot["feedback_color"],
        )
        self.options_frame.pack(fill="x", before=self.feedback_label)
        self.action_button.pack(side="bottom", fill="x")
        self.walk_away_button.pack(side="bottom", fill="x", pady=(8, 0))
        self.lifeline_button.pack(side="bottom", fill="x", pady=(8, 0))
        self.home_button.place(x=14, y=14)
        self.home_button.lift()
        self.action_button.config(
            text=self.game_snapshot["action_text"],
            state=self.game_snapshot["action_state"],
        )
        self.walk_away_button.config(state=self.game_snapshot["walk_state"])
        self.lifeline_button.config(
            text=self.game_snapshot["lifeline_text"],
            state=self.game_snapshot["lifeline_state"],
        )
        self.home_button.config(state="normal")
        self.screen_state = self.paused_game_state
        self._scroll_to_top()

    def leave_game(self) -> None:
        """Abandon the current run without recording winnings and reset the menu."""

        if self.screen_state not in {"home_prompt", "paused"}:
            return

        self.show_category_selection()

    def show_category_selection(self) -> None:
        """Reset transient game state and display the interactive category menu."""

        self._scroll_to_top()
        self.screen_state = "category"
        self.quiz = None
        self.current_category = ""
        self.paused_game_state = ""
        self.game_snapshot = {}
        for button in self.category_buttons:
            button.config(state="normal")
        self.progress_label.config(text="Choose a category")
        self.prize_label.config(text="Top prize: $1,000,000")
        self.question_label.config(text="What kind of music do you know best?")
        self.feedback_label.config(text="")
        self.home_menu_frame.pack_forget()
        self.options_frame.pack_forget()
        self.home_button.place_forget()
        self.lifeline_button.pack_forget()
        self.walk_away_button.pack_forget()
        self.action_button.pack_forget()
        self.category_frame.pack(fill="x", before=self.feedback_label)

    def load_quiz(self, category: str) -> None:
        """Show a loading screen and request a fresh quiz on a background thread."""

        self._scroll_to_top()
        self.screen_state = "loading"
        self.quiz = None
        self.current_category = category
        self.progress_label.config(text=f"Creating a {category} game...")
        self.prize_label.config(text="Building your $1,000,000 challenge...")
        self.question_label.config(text="Please wait while the questions load.")
        self.feedback_label.config(text="")
        self.category_frame.pack_forget()
        self.home_menu_frame.pack_forget()
        self.options_frame.pack_forget()
        self.home_button.place_forget()
        self.lifeline_button.pack_forget()
        self.walk_away_button.pack_forget()
        self.action_button.pack_forget()

        category_topic = self.CATEGORIES[category]
        recent_questions = tuple(
            self.question_history.get(category, [])[-self.PROMPT_HISTORY_LIMIT :]
        )
        Thread(
            target=self._generate_quiz,
            args=(category, category_topic, recent_questions),
            daemon=True,
        ).start()
        self.root.after(100, self._check_for_quiz)

    def _generate_quiz(
        self,
        category: str,
        category_topic: str,
        recent_questions: tuple[str, ...],
    ) -> None:
        """Call OpenAI for a structured quiz, avoiding recent category questions."""

        try:
            variety_angle = random.choice(self.VARIETY_ANGLES)
            exclusion_text = ""
            if recent_questions:
                excluded_questions = "\n".join(
                    f"- {question}" for question in recent_questions
                )
                exclusion_text = (
                    "\n\nPreviously asked questions are listed below. Do not "
                    "reuse these questions, their underlying facts, or close "
                    f"paraphrases:\n{excluded_questions}"
                )

            client = OpenAI()
            response = client.responses.parse(
                model="gpt-5.6-luna",
                input=(
                    f"Create a 15-question trivia quiz about {category_topic}. "
                    "Each question must be factually accurate and have exactly "
                    "four distinct choices. Begin with very easy questions and "
                    "increase the difficulty steadily so the final questions are "
                    "expert-level, like a TV game show prize ladder. Do not repeat "
                    "facts within the quiz. Provide the correct choice as A, B, C, "
                    f"or D. For variety, emphasize {variety_angle} while still "
                    f"covering a broad range of the category.{exclusion_text}"
                ),
                text_format=TriviaQuiz,
            )
            if response.output_parsed is None:
                raise RuntimeError("The model did not return a quiz.")
            self.remember_questions(category, response.output_parsed)
            self.results.put(("success", response.output_parsed))
        except Exception as error:
            self.results.put(("error", str(error)))

    def _check_for_quiz(self) -> None:
        """Poll the thread-safe result queue until generation succeeds or fails."""

        try:
            result_type, result = self.results.get_nowait()
        except Empty:
            self.root.after(100, self._check_for_quiz)
            return

        if result_type == "success" and isinstance(result, TriviaQuiz):
            self.start_quiz(result)
        else:
            self.show_error(str(result))

    def start_quiz(self, quiz: TriviaQuiz) -> None:
        """Initialize a new run and reveal its gameplay controls."""

        self.quiz = quiz
        self.question_number = 0
        self.score = 0
        self.lifeline_used = False
        self.options_frame.pack(fill="x", before=self.feedback_label)
        self.action_button.pack(side="bottom", fill="x")
        self.walk_away_button.pack(side="bottom", fill="x", pady=(8, 0))
        self.lifeline_button.pack(side="bottom", fill="x", pady=(8, 0))
        self.home_button.place(x=14, y=14)
        self.home_button.lift()
        self.lifeline_button.config(text="Use 50:50 Lifeline", state="normal")
        self.home_button.config(state="normal")
        self.show_question()

    def show_question(self) -> None:
        """Render the current question, prize information, and available choices."""

        if self.quiz is None:
            return

        self._scroll_to_top()
        self.screen_state = "answering"
        question = self.quiz.questions[self.question_number]
        self.answer_var.set("")
        prize = self.PRIZE_LADDER[self.question_number]
        current_winnings = self.PRIZE_LADDER[self.score - 1] if self.score else 0
        self.progress_label.config(
            text=(
                f"{self.current_category}  •  Question "
                f"{self.question_number + 1} for ${prize:,}"
            )
        )
        self.prize_label.config(
            text=(
                f"Current winnings: ${current_winnings:,}  •  "
                f"Guaranteed: ${self.guaranteed_winnings():,}"
            )
        )
        self.question_label.config(text=question.question)
        self.feedback_label.config(text="")

        for letter, choice, button in zip(
            self.CHOICE_LETTERS, question.choices, self.option_buttons
        ):
            button.config(text=f"{letter}.  {choice}", state="normal")

        self.action_button.config(text="Submit Answer", state="normal")
        self.walk_away_button.config(state="normal")
        self.lifeline_button.config(
            state="disabled" if self.lifeline_used else "normal"
        )

    def handle_action(self) -> None:
        """Route the main action button according to the current screen state."""

        if self.screen_state == "paused":
            self.resume_game()
        elif self.screen_state == "answering":
            self.submit_answer()
        elif self.screen_state == "feedback":
            self.question_number += 1
            self.show_question()
        elif self.screen_state == "finished":
            self.show_category_selection()
        elif self.screen_state == "error":
            self.load_quiz(self.current_category)

    def guaranteed_winnings(self) -> int:
        """Return the secured checkpoint prize based on answered questions."""

        if self.score >= 10:
            return 32_000
        if self.score >= 5:
            return 1_000
        return 0

    def use_fifty_fifty(self) -> None:
        """Use the one-time lifeline by disabling two incorrect choices."""

        if self.quiz is None or self.screen_state != "answering" or self.lifeline_used:
            return

        question = self.quiz.questions[self.question_number]
        incorrect_letters = [
            letter
            for letter in self.CHOICE_LETTERS
            if letter != question.correct_answer
        ]
        removed_letters = incorrect_letters[:2]

        if self.answer_var.get() in removed_letters:
            self.answer_var.set("")

        for letter in removed_letters:
            index = self.CHOICE_LETTERS.index(letter)
            self.option_buttons[index].config(text="", state="disabled")

        self.lifeline_used = True
        self.lifeline_button.config(text="50:50 Lifeline Used", state="disabled")

    def walk_away(self) -> None:
        """End the run voluntarily and bank the latest correctly earned prize."""

        if self.screen_state not in {"answering", "feedback"}:
            return

        winnings = self.PRIZE_LADDER[self.score - 1] if self.score else 0
        self.show_end_screen(
            heading="You walked away!",
            message=f"You leave the game with ${winnings:,}.",
            cash_prize=winnings,
        )

    def submit_answer(self) -> None:
        """Validate and score the selected answer, then advance or end the run."""

        if self.quiz is None:
            return

        selected_answer = self.answer_var.get()
        if selected_answer not in self.CHOICE_LETTERS:
            self.feedback_label.config(
                text="Choose A, B, C, or D before submitting.", fg=self.GOLD
            )
            return

        question = self.quiz.questions[self.question_number]
        if selected_answer == question.correct_answer:
            self.score += 1
            prize = self.PRIZE_LADDER[self.question_number]
            if prize == 1_000_000:
                self.show_end_screen(
                    heading="You are a Music Millionaire!",
                    message="Congratulations—you won $1,000,000!",
                    cash_prize=1_000_000,
                )
                return

            self.feedback_label.config(
                text=f"Correct! You have won ${prize:,}.", fg=self.CORRECT
            )
        else:
            correct_index = self.CHOICE_LETTERS.index(question.correct_answer)
            correct_choice = question.choices[correct_index]
            guaranteed = self.guaranteed_winnings()
            self.show_end_screen(
                heading="That is not the correct answer.",
                message=(
                    f"The answer was {question.correct_answer}. {correct_choice}.\n"
                    f"You leave with ${guaranteed:,}."
                ),
                cash_prize=guaranteed,
            )
            return

        for button in self.option_buttons:
            button.config(state="disabled")

        self.screen_state = "feedback"
        self.lifeline_button.config(state="disabled")
        self.action_button.config(text="Next Question")

    def show_end_screen(self, heading: str, message: str, cash_prize: int) -> None:
        """Finish a run, record eligible winnings, and show its outcome message."""

        self._scroll_to_top()
        self.record_cash_prize(cash_prize)
        self.screen_state = "finished"
        self.progress_label.config(
            text=f"{self.current_category} game complete"
        )
        self.prize_label.config(text="")
        self.question_label.config(text=heading)
        self.options_frame.pack_forget()
        self.home_menu_frame.pack_forget()
        self.home_button.place_forget()
        self.lifeline_button.pack_forget()
        self.walk_away_button.pack_forget()
        self.feedback_label.config(text=message, fg=self.WHITE)
        self.action_button.config(text="Choose Another Category", state="normal")

    def show_error(self, message: str) -> None:
        """Replace the current screen with a retryable quiz-generation error."""

        self._scroll_to_top()
        self.screen_state = "error"
        self.progress_label.config(text="Could not create the quiz")
        self.prize_label.config(text="")
        self.question_label.config(text="Something went wrong.")
        self.feedback_label.config(text=message, fg=self.INCORRECT)
        self.home_menu_frame.pack_forget()
        self.home_button.place_forget()
        self.lifeline_button.pack_forget()
        self.walk_away_button.pack_forget()
        self.action_button.pack(side="bottom", fill="x")
        self.action_button.config(text="Try Again", state="normal")


def main() -> None:
    """Load environment settings, create the Tk window, and start its event loop."""

    load_dotenv()
    root = tk.Tk()
    TriviaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
