"""A Pokedex for all chat's pokemon reference needs."""

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
import random

from dataclasses import dataclass

import requests

from twitchio.ext import commands


class APIError(Exception):
    """Indicates an error using the pokemon API."""


@dataclass
class Pokemon:
    """The details of a pokemon from the pokedex."""

    id: int
    name: str
    height: int
    weight: float
    types: list
    stats: list
    color: str
    shape: str
    genus: str
    habitat: str
    flavor_texts: list

    def __str__(self):
        """Format a pokedex description for this pokemon."""
        flavor_text = random.choice(self.flavor_texts).replace('\n', ' ')
        return (f'[Pokedex Entry #{self.id}] {self.name.title()}: Height {self.height}cm, '
                f'Weight {self.weight}kg, Type {" ".join(self.types)}. '
                f'A {self.color} {self.shape} {self.genus} that lives in '
                f'{self.habitat}. {flavor_text} {", ".join(self.stats)}')


class Pokedex(commands.Cog):
    """A pokedex tool that chat can use to query info about pokemon."""

    api_url = 'https://pokeapi.co/api/v2'

    # main endpoint
    pokemon = api_url + '/pokemon'

    # url parameters
    limit = '?limit={}'

    timeout = 10
    canned_error_message = "Failed to query Pokemon API. Please complain to fret :)"
    logging_error_message = 'Failed Pokemon API query: status {status} : {text}'

    def __init__(self):
        self.pokemon_count = self.get_number_of_pokemon()
        logging.info(f'There are {self.pokemon_count} pokemon available to query.')

        self._cache = {}  # id: Pokemon
        self._name_to_id = {}  # name: id

    def get_number_of_pokemon(self):
        """Query the pokemon endpoint to find the number of available pokemon."""
        response = requests.get(self.pokemon + self.limit.format(1), timeout=self.timeout)
        if not response.ok:
            err_msg = self.logging_error_message.format(status=response.status_code, text=response.text)
            logging.error(err_msg)
            raise APIError(err_msg)

        return response.json()['count']

    def get_species_info(self, url):
        """Retrieve some species information about a pokemon."""
        species_response = requests.get(url, timeout=self.timeout)

        if not species_response.ok:
            logging.error(self.logging_error_message.format(status=species_response.status_code,
                                                            text=species_response.text))
            raise APIError()

        species_data = species_response.json()

        color = species_data['color']['name']
        shape = species_data['shape']['name']
        if species_data['habitat'] is None:
            habitat = 'unknown areas'
        else:
            habitat = species_data['habitat']['name']

        stub = '{} (description from: {})'
        flavor_texts = []
        for data in species_data['flavor_text_entries']:
            if data['language']['name'] != 'en':
                continue
            flavor_texts.append(stub.format(data['flavor_text'], data['version']['name']))

        for genus_data in species_data['genera']:
            if genus_data['language']['name'] != 'en':
                continue
            genus = genus_data['genus']

        return color, shape, genus, habitat, flavor_texts

    def get_pokemon_info(self, pokemon):
        """Retrieve some information about a pokemon."""
        core_response = requests.get(self.pokemon + '/' + str(pokemon), timeout=self.timeout)

        if not core_response.ok:
            logging.error(self.logging_error_message.format(status=core_response.status_code,
                                                            text=core_response.text))
            raise APIError()

        core_data = core_response.json()
        pokedex_id = core_data['id']
        name = core_data['name']
        height = core_data['height'] * 10  # data in decimeters, x10 for centimeters
        weight = core_data['weight'] / 10.0  # data in hectogram, /10 for kilograms
        types = [obj['type']['name'] for obj in core_data['types']]
        stats = [f'{obj["stat"]["name"]}: {obj["base_stat"]}' for obj in core_data['stats']
                 if 'special' not in obj['stat']['name']]

        color, shape, genus, habitat, flavor_texts = self.get_species_info(core_data['species']['url'])

        return Pokemon(pokedex_id, name, height, weight, types, stats, color, shape, genus, habitat, flavor_texts)

    @commands.command(aliases=['p'])
    async def pokedex(self, ctx: commands.Context):
        """
        Send chat info about the requested pokemon.

        Choose a random pokemon if one is not requested.
        """
        if ' ' in ctx.message.content:
            pokemon_request = ctx.message.content[ctx.message.content.find(' '):].strip().lower()
            if '/' in pokemon_request:
                await ctx.send('Error: pokemon names cannot include characters like "/"')
                return

            logging.info(f'Looking up requested pokemon: {pokemon_request}')

        else:
            pokemon_request = random.randint(1, self.pokemon_count)
            logging.info(f'Looking up random pokemon: {pokemon_request}')

        # check cache for pokemon_request
        if pokemon_request in self._cache:
            pokemon = self._cache[pokemon_request]

        elif pokemon_request in self._name_to_id:
            pokemon = self._cache[self._name_to_id[pokemon_request]]

        else:
            try:
                pokemon = self.get_pokemon_info(pokemon_request)

            except APIError:
                await ctx.send(self.canned_error_message)
                return

            self._cache[pokemon.id] = pokemon
            self._name_to_id[pokemon.name] = pokemon.id

        await ctx.send(str(pokemon))
