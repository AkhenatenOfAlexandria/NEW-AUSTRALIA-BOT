import random

SUITS = ("S", "D", "H", "C")
CARDS = set()

def CARD():
    while True:
        SUIT = random.choice(SUITS)
        FACE = str(random.randint(1, 13))
        if FACE == "11":
            FACE = "J"
        elif FACE == "12":
            FACE = "Q"
        elif FACE == "13":
            FACE = "K"
        elif FACE == "1":
            FACE = "A"
        CARD = FACE+SUIT
        if not CARD in CARDS:
            CARDS.add(CARD)
            break
    return CARD


def FACE(CARD):
    return CARD[:-1]


def CARD_SCORE(CARD):
    ACE = False
    try:
        _SCORE = int(FACE(CARD))
    except ValueError:
        if FACE(CARD) == "J":
            _SCORE = 10
        elif FACE(CARD) == "Q":
            _SCORE = 10
        elif FACE(CARD) == "K":
            _SCORE = 10
        elif FACE(CARD) == "A":
            _SCORE = 1
            ACE = True
    return _SCORE, ACE


def HAND_SCORE(HAND):
    _SCORE = 0
    for CARD in HAND:
        _CARD_SCORE, ACE = CARD_SCORE(CARD)
        _SCORE += _CARD_SCORE
    return _SCORE, ACE

BALANCE = 100

while BALANCE > 0:
    print(f"BALANCE: {BALANCE}")
    while True:
        try:
            PLAYER_BET = int(input("PLACE THY BET: "))
        except TypeError:
            pass
        if PLAYER_BET <= BALANCE:
            break
        
        BALANCE -= PLAYER_BET
        BET = PLAYER_BET

    HOLE = CARD()

    DEALER = {CARD()}

    HAND1 = {CARD(), CARD()}

    HANDS = [HAND1]
    HIT = False
    SPLIT = False
    for HAND in HANDS:
        while HAND_SCORE(HAND)[0] < 21:
            D_SCORE = HAND_SCORE(DEALER)[0]
            H_SCORE = HAND_SCORE(HAND)[0]
            if HAND_SCORE(DEALER)[1] and D_SCORE+10<21:
                D_SCORE += 10
            if HAND_SCORE(HAND)[1] and H_SCORE+10<21:
                H_SCORE += 10
            print(f"DEALER: {DEALER}: {D_SCORE}")
            print(f"HAND: {HAND}: {H_SCORE}")
            INPUT = input()
            if INPUT == "HIT":
                HIT = True
                HAND.add(CARD())
            elif INPUT == "DOUBLE" and not HIT and BALANCE >= PLAYER_BET:
                HAND.add(CARD())
                BET += PLAYER_BET
                BALANCE -= PLAYER_BET
                break
            elif INPUT == "SPLIT"  and not HIT and BALANCE >= PLAYER_BET:
                CARD1 = HAND.pop()
                CARD2 = HAND.pop()
                if FACE(CARD1) == FACE(CARD2):
                    HAND.add(CARD1)
                    HAND.add(CARD())
                    HAND2 = {CARD2, CARD()}
                    HANDS.append(HAND2)
                    SPLIT = True
                    BET += PLAYER_BET
                    BALANCE -= PLAYER_BET
                else:
                    HAND.add(CARD1)
                    HAND.add(CARD2)
            elif INPUT == "STAND":
                break
            elif INPUT == "SURRENDER" and not HIT and not SPLIT:
                break

    if INPUT == "SURRENDER":
        print(f"PLAYER SURRENDERS. RECEIVES {BET/2}.")
        BALANCE += BET/2
    else:
        BUST = False
        PUSH = False
        STRING = ""
        for i, HAND in enumerate(HANDS, 1):
            STRING = f"{STRING}HAND{i}: {HAND}: {HAND_SCORE(HAND)[0]}"
            if HAND_SCORE(HAND)[0] > 21:
                STRING = f"{STRING}: BUST"
                BUST = True
            elif BUST:
                PUSH = True
            STRING = f"{STRING}\n"
        if BUST:
            if PUSH:
                STRING = f"{STRING}PUSH: PLAYER RECEIVES {BET}."
                BALANCE += BET
            else:
                STRING = f"{STRING}BUST"
            print(STRING)
        
        else:
            while HAND_SCORE(DEALER)[0] + CARD_SCORE(HOLE)[0] < 17 and HAND_SCORE(HAND)[0] <= 21:
                DEALER.add(CARD())

            D_SCORE = HAND_SCORE(DEALER)[0] + CARD_SCORE(HOLE)[0]
            H_SCORE = HAND_SCORE(HAND)[0]
            if (HAND_SCORE(DEALER)[1] or CARD_SCORE(HOLE)[1]) and D_SCORE+10<21:
                D_SCORE += 10
            if HAND_SCORE(HAND)[1] and H_SCORE+10<21:
                H_SCORE += 10
            print(f"DEALER: {DEALER} HOLE: {HOLE}: {D_SCORE}")
            print(f"HAND: {HAND}: {H_SCORE}")

            if D_SCORE > 21:
                print(f"DEALER BUSTS. PLAYER WINS {BET*2}.")
                BALANCE += BET*2
            elif D_SCORE > H_SCORE:
                print("DEALER WINS.")
            elif D_SCORE < H_SCORE:
                print(f"PLAYER WINS{BET*2}.")
                BALANCE += BET*2
            else:
                print(f"PUSH. PLAYER RECEIVES {BET}.")
                BALANCE += BET
            