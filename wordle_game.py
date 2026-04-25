import random
from collections import Counter, defaultdict
from functools import lru_cache

# --- Global Constants ---
# These act as the 'Protocol' for bot-to-game communication
CORRECT = "+"
WRONG_POS = "*"
NOT_IN_WORD = "-"
MAX_GUESSES = 25  # Set to your preferred trial limit


class WordleGame:
    def __init__(self, word_list_path="words.txt", secret_word=None, word_list=None):
        """
        Initializes a Wordle environment.

        Args:
            word_list_path (str): Path to the dictionary file if no list is provided.
            secret_word (str): Optional hardcoded secret for specific testing.
            word_list (set): Optional pre-loaded set of words to save I/O time.
        """
        # 1. Source the dictionary
        if word_list is not None:
            self.words = set(word_list)
        else:
            self.words = self._load_words(word_list_path)

        # 2. Set the secret word
        if secret_word:
            self.secret = secret_word.lower()
        else:
            if not self.words:
                raise ValueError("Word list is empty. Cannot choose a secret.")
            self.secret = random.choice(tuple(self.words))

        # 3. State Tracking (isolated by bot_id)
        self.sessions = defaultdict(list)
        self.status = defaultdict(lambda: {"won": False, "over": False})

    def _load_words(self, path):
        """Internal helper to load 5-letter words from a file."""
        try:
            with open(path, "r") as f:
                return {line.strip().lower() for line in f if len(line.strip()) == 5}
        except FileNotFoundError:
            # Fallback or error depending on your env
            print(f"Warning: {path} not found. Ensure it exists in the root.")
            return set()

    @lru_cache(maxsize=2048)
    def _get_feedback(self, guess):
        """
        The core Wordle logic engine.
        Uses a two-pass approach to handle duplicate letters correctly.
        """
        feedback = [NOT_IN_WORD] * 5
        inventory = Counter(self.secret)

        # First Pass: Identify Greens (Correct position)
        for i in range(5):
            if guess[i] == self.secret[i]:
                feedback[i] = CORRECT
                inventory[guess[i]] -= 1

        # Second Pass: Identify Yellows (Wrong position)
        for i in range(5):
            if feedback[i] == CORRECT:
                continue
            char = guess[i]
            if inventory[char] > 0:
                feedback[i] = WRONG_POS
                inventory[char] -= 1

        return "".join(feedback)

    def play(self, bot_id, guess):
        """
        The primary API for solvers.
        Updates the specific bot's session and returns the current game state.
        """
        guess = guess.lower()
        bot_state = self.status[bot_id]

        # Guard Clauses
        if bot_state["over"]:
            return {"error": "Game already over for this bot.", "over": True}

        if len(guess) != 5 or guess not in self.words:
            return {"error": "Invalid word. Not in dictionary.", "valid": False}

        # Process Turn
        feedback = self._get_feedback(guess)
        self.sessions[bot_id].append({"guess": guess, "feedback": feedback})

        # Update Session State
        turn = len(self.sessions[bot_id])
        if feedback == "+++++":
            bot_state["won"] = True
            bot_state["over"] = True
        elif turn >= MAX_GUESSES:
            bot_state["over"] = True

        return {
            "feedback": feedback,
            "turn": turn,
            "won": bot_state["won"],
            "over": bot_state["over"],
            "history": self.sessions[bot_id],
        }

    def get_bot_summary(self, bot_id):
        """
        Returns a human-readable (and shareable) summary of a bot's performance.
        """
        if bot_id not in self.sessions:
            return {"error": "No history found for this bot_id."}

        emoji_map = {CORRECT: "🟩", WRONG_POS: "🟨", NOT_IN_WORD: "⬛"}
        grid = []
        for turn in self.sessions[bot_id]:
            grid.append("".join(emoji_map[symbol] for symbol in turn["feedback"]))

        score = len(self.sessions[bot_id]) if self.status[bot_id]["won"] else "X"

        return {
            "bot_id": bot_id,
            "score": f"{score}/{MAX_GUESSES}",
            "grid": "\n".join(grid),
            "won": self.status[bot_id]["won"],
        }
