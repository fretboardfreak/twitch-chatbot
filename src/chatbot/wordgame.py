"""A word guessing game for chat."""

# Copyright 2024 Curtis Sand
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import logging
import random
import string
import threading

from importlib import resources
from functools import cache

import yaml

from twitchio.ext import commands


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MissingLockError(RuntimeError):
    """Used to indicate a section of code that requires a lock before running."""


class WordgameError(Exception):
    """Used to indicite a miscellaneous error within the wordgame."""


class WordgameUI(commands.Cog):
    """TwitchIO Cog providing a chat interface to the wordgame."""

    def start(self, ctx: commands.Context):
        """Start a new instance of the wordgame for the given twitch channel."""

    def end(self, ctx: commands.Context):
        """End a running instance of the wordgame for the given twitch channel."""

    def show(self, ctx: commands.Context):
        """Show the secret word for the wordgame in the given twitch channel."""

    def guess(self, ctx: commands.Context):
        """Submit a guess from a chatter for the wordgame in the given twitch channel."""

    def help(self, ctx: commands.Context):
        """Print the wordgame help text in the given twitch channel."""


class Wordgame:
    """A word guessing game."""

    _data = None
    data_yaml = 'wordgame_wordlist.yml'

    def __init__(self):
        """Start a new wordgame."""
        self.secret_word = None
        self.censored_word = None
        self.guesses = []

    @classmethod
    def load_word_data(cls):
        """Load the word data from the packaged yaml file and cache it for the system."""

        if cls._data:
            logger.debug('using cached word data')
            return

        logger.debug('loading word data')
        with (resources.files(__package__) / cls.data_yaml).open('r') as wordfile:
            cls._data = yaml.load(wordfile, yaml.Loader)

    @classmethod
    @cache
    def word_categories(cls):
        """Return a list of categories the wordgame can choose a secret word from."""
        cls.load_word_data()
        return [str(key) for key in cls._data.keys() if key != 'test']

    def start(self, out_cb, category=None):
        """Start a new wordgame instance by choosing a secret and calculating a censored word."""




class OriginalWordgame(commands.Cog):
    """TwitchIO Cog that represents a hangman-ish style word guessing game for twitch chats."""

    default_description = "I'm thinking of the name of an item that you can collect in Minecraft."
    default_wordlist_yaml = 'minecraft_1.20_item_list.yml'

    def __init__(self, bot, description=None, wordlist_yaml_file=None):
        self.bot = bot
        self.description = description
        self.wordlist_yaml_file = wordlist_yaml_file
        self.wordlist = self.load_words()
        logging.info(f"Wordgame has {len(self.wordlist)} words available")

        self.game_started = False
        self.hard_mode = False
        # game lock to control access to game state like declaring a winner or starting up
        self.game_lock = threading.Lock()
        self.selected_word = None
        self.censured_word = None
        self.normalized_word = None  # selected_word but processed for easy guess checking
        # censured word lock to control access to updating the censured word
        self.censured_word_lock = threading.Lock()
        self.guesses = collections.deque()
        self.guessed_letters = collections.Counter()

    def load_words(self):
        """Load a list of words from the given yaml file containing word lists."""
        try:
            if self.wordlist_yaml_file is None:
                self.description = self.default_description
                self.wordlist_yaml_file = (resources.files(__package__) / self.default_wordlist_yaml).open('r')

            data = yaml.load(self.wordlist_yaml_file, yaml.Loader)
        finally:
            if not self.wordlist_yaml_file.closed:
                self.wordlist_yaml_file.close()

        return self.load_words_from_data(data)

    def load_words_from_data(self, data: (dict, list)):
        """Recursively parse out strings from the data object."""
        wordlist = []
        for key in data:
            value = key if isinstance(data, list) else data[key]
            if isinstance(value, (list, dict)):
                wordlist.extend(self.load_words_from_data(value))

            elif isinstance(value, str):
                wordlist.append(value)

            else:
                logging.warning(f'wordgame load words: skipping {data[key]}')

        return wordlist

    def get_word(self):
        """Get a random word with no underscores and in lower case."""
        choice = random.choice(self.wordlist).replace('_', ' ').lower()

        if not choice.isalnum():
            # spaces are allowed, but are not considered alphanumeric so loop
            # through punctuation anyways and just ignore them.
            for char in string.punctuation:
                choice = choice if char not in choice else choice.replace(char, '')

        return choice

    @commands.command()
    async def wg_get_word(self, ctx: commands.Context):
        """Get a random word and send it to chat."""
        await ctx.send(self.get_word())

    def build_censured_word(self):
        """Build a censured version of the selected word based on the guessed letters."""
        if not self.censured_word_lock.locked():
            raise MissingLockError('The build_censured_word method requires the censured_word_lock')

        self.censured_word = ''
        for char in self.selected_word:
            if self.hard_mode and char == ' ':  # preserve spaces in selected word but skip them in the censured one
                continue

            if char in string.punctuation + ' ':
                if char == ' ':
                    self.censured_word += '- '
                else:
                    self.censured_word += char + ' '

            elif char in self.guessed_letters:
                self.censured_word += char + ' '

            else:
                self.censured_word += '_ '

        logging.info(f'Starting with censured word: {self.censured_word}')

    def build_normalized_word(self):
        """Change the formatting of the selected word to make guess checking easier."""
        self.normalized_word = self.selected_word.replace(' ', '')

    def show_str(self):
        """Format a string showing what the censured word is."""
        return f'The word you are guessing is: {self.censured_word}'

    @commands.command()
    async def start(self, ctx: commands.Context):
        """Start the word game."""
        if not await self.bot.require_mod(ctx):
            return

        with self.game_lock:
            if self.game_started:
                await ctx.send(f'A game is already started! {self.show_str()}')
                return

            if 'hard' in ctx.message.content.lower():
                self.hard_mode = True

            difficulty = 'hard ' if self.hard_mode else ''
            logging.info(f'starting a new {difficulty}game')
            self.selected_word = self.get_word()
            self.build_normalized_word()

            logging.info(f'selected word {self.selected_word}')

            with self.censured_word_lock:
                self.build_censured_word()

            preamble = (f"Alrighty chat! Let's play a Wordgame. {self.description} "
                        "You can guess single letters or words. Use '?help' for a list of available game commands. "
                        "Use '?guess GUESS' or '?g GUESS' to submit a guess. "
                        "Use '?show' to see the word again and '?help' to see these commands again.")

            hard_msg = " A - (hyphen) in the secret word indicates a space. "
            if self.hard_mode:
                hard_msg = ' This is hard mode so spaces are not shown in the secret word. Good luck!! '

            word = f"Here is the word you are guessing: {self.censured_word}"

            await ctx.send(preamble + hard_msg + word)

            self.game_started = True

    @commands.command()
    async def show(self, ctx: commands.Context):
        """Send a message to chat showing what the censured word is."""
        await ctx.send(self.show_str())

    async def end_game(self, ctx: commands.Context, print_stats=True):
        """
        End the game and reset the state variables.

        Optionally send a chat message with some game statistics.
        """
        if print_stats:
            most_common_letter = self.guessed_letters.most_common(n=1)[0]
            await ctx.send(f'It took {len(self.guesses)} guesses to get the word. '
                           f'The most commonly guessed letter, {most_common_letter[0]}, '
                           f'was guessed {most_common_letter[1]} times.  GG Chat!')

        logging.info(f'Guesses: {list(self.guesses)}')
        logging.info(f'Total guesses: {len(self.guesses)}')
        self.game_started = False
        self.selected_word = None
        self.censured_word = None
        self.normalized_word = None

        self.guesses = collections.deque()
        self.guessed_letters.clear()

    @commands.command()
    async def end(self, ctx: commands.Context):
        """
        End the game and reset the state.

        Requires mod powers.
        """
        if not await self.bot.require_mod(ctx):
            return

        exit_message = "Th-th-th-that's it folks."
        if not self.game_started:
            await ctx.send(exit_message)
            return

        await ctx.send(f"{exit_message} The secret word was: {self.selected_word}")

        with self.game_lock:
            await self.end_game(ctx, print_stats=False)

    @commands.command(aliases=['g'])
    async def guess(self, ctx: commands.Context):
        """Make a guess in the word game."""
        if not self.game_started:
            await ctx.send(f"Yo {ctx.author.name}, there's no game going at the moment.")
            return

        guess = ctx.message.content[ctx.message.content.find(' '):].strip().lower()
        logging.info(f'received guess: {guess}')

        # Using a - to indicate spaces in the censured word.
        # Ignore them if people accidentally use that instead of a space
        guess = guess.replace('-', '')

        if not guess.isalnum() and any(char in guess for char in string.punctuation):
            await ctx.send(f"Sorry {ctx.author.name}, this game doesn't use punctuation in the guesses.")
            return

        if guess in self.guesses:
            await ctx.send(f'{guess} has already been guessed')
            return

        self.guesses.append(guess)

        norm_guess = guess.replace(' ', '')

        if norm_guess in self.normalized_word:
            logging.info(f'"{guess}" is in the word')
            with self.censured_word_lock:
                self.guessed_letters.update(guess)

                self.build_censured_word()

            if '_' not in self.censured_word:  # winning condition
                with self.game_lock:
                    await ctx.send(f'GG {ctx.author.name}, you cleared the blanks! The word was: {self.selected_word}')

                    await self.end_game(ctx)
                    return

            # good guess, still have blanks left to figure out
            await ctx.send(f'Great guess {ctx.author.name}! "{guess}" is in the secret word.  ' +
                           self.show_str())
            return

        # not a good guess
        negatives = ["Nerp!", "Nope, good try!", "You wish!", "Sorry", "Nuh-uh", "If only that was correct!",
                     "That would have been right if it wasn't sooooo wrong!"]
        await ctx.send(f'{random.choice(negatives)} {ctx.author.name}, "{guess}" is not in the secret word.')
        await self.show(ctx)

    @commands.command()
    async def help(self, ctx: commands.Context):
        """Send a chat message with some helpful details about how to play the wordgame."""
        await ctx.send("This is Wordgame Chatbot! Use '?guess GUESS' or '?g GUESS' to make a guess. "
                       "Use '?show' to show the secret word with the latest guesses revealed. "
                       "You can guess single letters or you can guess full words. When the secret word has been "
                       "fully revealed the game will be over. The person to guess the last few blanks is "
                       "declared the winner.")
