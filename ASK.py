import random

RESPONSES = (
    "It is certain.",
    "It is decidedly so.",
    "Without a doubt.",
    "Yes definitely.",
    "You may rely on it.",
    "As I see it, yes.",
    "Most likely.",
    "Outlook good.",
    "Yes.",
    "Signs point to yes.",
    "Reply hazy, try again.",
    "Ask again later.",
    "Better not tell you now.",
    "Cannot predict now.",
    "Concentrate and ask again.",
    "Don't count on it.",
    "My reply is no.",
    "My sources say no.",
    "Outlook not so good.",
    "Very doubtful."
    )

def REPLY():
    RESPONSE = random.choice(RESPONSES)
    if RESPONSES.index(RESPONSE) < 10:
        ANSWER = "Y"
    elif RESPONSES.index(RESPONSE) > 14:
        ANSWER = "N"
    else:
        ANSWER = "M"
    return RESPONSE, ANSWER
