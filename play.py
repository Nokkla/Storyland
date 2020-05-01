#!/usr/bin/env python3
import os
import random
import sys
import time
import argparse

from generator.gpt2.gpt2_generator import *
from story import grammars
from story.story_manager import *
from story.utils import *

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

parser = argparse.ArgumentParser("Play Storyland")
parser.add_argument(
    "--cpu",
    action="store_true",
    help="Force using CPU instead of GPU."
)


def splash():
    print("0) New Game\n1) Load Game\n")
    choice = get_num_options(2)

    if choice == 1:
        return "load"
    else:
        return "new"



def select_game():
    with open(YAML_FILE, "r") as stream:
        data = yaml.safe_load(stream)

    setting = "story"
    character_key = "player"

    name = input("\nWhat is your name? ")
    setting_description = data["settings"][setting]["description"]
    character = data["settings"][setting]["characters"][character_key]

    return setting, character_key, name, character, setting_description

def get_curated_exposition(
    setting_key, character_key, name, character, setting_description
):
    name_token = "<NAME>"
    try:
        context = grammars.generate(setting_key, character_key, "context") + "\n\n"
        context = context.replace(name_token, name)
        prompt = grammars.generate(setting_key, character_key, "prompt")
        prompt = prompt.replace(name_token, name)
    except:
        context = (
            "You are "
            + name
            + ", a "
            + character_key
            + " "
            + setting_description
            + "You have a "
            + character["item1"]
            + " and a "
            + character["item2"]
            + ". "
        )
        prompt_num = np.random.randint(0, len(character["prompts"]))
        prompt = character["prompts"][prompt_num]

    return context, prompt


def instructions():
    text = "\nStorylandland Instructions:"
    text += '\n To perform an action: write actions starting with a verb. Ex: "eat the pizza" or "pet the cat."'
    text += '\n To speak: enter "say" followed by the words you want to say. Ex: "say hello " or "say I like chocolate" '
    text += '\n'
    text += "\n\nThe following commands can be used at any time during the game: "
    text += '\n  "/revert"   Reverts the last action allowing you to pick a different action.'
    text += '\n  "/quit"     Quits the game and saves'
    text += '\n  "/reset"    Starts a new game and saves your current one'
    text += '\n  "/restart"  Starts the game from beginning with same settings'
    text += '\n  "/save"     Makes a new save of your game and gives you the save ID'
    text += '\n  "/load"     Asks for a save ID and loads the game if the ID is valid'
    text += '\n  "/print"    Prints a transcript of your adventure (without extra newline formatting)'
    text += '\n  "/help"     Prints these instructions again'
    return text


def playStoryland(args):
    """
    Entry/main function for starting Storyland

    Arguments:
        args (namespace): Arguments returned by the
                          ArgumentParser
    """
    upload_story = True

    print("\nInitializing Storyland! (This might take a few minutes)\n")
    generator = GPT2Generator(force_cpu=args.cpu)
    story_manager = UnconstrainedStoryManager(generator)
    print("\n")

    with open("opening.txt", "r", encoding="utf-8") as file:
        starter = file.read()
    print(starter)

    while True:
        if story_manager.story != None:
            story_manager.story = None

        while story_manager.story is None:
            print("\n\n")
            splash_choice = splash()

            if splash_choice == "new":
                print("\n\n")
                (
                    setting_key,
                    character_key,
                    name,
                    character,
                    setting_description,
                ) = select_game()

                # if setting_key == "custom":
                #       context, prompt = get_custom_prompt()

                #else:
                context, prompt = get_curated_exposition(
                    setting_key, character_key, name, character, setting_description
                )

                console_print(instructions())
                print("\nGenerating story...")

                result = story_manager.start_new_story(
                    prompt, context=context, upload_story=upload_story
                )
                print("\n")
                console_print(result)

            else:
                load_ID = input("What is the ID of the saved game? ")
                result = story_manager.load_new_story(
                    load_ID, upload_story=upload_story
                )
                print("\nLoading Game...\n")
                console_print(result)

        while True:
            sys.stdin.flush()
            action = input("> ").strip()
            if len(action) > 0 and action[0] == "/":
                split = action[1:].split(" ")  # removes preceding slash
                command = split[0].lower()
                args = split[1:]
                if command == "reset":
                    story_manager.story.get_rating()
                    break

                elif command == "restart":
                    story_manager.story.actions = []
                    story_manager.story.results = []
                    console_print("Game restarted.")
                    console_print(story_manager.story.story_start)
                    continue

                elif command == "quit":
                    story_manager.story.get_rating()
                    exit()

                elif command == "help":
                    console_print(instructions())

                elif command == "save":
                    if upload_story:
                        id = story_manager.story.save_to_storage()
                        console_print("Game saved.")
                        console_print(
                            "To load the game, type 'load' and enter the "
                            "following ID: {}".format(id)
                        )
                    else:
                        console_print("Saving has been turned off. Cannot save.")

                elif command == "load":
                    if len(args) == 0:
                        load_ID = input("What is the ID of the saved game?")
                    else:
                        load_ID = args[0]
                    result = story_manager.story.load_from_storage(load_ID)
                    console_print("\nLoading Game...\n")
                    console_print(result)

                elif command == "print":
                    print("\nPRINTING\n")
                    print(str(story_manager.story))

                elif command == "revert":
                    if len(story_manager.story.actions) == 0:
                        console_print("You can't go back any farther. ")
                        continue

                    story_manager.story.actions = story_manager.story.actions[:-1]
                    story_manager.story.results = story_manager.story.results[:-1]
                    console_print("Last action reverted. ")
                    if len(story_manager.story.results) > 0:
                        console_print(story_manager.story.results[-1])
                    else:
                        console_print(story_manager.story.story_start)
                    continue

                else:
                    console_print("Unknown command: {}".format(command))

            else:
                if action == "":
                    action = ""
                    result = story_manager.act(action)
                    console_print(result)

                elif action[0] == '"':
                    action = "You say " + action

                else:
                    action = action.strip()

                    if "you" not in action[:6].lower() and "I" not in action[:6]:
                        action = action[0].lower() + action[1:]
                        action = "You " + action

                    if action[-1] not in [".", "?", "!"]:
                        action = action + "."

                    action = first_to_second_person(action)

                    action = "\n> " + action + "\n"

                result = "\n" + story_manager.act(action)
                if len(story_manager.story.results) >= 2:
                    similarity = get_similarity(
                        story_manager.story.results[-1], story_manager.story.results[-2]
                    )
                    if similarity > 0.9:
                        story_manager.story.actions = story_manager.story.actions[:-1]
                        story_manager.story.results = story_manager.story.results[:-1]
                        console_print(
                            "Woops that action caused the model to start looping. Try a different action to prevent that."
                        )
                        continue

                if player_won(result):
                    console_print(result + "\n CONGRATS YOU WIN")
                    story_manager.story.get_rating()
                    break
                elif player_died(result):
                    console_print(result)
                    console_print("YOU LOST. GAME OVER")
                    console_print("\nOptions:")
                    console_print("0) Start a new game")
                    console_print(
                        "1) \"I'm not dead yet!\""
                    )
                    console_print("Which do you choose? ")
                    choice = get_num_options(2)
                    if choice == 0:
                        story_manager.story.get_rating()
                        break
                    else:
                        console_print("Sorry about that...where were we?")
                        console_print(result)

                else:
                    console_print(result)


if __name__ == "__main__":
    args = parser.parse_args()
    playStoryland(args)
