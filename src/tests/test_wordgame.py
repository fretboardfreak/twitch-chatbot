"""Tests for the wordgame."""

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

# ignore some typical style issues pylint finds with common pytest structure
# pylint: disable=protected-access, unused-argument, redefined-outer-name
# pylint: disable=too-many-arguments, too-many-positional-arguments

import pytest

from chatbot import wordgame


wordgame.DEBUG = True


@pytest.fixture
def cleanup():
    """Reset any class level state after each test."""
    yield
    wordgame.DEBUG = True
    wordgame.Wordgame.clear_caches()


def test_load_data(cleanup):
    """Test the yaml data loading mechanism and caching."""
    wordgame.Wordgame._data = None
    assert wordgame.Wordgame._data is None
    wordgame.Wordgame.load_word_data()
    assert wordgame.Wordgame._data is not None

    # show loading with cache
    id1 = id(wordgame.Wordgame._data)
    wordgame.Wordgame.load_word_data()
    id2 = id(wordgame.Wordgame._data)
    assert id1 == id2


@pytest.mark.parametrize('debug', [(False), (True)])
def test_categories(debug, cleanup):
    """Verify the list of word categories works as expected."""
    wordgame.Wordgame.load_word_data()
    assert "test" in wordgame.Wordgame._data

    wordgame.DEBUG = debug
    categories = wordgame.Wordgame.word_categories()
    assert isinstance(categories, list)
    assert isinstance(categories[0], str)
    if debug:
        assert "test" in categories
    else:
        assert "test" not in categories


@pytest.mark.parametrize('category', [(None), ('test')])
def test_choose_word(category, cleanup):
    """Test the choose word method sets state as expected."""
    instance = wordgame.Wordgame()
    assert instance.secret_word is None and instance.secret_word_category is None

    with instance.lock:
        success = instance.choose_word(category)

    assert success
    assert isinstance(instance.secret_word, str) and instance.secret_word
    if category:
        assert (isinstance(instance.secret_word_category, str)
                and instance.secret_word_category == category)

    else:
        assert (isinstance(instance.secret_word_category, str)
                and instance.secret_word_category)

def test_clear_caches(cleanup):
    """Ensure clearing caches actually removes cached state."""
    wordgame.Wordgame.word_categories()
    assert wordgame.Wordgame._data is not None and wordgame.Wordgame._categories is not None

    wordgame.Wordgame.clear_caches()
    assert wordgame.Wordgame._data is None and wordgame.Wordgame._categories is None

@pytest.mark.parametrize('secret_word,guesses,expected_censored',
                         [('foo', {}, '_ _ _'),
                          ('Foo', {'f'}, 'f _ _'),
                          ('foo', {'o'}, '_ o o'),
                          ('tetheh', {'th'}, '_ _ t h _ _'),
                          ('foo bar baz', {'o', 'a'}, '_ o o - _ a _ - _ a _'),
                          ('Pun*ct#ua(tioN', {}, '_ _ _ _ _ _ _ _ _ _ _'),
                          ])
def test_build_censored_word(secret_word, guesses, expected_censored, cleanup):
    """Verify the algorithm for creating the censored word."""
    instance = wordgame.Wordgame()

    instance.secret_word = secret_word
    instance.guesses = guesses

    with instance.lock:
        instance.build_censored_word()

    assert instance.censored_word == expected_censored


@pytest.mark.parametrize('secret_word,guesses,expected_censored,is_new,is_good',
                         [('foobar', ['o'], '_ o o _ _ _', True, True),
                          ('foobar', ['o', 'o'], '_ o o _ _ _', False, True),
                          ('foobar', ['x'], '_ _ _ _ _ _', True, False),
                          ('foo bar', [' '], '_ _ _ - _ _ _', True, True),
                          ])
def test_guess(secret_word, guesses, expected_censored, is_new, is_good, cleanup):
    """Verify that guesses are handled and applied as expected."""
    instance = wordgame.Wordgame()

    instance.secret_word = secret_word

    with instance.lock:
        instance.build_censored_word()

        for guess in guesses:
            instance.guess(guess)

    assert instance.censored_word == expected_censored


def test_endgame(cleanup):
    """Test the end game trigger."""
    instance = wordgame.Wordgame()
    instance.secret_word = 'secret word'

    with instance.lock:
        instance.build_censored_word()
        instance.guess('secret')

        with pytest.raises(wordgame.EndgameException):
            instance.guess('word')
