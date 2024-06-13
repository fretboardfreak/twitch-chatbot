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

import yaml

from twitchio.ext import commands


class Wordgame(commands.Cog):
    """TwitchIO Cog that represents a hangman-ish style word guessing game for twitch chats."""

    def __init__(self, bot, description, wordlist_yaml):
        self.bot = bot
        self.description = description
        self.wordlist_yaml_file = wordlist_yaml
        self.wordlist = self.load_words()
        logging.info("Wordgame has %s words available", len(self.wordlist))

        self.game_started = False
        # game lock to control access to game state like declaring a winner or starting up
        self.game_lock = threading.Lock()
        self.selected_word = None
        self.censured_word = None
        # censured word lock to control access to updating the
        self.censured_word_lock = threading.Lock()
        self.guesses = collections.deque()
        self.guessed_letters = collections.Counter()

    def load_words(self):
        """Load a list of words from the given yaml file containing word lists."""
        data = yaml.load(self.wordlist_yaml_file, yaml.Loader)
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
                logging.warning('wordgame load words: skipping %s', data[key])

        return wordlist

    def get_word(self):
        """Get a random word with no underscores and in lower case."""
        return random.choice(self.wordlist).replace('_', ' ').lower()

    @commands.command()
    async def wg_get_word(self, ctx: commands.Context):
        """Get a random word and send it to chat."""
        await ctx.send(self.get_word())

    def build_censured_word(self):
        """Build a censured version of the selected word based on the guessed letters."""
        self.censured_word = ''
        for char in self.selected_word:
            if char == ' ':
                continue

            if char in self.guessed_letters or char in string.punctuation:
                self.censured_word += char + ' '

            else:
                self.censured_word += '_ '

        logging.info(self.censured_word)

    @commands.command()
    async def start(self, ctx: commands.Context):
        """Start the word game."""
        if not await self.bot.require_mod(ctx):
            return

        with self.game_lock:
            if self.game_started:
                await ctx.send(f'A game is already started!  The word you are guessing is {self.censured_word}')
                return

            logging.info('starting a new game')
            self.selected_word = self.get_word()

            logging.info('selected word %s', self.selected_word)

            with self.censured_word_lock:
                self.build_censured_word()

            preamble = (f"Alrighty chat! Let's play a Wordgame. {self.description} "
                        "You can guess single letters or words. Use '?help' for a list of available game commands. "
                        "Use '?guess GUESS' or '?g GUESS' to submit a guess. "
                        f"Here is the word you are guessing: {self.censured_word}")
            await ctx.send(preamble)

            self.game_started = True

    def show_str(self):
        """Format a string showing what the censured word is."""
        return f'The word you are guessing is: {self.censured_word}'

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

        logging.info('Guesses: %s', list(self.guesses))
        logging.info('Total guesses: %s', len(self.guesses))
        self.game_started = False
        self.selected_word = None
        self.censured_word = None
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

        with self.game_lock:
            await self.end_game(ctx, print_stats=False)

        await ctx.send("Th-th-th-that's it folks.")

    @commands.command(aliases=['g'])
    async def guess(self, ctx: commands.Context):
        """Make a guess in the word game."""
        if not self.game_started:
            await ctx.send(f"Yo {ctx.author.name}, there's no game going at the moment.")
            return

        guess = ctx.message.content[ctx.message.content.find(' '):].strip().lower()
        logging.info('received guess: %s', guess)
        if guess in self.guesses:
            await ctx.send(f'{guess} has already been guessed')
            return

        self.guesses.append(guess)

        if guess in self.selected_word:
            with self.censured_word_lock:
                for char in guess:
                    self.guessed_letters.update(char)

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
        negatives = ["Nerp!", "Nope, good try!", "You wish!", "Sorry"]
        await ctx.send(f'{random.choice(negatives)} {ctx.author.name}, "{guess}" is not in the secret word.')
        await self.show(ctx)

    @commands.command()
    async def help(self, ctx: commands.Context):
        await ctx.send('help not implemented yet')
