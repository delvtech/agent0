"""Script to update database address to username to user tables to this config.
This script is meant to run once at docker initialization.
The script can then be ran at any time to update the database in the case of
e.g., new wallets being added.
"""

import logging

from agent0.chainsync.db.base import add_addr_to_username, initialize_session
from agent0.hyperlogs import setup_logging

# Force row updates if key conflicts
FORCE_UPDATE = False

# Dictionary mapping from the public wallet address to a username
addr_to_username = {
    "0x004dfC2dBA6573fa4dFb1E86e3723e1070C0CfdE": "Charles St. Louis",
    "0x005182C62DA59Ff202D53d6E42Cef6585eBF9617": "Alim Khamisa",
    "0x005BB73FddB8CE049eE366b50d2f48763E9Dc0De": "Danny Delott",
    "0x0065291E64E40FF740aE833BE2F68F536A742b70": "Gregory Lisa",
    "0x0076b154e60BF0E9088FcebAAbd4A778deC5ce2c": "Jonny Rhea",
    "0x00860d89A40a5B4835a3d498fC1052De04996de6": "Matt Brown",
    "0x00905A77Dc202e618d15d1a04Bc340820F99d7C4": "Giovanni Effio",
    "0x009ef846DcbaA903464635B0dF2574CBEE66caDd": "Mihai Cosma",
    "0x00D5E029aFCE62738fa01EdCA21c9A4bAeabd434": "Ryan Goree",
    "0x020A6F562884395A7dA2be0b607Bf824546699e2": "Alex Towle",
    "0x020a898437E9c9DCdF3c2ffdDB94E759C0DAdFB6": "Adelina Ruffolo",
    "0x020b42c1E3665d14275E2823bCef737015c7f787": "Jacob Arruda",
    "0x02147558D39cE51e19de3A2E1e5b7c8ff2778829": "Dylan Paiton",
    "0x021f1Bbd2Ec870FB150bBCAdaaA1F85DFd72407C": "Sheng Lundquist",
    "0x02237E07b7Ac07A17E1bdEc720722cb568f22840": "ControlC Schmidt",
    "0x022ca016Dc7af612e9A8c5c0e344585De53E9667": "George Towle",
    "0x0235037B42b4c0575c2575D50D700dD558098b78": "Jack Burrus",
    "0x0238811B058bA876Ae5F79cFbCAcCfA1c7e67879": "Jordan J",
    "0x024c641B5F6C32a492B1520FE76251701b1d1AA7": "Phil (Flowcarbon)",
    "0x025d59829B0a2470C8175ac7F501a53E94D223Ac": "Nirvaan (Flowcarbon)",
    "0x026143Ec99d915019B8666cb2Bf2ebA8261c5D46": "Chp (Flowcarbon)",
    "0x026483eC0deBbc4252372eEab8a53071ba83ffAF": "Isaac (Flowcarbon)",
    "0x2C4F64C3BE604E7Ae00fd822CE5FC3131F30C3F0": "Nate (Number Group)",
    "0x027de2B3095181C1B44ba401d0D8341dAAcA489E": "Zak cole (Number Group)",
    "0x029154117EA657009a01a9778be20efDA203fA95": "Drew O (Number Group)",
    "0x0295aCB19B11ef429298C78d92Ec20A70E7da472": "Nate 2 (Number Group)",
    "0x029907c0c7b63dae567C45Dea77e804C0F567df0": "Chris (Summer fi)",
    "0x029cE100BC18Ed5D78b1359b114564F25Ef87673": "Luciano (Summer fi)",
    "0x02A79FFab3b447a243327373e2958af2d6305BC7": "Linda (Scalar Capital)",
    "0x02B73Bb05Af09Ed35F327c9711dA676AED1e5512": "Sam (Phoenix Labs)",
    "0x02BF9a114C29ed12d885f963593fcD2e1505B460": "Lucas (Phoenix Labs)",
    "0x02C0eD0DF2142459Ed220d3860c2a6AffB51cd3D": "Christian Cerullo",
    "0x02C96EF2c1dFE09223a0549cCbA9955307378AfC": "Jordan Jackson",
    "0x02Ca782d6Ff1dF9ED70eCA5F4860C1A0f86F4e5b": "Luke (Polychain)",
    "0x02Ce145B96510ECa815C5ddb8C69D0304AF258AC": "Sven (Polychain)",
    "0x02DFF5EF42EF7ba40Bdf049059DdC147eCe27233": "Elazzarin (a16Z)",
    "0x02E1769501e5491612bB37c45698eA4dC0D5d72b": "Joel (Placeholder)",
    "0x02F208E514bDAee6F0412D86628074F14Ca23bA8": "Min (Ethereal)",
    "0x02FEf166ac43e5a81bB0e0D56cC58CeA4B686fF1": "Praneeth (Ethereal)",
    "0x02Faff249A85f304C4d4f4CDD133B6aebE543eAA": "Robert Drost (Ethereal)",
    "0x02aDc6C8E017A5e6465C22eBDE4DcF7a3C477630": "Eeshaan (Ethereal)",
    "0x02b9B98cE712b0d4259008388c04a11614Dbcd17": "Boris (Republiccapital)",
    "0x02bd11C612a32dB2Ca0dA0Fdb0bbe3Ee0E9C203f": "Shawn (Republiccapital)",
    "0x02d3537230De86d5090d2Bae4D8084fBCdf5FbC1": "Kartik (Acapital)",
    "0x02dE93FAdf8626d29fbAc241676FbA3771A1f623": "Camron (Rarestone)",
    "0x02e3E392C81abaa7e7b31E87E12038BFBe89c6D5": "Connor Sumners (Femboy Capital)",
    "0x03086522fAA9685c1322905D1CA33af4022B4fcd": "Tilt (Yunt)",
    "0x0318Eb61C45F30cB2D5E3371dF72851C638aA4Cb": "0xbewdev (Yunt)",
    "0x032281f3501cFdD61e95BFbED738990f4D866cb9": "Brian (Universal Defi Holdings)",
    "0x032DcE137A5d24cAebB4303c4bbA469db3dB0197": "Torben (Universal Defi Holdings)",
    "0x0330af2D8d07F44C6e6cf5148431a09a67Cb5D6f": "Katie (Universal Defi Holdings)",
    "0x033355c4Fa83B52C81061c93eb0E7F156dd740df": "Stevenb (Universal Defi Holdings)",
    "0x033f7c8c4997d8f7A046434320424E1E7491AF35": "Am (P2P)",
    "0x034076c7f368D81b8afA74219A4226017Fe7b251": "Sergei.m (P2P)",
    "0x03408bed71777fC8623055941C2E4Dda597D2776": "K (P2P)",
    "0x0346caE47Ce48EF92b2b631655562Ef9900Ae493": "Santiago Santos",
    "0x034870eD5321982a1c458637f046F945F0154348": "Anthony Sassano",
    "0x0352e3149cCE05fE6eB7Dfd3155e3A9443e75a54": "David Hoffman",
    "0x0353Be3a5131504434C9b63E4f1B13339d777Be3": "Dean Eiganmann",
    "0x035760D400571770ae8076deFaf237a1F049d1C0": "Darren Lau",
    "0x0369F268EB4Dc1fC0e2846092A5D25aa331F57Ea": "Daryl Lau",
    "0x03719fa1Bc3e0aAE1A998Fca2fd619D2f16b6aBB": "Rune Christensen",
    "0x0371af19efD20986605cC7dbb4bb7E69FecCbAd1": "Cyrus Younessi",
    "0x0373cD781D0884b32E2b68dd2799fCA90bf1395A": "Patrick LaVecchia",
    "0x037b344e4A3b0810F70AF7E8Be578C5c63BbB340": "Mariano Conti",
    "0x03874883399cE56e438E41726975EbD033D0Ee63": "Will Price",
    "0x0389338879FE3cb062A933dd7f43C0Bb7f0f1520": "Fernando Martinelli",
    "0x038a2aF6dC7724125884E74D9fc3F474B8a79943": "Stani Kulechov/Laglio",
    "0x038e756d9E9FE13adBD96D4b81e6a05c5d2752A4": "Alex Svanevik",
    "0x039C43f3F887B8a0CF4C1529313a3392f6744D61": "Marc Bhargava",
    "0x039b567ed59A29b5d7a57354400544Ba6c35CFD3": "Jamie Zigelbaum",
    "0x03A0baE872c0243E08f75426f5DCBc1CE4343C65": "Ryan Sean Adams",
    "0x03A321192854a4e8161c1f06fa9a99F37F075718": "Hart Lambur",
    "0x03A3795cb5e43a57f95BBDB08DE6f293f92CE7Ab": "Julian Koh",
    "0x03A7F59dd1dd7ECF01BA22BeD091262D4289073f": "Kain Warwick",
    "0x03AadFc86fcd720681e0EB8a11c57751A28Fb99a": "Delong",
    "0x03Ba9f3ADb4B23C3332D8b68fa03dAf487f98D16": "Evan VN",
    "0x03C322F4a90f3387333a44D7FF6109209De815Cf": "Robert (Compound)",
    "0x03D52a3403808323481CA80bEee09c639bEF4297": "Tarun (Gauntlet)",
    "0x03D97e0BC935FDaF076b284917Bebe91904B762A": "Hello (kevalin)",
    "0x03Df13eCd08CC1bd5FF7F8E339FfABA716Cee334": "Christian (Component)",
    "0x03a461045fE36815C41663819EBb47a49fF2d1e4": "Greg (Chainsafe)",
    "0x03c8ADC46c02EC34D7065c97C85E352085E64aB3": "Simona Pop",
    "0x03d8FF639642441a16701bc49666c2f670EBD640": "Re'em",
    "0x03dD702256C0cFAd7D53FeFaddC51063A151c898": "Mattias",
    "0x03f581A203C30c838d2772D209F888BeE68d6805": "Bobby",
    "0x04032d4b73470f1c72F6c918b263B5B6CD696C35": "Shant",
    "0x0405bfa774BC712c8141E627D292c0d6FB1F5A78": "Tucker (Oasis Pro)",
    "0x0406863656EB235C7eAd4c4c7c22294A7450563a": "Coulter",
}

# Get session object
# This reads the postgres.env file for database credentials
db_session = initialize_session()

setup_logging(".logging/update_usernames.log", log_stdout=True, delete_previous_logs=True)

# Add to database
for addr, username in addr_to_username.items():
    logging.info("Registering address %s to username %s", addr, username)
    add_addr_to_username(username=username, addresses=addr, session=db_session, force_update=FORCE_UPDATE)
