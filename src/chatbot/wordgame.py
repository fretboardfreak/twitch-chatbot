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
import re
import string
import threading

from importlib import resources
from functools import cache
from functools import wraps

import yaml

from twitchio.ext import commands


logger = logging.getLogger(__name__)

LOGGING_LEVEL = logging.DEBUG  # change logging level here to enable/disable debug mode
logger.setLevel(LOGGING_LEVEL)

DEBUG = True if LOGGING_LEVEL <= logging.DEBUG else False


class MissingLockError(RuntimeError):
    """Used to indicate a section of code that requires a lock before running."""


class EndgameException(Exception):
    """Indicates the End Game conditions have been met."""


class WordgameUI(commands.Cog):
    """TwitchIO Cog providing a chat interface to the wordgame."""

    games = {}  # {channel name: channel wordgame, ...}

    # a bunch of short statements indicating a bad guess
    _negatives = ["Nerp!", "Nope, good try!", "You wish!", "Sorry",
                  "Nuh-uh", "If only that was correct!",
                  "That would have been right if it wasn't sooooo wrong!"]

    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        super(*args, **kwargs)

    def _show_msg(self, channel):
        """Return a string telling chat the censored word."""
        censored_word = self.games[channel].censored_word
        return f'The secret word is {censored_word}'

    commands.command()
    async def start(self, ctx: commands.Context):
        """Start a new instance of the wordgame for the given twitch channel."""

        # TODO: implement hardmode option
        # TODO: implement category option

        if not await self.bot.require_mod(ctx):
            return

        if ctx.channel.name in self.games:
            # a game is already running
            await ctx.send("Can't start a game; one is already running. "
                           + self._show_msg(ctx.channel.name))
            return

        game = Wordgame()

        game.load_word_data()

        with game.lock:
            game.choose_word()

        self.games[ctx.channel.name] = game

        preamble = ("Alrighty chat! Lets play a wordgame. I'm thinking of {self.description}."
                    "You can guess single letters or words. Use '?help' for a list of available "
                    "game commands. Use '?guess GUESS' or '?g GUESS' to submit a guess. "
                    "Use '?show' to see the word again and '?help' to see these commands again. ")
        await ctx.send(preamble + self._show_msg(ctx.channel.name))

    commands.command()
    async def end(self, ctx: commands.Context):
        """End a running instance of the wordgame for the given twitch channel."""
        if not await self.bot.require_mod(ctx):
            return

        if ctx.channel.name not in self.games:
            await ctx.send('Easy peasy boss. No game running.')
            return

        game = self.games.pop(ctx.channel.name)

        await ctx.send("Too bad we can't finish the game. The secret word was "
                       + game.secret_word)

    commands.command()
    async def show(self, ctx: commands.Context):
        """Show the secret word for the wordgame in the given twitch channel."""
        await ctx.send(f'{self._show_msg(ctx.channel.name)} and is {self.description}')

    commands.command(aliases=['g'])
    async def guess(self, ctx: commands.Context):
        """Submit a guess from a chatter for the wordgame in the given twitch channel."""
        if ctx.channel.name not in self.games:
            await ctx.send(f"Yo {ctx.author.name}, there's no game going at the moment.")
            return

        # remove the command stub from the prefix of the message
        guess = ctx.message.content[ctx.message.content.find(' '):].strip().lower()

        logger.info(f'channel {ctx.channel.name} received guess: {guess}')

        # Using a - to indicate spaces in the censored word.
        # Ignore them if people accidentally use that instead of a space
        guess = guess.replace('-', '')

        if not guess.isalnum() and any(char in guess for char in string.punctuation):
            await ctx.send(f"Sorry {ctx.author.name}, this game doesn't "
                           "use punctuation in the guesses.")
            return

        game = self.games[ctx.channel.name]

        with game.lock:
            try:
                is_new, is_good = game.guess(guess)
            except EndgameException:
                await ctx.send(f'GG {ctx.author.name}!! You cleared the blanks! The word was: '
                               + game.secret_word)
                self.games.pop(ctx.channel.name)
                return

        if not is_new:
            await ctx.send(f'Good try {ctx.author.name}. "{guess}" has already been guessed before.')
            return

        show_msg = self._show_msg(ctx.channel.name)

        if is_good:
            await ctx.send(f'Great guess {ctx.author.name}. "{guess}" is in '
                           f'the secret word. {show_msg}')
            return

        await ctx.send(f'{random.choice(self._negatives)} {ctx.author.name}, '
                       f'{guess} is not in the secret word. {show_msg}')

    commands.command()
    async def help(self, ctx: commands.Context):
        """Print the wordgame help text in the given twitch channel."""
        await ctx.send(
            "This is a Wordgame Chatbot! Use '?guess GUESS' or '?g GUESS' to make a guess. "
            "Use '?show' to show the secret word with the latest guesses revealed. "
            "You can guess single letters or you can guess full words. When the secret word has been "
            "fully revealed the game will be over. The person to guess the last few blanks is "
            "declared the winner.")


def require_lock(func):
    """Wrapper for wordgame methods to require the game lock to be held."""

    @wraps(func)
    def decorator(*args, **kwargs):
        try:
            game = args[0]
        except IndexError:
            logging.error('require_lock decorator only works on methods of the Wordgame class.')

        if not game.lock.locked():
            raise MissingLockError()

        return func(*args, **kwargs)

    return decorator


class Wordgame:
    """A word guessing game."""

    # TODO: implement hard mode

    data_yaml = (resources.files(__package__) / 'wordgame_wordlist.yml')
    _data = None
    _categories = None

    def __init__(self):
        """Prepare a new wordgame."""
        self.secret_word = None
        self.secret_word_category = None
        self.normalized_word = None
        self.censored_word = None
        self.guesses = set()
        self.lock = threading.Lock()

        self.load_word_data()  # precache data

    @classmethod
    def load_word_data(cls):
        """Load the word data from the packaged yaml file and cache it for the system."""

        if cls._data:
            logger.debug('using cached word data')
            return

        logger.debug('loading word data')
        cls._categories = None  # ensure other caches are cleared
        with cls.data_yaml.open('r') as wordfile:
            cls._data = yaml.load(wordfile, yaml.Loader)

    @classmethod
    def word_categories(cls):
        """Return a list of categories the wordgame can choose a secret word from."""
        cls.load_word_data()

        if cls._categories:
            return cls._categories

        filter = '' if DEBUG else 'test'

        cls._categories = [str(key) for key in cls._data.keys() if key != filter]
        return cls._categories

    @classmethod
    def clear_caches(cls):
        """Clear out the data caches."""
        cls._data = None
        cls._categories = None

    @property
    def description(self):
        return self._data[self.secret_word_category]['description']

    @require_lock
    def choose_word(self, category=None):
        """Choose a secret word from the given category."""
        if DEBUG:
            categories = self.word_categories()
        else:
            categories = [cat for cat in self.word_categories() if cat != 'test']

        logger.debug(f'choose_word: categories= {categories}')

        if not category:
            self.secret_word_category = random.choice(categories)

        elif category in categories:
            self.secret_word_category = category

        else:
            return False

        self.secret_word = random.choice(self._data[self.secret_word_category]['words']).lower()
        logger.debug(f'choose_word: category= {self.secret_word_category} word= {self.secret_word}')

        self.build_censored_word()

        return True

    @require_lock
    def build_censored_word(self):
        """Build the censored word from the secret word and the guesses."""
        if not self.secret_word:
            self.censored_word = None
            return

        # normalize the secret word. lowercase and remove punctuation
        # for censored_wip, start with all blanks, "_", but replace spaces with "-"
        normalized_word = ''
        censored_wip = ''
        for char in self.secret_word.lower():
            if char == ' ':
                normalized_word += char
                censored_wip += '-'
                continue

            if char not in string.punctuation:
                normalized_word += char
                censored_wip += '_'

        if not self.normalized_word or normalized_word != self.normalized_word:
            self.normalized_word = normalized_word

        logging.debug(f'secret {self.secret_word} | normal {self.normalized_word} | wip {censored_wip}')

        # process guesses
        for guess in self.guesses:
            logging.debug(f'processing guess {guess}')
            for match in re.finditer(guess, self.normalized_word):
                for index in range(*match.span()):
                    if censored_wip[index] == '_':
                        censored_wip = (censored_wip[0:index]
                                        + self.normalized_word[index]
                                        + censored_wip[index+1:])

        self.censored_word = ' '.join(censored_wip)
        logging.debug(f'final censored word: {self.censored_word}')

    @require_lock
    def guess(self, guess):
        """Submit a guess to the wordgame.

        Returns: (is_new, is_good)
        """
        # normalize the guess
        for punc in string.punctuation:
            if punc in guess:
                guess = guess.replace(punc, '')

        is_new = guess not in self.guesses
        is_good = guess in self.normalized_word

        # self.guesses is a set so no pre-check necessary
        self.guesses.add(guess)

        # rebuild censored word only if new characters are found
        if is_good and is_new:
            self.build_censored_word()

        # check endgame status
        if "_" not in self.censored_word:
            raise EndgameException()

        return is_new, is_good
