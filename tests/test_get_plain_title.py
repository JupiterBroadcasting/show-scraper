import re

SHOW_TITLE_REGEX = re.compile(r"^(?:(?:Episode)?\s?[0-9]+:+\s+)?(.+?)(?:(\s+\|+.*)|\s+)?$")


def get_plain_title(title: str) -> str:
    """
    Get just the show title, without any numbering etc
    """
    return SHOW_TITLE_REGEX.match(title)[1]

def test_selfhosted():
    assert get_plain_title("78: We Should Know Better") == "We Should Know Better"
    assert get_plain_title("77: Automations Gone Wrong") == "Automations Gone Wrong"
    assert get_plain_title("76: Solid as a Rock") == "Solid as a Rock"
    assert get_plain_title("75: In-Flight Changes") == "In-Flight Changes"
    assert get_plain_title("74: A Pi For Every Problem") == "A Pi For Every Problem"
    assert get_plain_title("73: 100 Days of HomeLab") == "100 Days of HomeLab"
    assert get_plain_title("72: First Account is Free") == "First Account is Free"
    assert get_plain_title("71: Recipe for Success") == "Recipe for Success"
    assert get_plain_title("70: Plausible Deniability") == "Plausible Deniability"
    assert get_plain_title("69: Get Off My Lawn, The Robot's Got It") == "Get Off My Lawn, The Robot's Got It"

    assert get_plain_title("9: Conquering Planned Obsolescence") == "Conquering Planned Obsolescence"
    assert get_plain_title("8: WLED Changes the Game") == "WLED Changes the Game"
    assert get_plain_title("7: Why We Love Home Assistant") == "Why We Love Home Assistant"
    assert get_plain_title("6: Low Cost Home Camera System") == "Low Cost Home Camera System"
    assert get_plain_title("5: ZFS Isn’t the Only Option") == "ZFS Isn’t the Only Option"
    assert get_plain_title("4: The Joy of Plex with Elan Feingold") == "The Joy of Plex with Elan Feingold"
    assert get_plain_title("3: Home Network Under $200") == "Home Network Under $200"
    assert get_plain_title("2: Why Self-Host? With Wendell from Level1techs") == "Why Self-Host? With Wendell from Level1techs"
    assert get_plain_title("1: The First One") == "The First One"
    assert get_plain_title("Self-Hosted Coming Soon") == "Self-Hosted Coming Soon"


def test_extras():
    assert get_plain_title("Brunch With Brent: Tim Canham") == "Brunch With Brent: Tim Canham"
    assert get_plain_title("Brunch with Brent: Quentin Stafford-Fraser") == "Brunch with Brent: Quentin Stafford-Fraser"
    assert get_plain_title("Headline Hangout w/Chris") == "Headline Hangout w/Chris"
    assert get_plain_title("March Boost Battle") == "March Boost Battle"
    assert get_plain_title("Microsoft is now the Disney of Video Games") == "Microsoft is now the Disney of Video Games"
    assert get_plain_title("Road Trip Tech") == "Road Trip Tech"
    assert get_plain_title("Road Trip Memories") == "Road Trip Memories"
    assert get_plain_title("Why Linux Will Win in 20 Years") == "Why Linux Will Win in 20 Years"
    assert get_plain_title("elementary OS 6.1 Secrets with Founder and CEO Danielle Foré") == "elementary OS 6.1 Secrets with Founder and CEO Danielle Foré"
    assert get_plain_title("Cryptocurrency Chat with Chris") == "Cryptocurrency Chat with Chris"

    assert get_plain_title("Librem 5 Unplugged") == "Librem 5 Unplugged"
    assert get_plain_title("Brunch with Brent: Drew DeVore") == "Brunch with Brent: Drew DeVore"
    assert get_plain_title("User Error Outtake: Bunk Beds") == "User Error Outtake: Bunk Beds"
    assert get_plain_title("The Story Behind Self-Hosted") == "The Story Behind Self-Hosted"
    assert get_plain_title("Brunch with Brent: Alex Kretzschmar") == "Brunch with Brent: Alex Kretzschmar"
    assert get_plain_title("Brunch with Brent: Chz Bacon") == "Brunch with Brent: Chz Bacon"
    assert get_plain_title("The Enthusiast Trap - Office Hours with Chris") == "The Enthusiast Trap - Office Hours with Chris"
    assert get_plain_title("Dell's New Ubuntu Hardware for Late 2019") == "Dell's New Ubuntu Hardware for Late 2019"
    assert get_plain_title("Chris and Wes React to LINUX Unplugged") == "Chris and Wes React to LINUX Unplugged"
    assert get_plain_title("Thomas Cameron Texas LinuxFest Keynote") == "Thomas Cameron Texas LinuxFest Keynote"

def test_coder():
    assert get_plain_title("482: Building Your Light Saber") == "Building Your Light Saber"
    assert get_plain_title("481: Apple's Metal Tax") == "Apple's Metal Tax"
    assert get_plain_title("480: Google's 1984 Moment") == "Google's 1984 Moment"
    assert get_plain_title("479: Apple's Mob Move") == "Apple's Mob Move"
    assert get_plain_title("478: Strange New Workflows") == "Strange New Workflows"
    assert get_plain_title("477: Sweet Little Lies") == "Sweet Little Lies"
    assert get_plain_title("476: Tapping the Breaks") == "Tapping the Breaks"
    assert get_plain_title("475: I Do Declare") == "I Do Declare"
    assert get_plain_title("474: Horton Hears a Linux User") == "Horton Hears a Linux User"
    assert get_plain_title("473: Laptop Coasters") == "Laptop Coasters"

    assert get_plain_title("Bye Bye Ballmer | CR 64") == "Bye Bye Ballmer"
    assert get_plain_title("Mozilla Persona | CR 63") == "Mozilla Persona"
    assert get_plain_title("FizzBuzzed! | CR 62") == "FizzBuzzed!"
    assert get_plain_title("Office Hours | CR 61") == "Office Hours"
    assert get_plain_title("Call In 2.0 | CR 60") == "Call In 2.0"
    assert get_plain_title("Sour Apple | CR 59") == "Sour Apple"
    assert get_plain_title("The 56k Solution | CR 58") == "The 56k Solution"
    assert get_plain_title("The Dev Jungle | CR 57") == "The Dev Jungle"
    assert get_plain_title("Microsoft’s in a Funk | CR 56") == "Microsoft’s in a Funk"
    assert get_plain_title("Software Exorcism | CR 55") == "Software Exorcism"

def test_lan():
    assert get_plain_title("Linux Action News 257") == "Linux Action News 257"
    assert get_plain_title("Linux Action News 256") == "Linux Action News 256"
    assert get_plain_title("Linux Action News 255") == "Linux Action News 255"
    assert get_plain_title("Linux Action News 254") == "Linux Action News 254"
    assert get_plain_title("Linux Action News 253") == "Linux Action News 253"
    assert get_plain_title("Linux Action News 252") == "Linux Action News 252"
    assert get_plain_title("Linux Action News 251") == "Linux Action News 251"
    assert get_plain_title("Linux Action News 250") == "Linux Action News 250"
    assert get_plain_title("Linux Action News 249") == "Linux Action News 249"
    assert get_plain_title("Linux Action News 248") == "Linux Action News 248"

    assert get_plain_title("Linux Action News 9") == "Linux Action News 9"
    assert get_plain_title("Linux Action News 8") == "Linux Action News 8"
    assert get_plain_title("Linux Action News 7") == "Linux Action News 7"
    assert get_plain_title("Linux Action News 6") == "Linux Action News 6"
    assert get_plain_title("Linux Action News 5") == "Linux Action News 5"
    assert get_plain_title("Linux Action News 4") == "Linux Action News 4"
    assert get_plain_title("Linux Action News 3") == "Linux Action News 3"
    assert get_plain_title("Linux Action News 2") == "Linux Action News 2"
    assert get_plain_title("Linux Action News 1") == "Linux Action News 1"
    assert get_plain_title("Linux Action News 00") == "Linux Action News 00"

def test_lup():
    assert get_plain_title("474: Linux's Malware Inevitability") == "Linux's Malware Inevitability"
    assert get_plain_title("473: End of the Road") == "End of the Road"
    assert get_plain_title("472: 5 Problems With NixOS") == "5 Problems With NixOS"
    assert get_plain_title("471: The Cottonwood Disaster") == "The Cottonwood Disaster"
    assert get_plain_title("470: Let's Call It an Upgrade") == "Let's Call It an Upgrade"
    assert get_plain_title("469: Tough Linux Love") == "Tough Linux Love"
    assert get_plain_title("468: The Read Only Scenario") == "The Read Only Scenario"
    assert get_plain_title("467: All Hands on Deck") == "All Hands on Deck"
    assert get_plain_title("466: The Night of a Thousand Errors") == "The Night of a Thousand Errors"
    assert get_plain_title("465: Too Nixy for My Shirt") == "Too Nixy for My Shirt"

    assert get_plain_title("Episode 10: The Ubuntu Hangover | LINUX Unplugged 10") == "The Ubuntu Hangover"
    assert get_plain_title("Episode 9: The Ubuntu Situation | LINUX Unplugged 9") == "The Ubuntu Situation"
    assert get_plain_title("Episode 8: Cloud Guilt | LINUX Unplugged 8") == "Cloud Guilt"
    assert get_plain_title("Episode 7: Full SteamOS Ahead | LUP 7") == "Full SteamOS Ahead"
    assert get_plain_title("Episode 6: The Android Problem | LINUX Unplugged 6") == "The Android Problem"
    assert get_plain_title("Episode 5: Wrath of Linus | LINUX Unplugged 5") == "Wrath of Linus"
    assert get_plain_title("Episode 4: Are Linux Users Cheap? | LINUX Unplugged 4") == "Are Linux Users Cheap?"
    assert get_plain_title("Episode 3: Go Dock Yourself | LINUX Unplugged 3") == "Go Dock Yourself"
    assert get_plain_title("Episode 2: Edge of Failure | LINUX Unplugged 2") == "Edge of Failure"
    assert get_plain_title("Episode 1: Too Much Choice | LU1") == "Too Much Choice"

def test_officehours():
    assert get_plain_title("11: Flipping The Switch") == "Flipping The Switch"
    assert get_plain_title("10: Coming in Hot with the Code!") == "Coming in Hot with the Code!"
    assert get_plain_title("9: We Hate Crypto Too") == "We Hate Crypto Too"
    assert get_plain_title("8: A Good Problem to Have") == "A Good Problem to Have"
    assert get_plain_title("7: Podcasting is Back") == "Podcasting is Back"
    assert get_plain_title("6: Peer to Peer Future") == "Peer to Peer Future"
    assert get_plain_title("5: The Real MVP") == "The Real MVP"
    assert get_plain_title("4: Finding Our Squeaky Wheels") == "Finding Our Squeaky Wheels"
    assert get_plain_title("3: New Website Energy") == "New Website Energy"
    assert get_plain_title("2: Podcasting Perils") == "Podcasting Perils"

    assert get_plain_title("1: The Enthusiast Trap ") == "The Enthusiast Trap"

def test_random_cases():
    assert get_plain_title("1: 1: The Enthusiast Trap ") == "1: The Enthusiast Trap"
    assert get_plain_title("1: 1:The Enthusiast Trap ") == "1:The Enthusiast Trap"
    assert get_plain_title("Z 1:") == "Z 1:"