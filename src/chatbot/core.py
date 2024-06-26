"""The core twich chatbot logic."""

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

import logging
import requests

from twitchio.ext import commands


class BotError(Exception):
    """Represents an error raised by the chatbot."""


class Bot(commands.Bot):
    """The core twitch chatbot object."""

    command_prefix = '?'

    def __init__(self, token, channels, moderators):
        """Initialize the bot object."""
        if not channels:
            raise BotError('At least one twitch channel to join must be specified.')

        super().__init__(token=token, prefix=self.command_prefix, initial_channels=channels)

        self.moderators = moderators if moderators else []

    async def event_ready(self):
        """Notify console when bot is logged in and ready to chat and use commands."""
        logging.info(f'Logged in as | {self.nick}')
        logging.debug(f'User id is | {self.user_id}')

    async def event_message(self, message):
        """Watch every message sent in the joined chats."""
        if message.echo:  # Messages with echo set to True are messages sent by the bot.
            return

        if not message.content.startswith(self.command_prefix):
            logging.info(f'{message.channel.name}, {message.author.name}, {message.content}')

        await self.handle_commands(message)

    async def require_mod(self, ctx: commands.Context):
        """Helper method for commands that require a moderator to run them."""

        logging.info(f"user {ctx.author.name}: mod {ctx.author.is_mod}, "
                     f"broadcaster {ctx.author.is_broadcaster}, bot_mod {ctx.author.name in self.moderators}")

        if ctx.author.is_mod or ctx.author.is_broadcaster or ctx.author.name in self.moderators:
            return True

        await ctx.send(f'Nice try {ctx.author.name}... suckah!')
        return False

    @commands.command()
    async def hello(self, ctx: commands.Context):
        """Test command, "hello" to show the bot is working."""
        await ctx.send(f'Hello {ctx.author.name}!')

    @commands.command()
    async def joke(self, ctx: commands.Context):
        """Request a joke from icanhazdadjoke.com and send to chat."""
        response = requests.get('https://icanhazdadjoke.com/', headers={'Accept': "application/json"}, timeout=30)
        if not response.ok:
            await ctx.send('Failed to get a joke.  Contact fret :( ')
            return

        json_data = response.json()
        await ctx.send(json_data['joke'])
