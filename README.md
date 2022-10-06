# Assassins' Network Scripts

Welcome to the Assassins' Network Scripts repository.
This includes all the backend scripts used on the Network, including screenshot OCRing, MMR-based team generator, Twitter posting, and much more.

The scripts can all be ran via a Discord bot, allowing users with the appropriate role to update the database without SSH access, and also giving all users access to the bot's OCR tool.

## Prerequisites 
Some housekeeping things to do before you're able to use this bot completely. Make sure that you have:
- [Python 3.X](https://www.python.org/downloads/)
- [Flask-MongoDB](https://flask-pymongo.readthedocs.io/en/latest/)
- [VapourSynth](http://www.vapoursynth.com/doc/)
- [AWarpSharp2 plugin for VapourSynth](https://github.com/dubhater/vapoursynth-awarpsharp2)
- [DiscordPy](https://pypi.org/project/discord.py/)
- [Apscheduler](https://apscheduler.readthedocs.io/en/stable/)
- [Telegram](https://python-telegram-bot.org/)
- [Tweepy](https://pypi.org/project/tweepy)
- [Pandas](https://pandas.pydata.org)
- [NumPy](https://numpy.org)

## Installation
- `git clone https://github.com/ACBMP/Scripts.git`
- Open a text editor and follow these steps `File -> New -> Import Module`
- [Making a Discord bot](https://discord.com/developers/docs/intro)

## Uploading Matches
- In order to upload match data to the DB, please input relevant information according to the format available on GitHub.
- **Do not return** ("Enter" button) after entering the last line. 
- Each entry should be treated as a line of text.
- Once the `matches.txt` file contains the data, run the `read_and_update.py` script to upload them to the DB.
- All new data entries will have a field `new` set to the boolean value `true`. 
- ***REMEMBER***: an **empty** file should consist of a single 'hash' (#) character and nothing else. 
- This is also how the file will look like after updating, all text input will be wiped. 
- A file with entries **SHOULD NOT** contain the #.
- The `read_and_update.py` script will update the Elo ratings as well.
- Run the script using [Python 3.X](https://www.python.org/downloads/).

## Bots

### Discord

The Discord bot can be used for general maintenance, such as adding matches, updating leaderboards, inserting players, organizing lobbies etc.

# Authors
- [zawsze-razem](https://github.com/zawsze-razem)
- [munnich](https://github.com/munnich)
- [walletfats](https://github.com/walletfats)

# Contributing

When contributing to this repository, please first discuss the change you wish to make via issue,
email, or any other method with the owners of this repository before making a change. 

Please note we have a code of conduct, please follow it in all your interactions with the project.

## Pull Request Process

1. Ensure any install or build dependencies are removed before the end of the layer when doing a 
   build.
2. Update the README.md with details of changes to the interface, this includes new environment 
   variables, exposed ports, useful file locations and container parameters.
3. You may merge the Pull Request in once you have the sign-off of two other developers, or if you 
   do not have permission to do that, you may request the second reviewer to merge it for you.

## Code of Conduct

### Our Pledge

In the interest of fostering an open and welcoming environment, we as
contributors and maintainers pledge to making participation in our project and
our community a harassment-free experience for everyone, regardless of age, body
size, disability, ethnicity, gender identity and expression, level of experience,
nationality, personal appearance, race, religion, or sexual identity and
orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment
include:

* Using welcoming and inclusive language
* Being respectful of differing viewpoints and experiences
* Gracefully accepting constructive criticism
* Focusing on what is best for the community
* Showing empathy towards other community members
