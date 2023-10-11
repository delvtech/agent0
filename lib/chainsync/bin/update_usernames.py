"""Script to update database address to username to user tables to this config.
This script is meant to run once at docker initialization.
The script can then be ran at any time to update the database in the case of
e.g., new wallets being added.
"""
import logging

from chainsync.db.base import add_addr_to_username, add_username_to_user, initialize_session

# Force row updates if key conflicts
FORCE_UPDATE = False

# Dictionary mapping from the public wallet address to a username
addr_to_username = {
    "0x004dfC2dBA6573fa4dFb1E86e3723e1070C0CfdE": "Charles St. Louis (click)",
    "0x005182C62DA59Ff202D53d6E42Cef6585eBF9617": "Alim Khamisa (click)",
    "0x005BB73FddB8CE049eE366b50d2f48763E9Dc0De": "Danny Delott (click)",
    "0x0065291E64E40FF740aE833BE2F68F536A742b70": "Gregory Lisa (click)",
    "0x0076b154e60BF0E9088FcebAAbd4A778deC5ce2c": "Jonny Rhea (click)",
    "0x00860d89A40a5B4835a3d498fC1052De04996de6": "Matt Brown (click)",
    "0x00905A77Dc202e618d15d1a04Bc340820F99d7C4": "Giovanni Effio (click)",
    "0x009ef846DcbaA903464635B0dF2574CBEE66caDd": "Mihai Cosma (click)",
    "0x00D5E029aFCE62738fa01EdCA21c9A4bAeabd434": "Ryan Goree (click)",
    "0x020A6F562884395A7dA2be0b607Bf824546699e2": "Alex Towle (click)",
    "0x020a898437E9c9DCdF3c2ffdDB94E759C0DAdFB6": "Adelina Ruffolo (click)",
    "0x020b42c1E3665d14275E2823bCef737015c7f787": "Jacob Arruda (click)",
    "0x02147558D39cE51e19de3A2E1e5b7c8ff2778829": "Dylan Paiton (click)",
    "0x021f1Bbd2Ec870FB150bBCAdaaA1F85DFd72407C": "Sheng Lundquist (click)",
    "0x02237E07b7Ac07A17E1bdEc720722cb568f22840": "ControlC Schmidt (click)",
    "0x022ca016Dc7af612e9A8c5c0e344585De53E9667": "George Towle (click)",
    "0x0235037B42b4c0575c2575D50D700dD558098b78": "Jack Burrus (click)",
    "0x0238811B058bA876Ae5F79cFbCAcCfA1c7e67879": "Jordan J (click)",
}

# Maps all usernames to a single user
username_to_user = {
    "Charles St. Louis (click)": "Charles St. Louis",
    "Alim Khamisa (click)": "Alim Khamisa",
    "Danny Delott (click)": "Danny Delott",
    "Gregory Lisa (click)": "Gregory Lisa",
    "Jonny Rhea (click)": "Jonny Rhea",
    "Matt Brown (click)": "Matt Brown",
    "Giovanni Effio (click)": "Giovanni Effio",
    "Mihai Cosma (click)": "Mihai Cosma",
    "Ryan Goree (click)": "Ryan Goree",
    "Alex Towle (click)": "Alex Towle",
    "Adelina Ruffolo (click)": "Adelina Ruffolo",
    "Jacob Arruda (click)": "Jacob Arruda",
    "Dylan Paiton (click)": "Dylan Paiton",
    "Sheng Lundquist (click)": "Sheng Lundquist",
    "ControlC Schmidt (click)": "ControlC Schmidt",
    "George Towle (click)": "George Towle",
    "Jack Burrus (click)": "Jack Burrus",
    "Jordan J (click)": "Jordan J",
    # Bot accounts
    # NOTE register username from bots automatically appends " (bots)" to the username
    "slundquist (bots)": "Sheng Lundquist",
}

# Get session object
# This reads the .env file for database credentials
db_session = initialize_session()

# Add to database
for addr, username in addr_to_username.items():
    logging.info("Registering address %s to username %s", addr, username)
    add_addr_to_username(username=username, addresses=addr, session=db_session, force_update=FORCE_UPDATE)

# Add to database
for username, user in addr_to_username.items():
    logging.info("Registering username %s to user %s", username, user)
    add_username_to_user(user=user, username=username, session=db_session, force_update=FORCE_UPDATE)
