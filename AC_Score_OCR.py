from functools import partial
import os
import re
import cv2
import pytesseract
import numpy as np

os.environ['LC_ALL'] = 'C'

def OCR(screenshot: str, game: str, players: int, post_game: bool = False, ffa: bool = False):
    """
    Screenshot OCR function using VapourSynth and Tesseract.

    :param screenshot: path to screenshot file
    :param game: game initials to change settings
    :param players: total number of players in the match
    :param post_game: switch to post_game screenshotting style (currently only AC4)
    :return: OCRed match data string formatted for eloupdate
    """
    players = int(players)
    orig = cv2.imread(screenshot)
    img = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    if game.lower() == "acb":
        scale = img.shape[1] / 1280
        left = int(229 * scale)
        top = int(145 * scale)
        width = int(546 * scale)
        height = int(players * 26 * scale)
        binarize = [120, 145] # highlight, rest
        threshold = 150
        img = img[top:top + height,left:left + width]
        common = {
                "$S": "$5",
                "$g": "$9",
                "Tha$Fazz": "Tha Fazz",
                "EtermityEzioWolf": "EternityEzioWolf",
                "EtemnityEzioWolf": "EternityEzioWolf",
                "DevelSpnt": "DevelSpirit",
                "DevelSpint": "DevelSpirit",
                "DaokO": "Daok0",
                "Daoko": "Daok0",
                "piesiol": "piesio1",
                "Mrtirox": "MrEirox",
                "MtEirox": "MrEirox",
                "DevelSpnt": "DevelSpirit",
                "Dnft": "Drift",
                "Dnift": "Drift",
                "Delipit": "Dellpit",
                "Deilpit": "Dellpit",
                "Etemity": "Eternity",
                "ThaF$azz": "Tha Fazz",
                "Fox92": "Auditore92",
                "F_o_x$92": "Auditore92",
                "Fox9_2": "Auditore92",
                "Fox_9_2": "Auditore92",
                "F_ox_92": "Auditore92",
                "F_ox9_2": "Auditore92",
                "F$ox9$2": "Auditore92",
                "Fo$x9$2": "Auditore92",
                "F$o$x9$2": "Auditore92",
                "F_o$x$92": "Auditore92",
                "F_ox92": "Auditore92",
                "F_ox_9_2": "Auditore92",
                "Tha$_Fazz": "Tha_Fazz",
                "95On": "95on",
                "950n": "95on",
                "Crispi$Kreme": "Crispi Kreme",
                "Leviathan$B": "Levi",
                "F$ox92": "Auditore92",
                "Fox$92": "Auditore92",
                "F_ox$92": "Auditore92",
                "XxdJlantitou": "XxJlantitou",
                "JIantitou": "Jlantitou",
                "Vinny$Fe": "Vinny_Fe",
                "Crispi_$": "Crispi_",
                }
    elif game.lower() == "acr":
        scale = img.shape[1] / 1280
        left = 518 * scale
        top = [194 * scale, 360 * scale]
        right=352 * scale
        bottom = [430 * scale, 264 * scale]
        binarize = [150, 115]
        threshold = 200
        left = int(left)
        top = [int(i) for i in top]
        width = int(img.shape[1] - left - right)
        height = int(img.shape[0] - top[0] - bottom[0])
        img = cv2.vconcat([img[top[i]:top[i] + height, left:left + width] for i in range(2)])
        blue_v = [0, 255]
        common = {
                "piesiol": "piesio1",
                "piesio[": "piesio1",
                "$M": "$11",
                "$N": "$11",
                "$n": "$11",
                "IQueazo": "iQueazo",
                "DurandaISword": "DurandalSword",
                "|DurZa": "DurZa",
                "O0": "0",
                "0O": "0",
                "TneAngryRiver": "TheAngryRiver",
                "|IDurZa": "DurZa",
                "iiDurZa": "DurZa",
                "piesio]": "piesio1",
                "TneAngrwaer": "TheAngryRiver",
                "iiQueazo": "iQueazo",
                "iQueazol": "iQueazo",
                "nyxies": "Onyxies",
                "OOnyxies": "Onyxies",
                "Sugarfree$": "Sugarfree.$",
                "iQueazo4": "iQueazo24"
                }
    elif game.lower() == "ac4":
        scale = img.shape[1] / 1920
        scale_y = img.shape[0] / 1080
        blue_v = [0, 255]
        threshold = 150
        if not ffa:
            if not post_game:
                left = 650 * scale
                top = [660 * scale_y, 890 * scale_y]
                right = 486 * scale
                bottom = [267 * scale_y, 39 * scale_y]
                binarize = [140, 90]
            else:
                # get rid of abstergo nonsense
                for h in range(img.shape[0]):
                    for w in range(img.shape[1]):
                        if orig[h, w, 0] < 60 and orig[h, w, 2] > 100:
                            img[h, w] = 255
                left = 906 * scale
                top = [526 * scale_y, 755 * scale_y]
                right = 196 * scale
                bottom = [402 * scale_y, 174 * scale_y]
                binarize = [140, 130]
            left = int(left)
            top = [int(i) for i in top]
            width = int(img.shape[1] - left - right)
            height = int(img.shape[0] - top[0] - bottom[0])
            img = cv2.vconcat([img[top[i]:top[i] + height, left:left + width] for i in range(2)])
            img = cv2.hconcat([img[:, :360], img[:, 375:560], img[:, 575:710], img[:, 725:]])
        else:
            left = int(650 * scale)
            top = int(682 * scale_y)
            right = int(486 * scale)
            bottom = int(90 * scale_y)
            binarize = [140, 90]
            width = int(img.shape[1] - left - right)
            height = int(img.shape[0] - top - bottom)
            img = img[top:top + height, left:left + width]
            blue_v = [255, 0]
        common = {
                "She$Who": "She_Who",
                "Who$Knows": "Who_Knows",
                "El$Pig": "El_Pig",
                "EI$Pig": "El_Pig",
                "E|$Pig": "El_Pig",
                "The$Shmush": "The_Shmush",
                "$The_Shmush": "The_Shmush",
                "Iltoxic": "iltoxic",
                "iItoxic": "iltoxic",
                "i|toxic": "iltoxic",
                "Lunaire$.-": "Lunaire.-",
                "Arunl991": "Arun1991",
                "yOssi100": "y0ssi100",
                "KirkkoMain69": "KirikoMain69",
                "KirlkoMain69": "KirikoMain69",
                "katswya": "Katsvya",
                "katsvya": "Katsvya",
                "$Xanthe$x": "Xanthex",
                "$Xanthex": "Xanthex",
                "chrlstlanC": "Chr1st1anC",
                "Arun0G": "ArunOG"
                }
    else:
        return OCR(screenshot, "acb", players)

    # cv2.imshow("", img)
    # cv2.waitKey(0)
    img = cv2.resize(img, [i * 3 for i in img.shape[:2]][::-1], interpolation=cv2.INTER_NEAREST)

    # split players
    img_arr = []
    m = players
    for i in range(1, m + 1):
        top = img.shape[0] // m * (i - 1)
        img_arr.append(img[top:top + img.shape[0] // players, :])

    for i in range(len(img_arr)):
        if np.median(img_arr[i]) < threshold:
            _, img_arr[i] = cv2.threshold(img_arr[i], binarize[0], 255, cv2.THRESH_BINARY_INV)
        else:
            _, img_arr[i] = cv2.threshold(img_arr[i], binarize[1], 255, cv2.THRESH_BINARY)
        # cv2.imshow("", img_arr[i])
        # cv2.waitKey(0)

    whitelist = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-_ []"
    result = []
    for i in img_arr:
        r = pytesseract.image_to_string(i, lang="eng", config=f"--psm 7 -c tessedit_char_whitelist={whitelist}")
        r = r.replace("'", "").replace(" ", "$").replace("\\n", ", ").replace("\n", ", ")
        for m in [*common]:
            r = r.replace(m, common[m])
        result.append(r)

    # remove n from earlier and join
    out = ", ".join([p[1:] for p in result]).replace("$O", "$0")
    return re.sub("[\[].*?[\]]", "", out)


def correct_score(match: str, correction: int, team: int):
    """
    Score correction script to evenly add points to a team.

    :param match: match as eloupdate formatted string
    :param correction: points to add
    :param team: team to add points to
    :return: match with adjusted points
    """
    # we only have int corrections
    correction = int(correction)
    team = int(team) - 1
    # extract teams and players
    players = match.split(", ")
    isfloat = correction % (len(players) / 2)
    correction /= len(players) / 2
    if not isfloat:
        correction = int(correction)
    middle = int(len(players) / 2)
    teams = [players[:middle], players[middle:]]
    affected_split = [player.split("$") for player in teams[team]]
    for i in range(len(affected_split)):
        affected_split[i][1] = str(int(affected_split[i][1]) + correction)
    # combine it all
    combine = ["$".join(player) for player in affected_split]
    teams[team] = combine
    teams = [", ".join(team) for team in teams]
    return ", ".join(teams)


if __name__ == "__main__":
    OCR("./manhunt1.png", "acb", 6)
    OCR("./escort1.png", "acb", 4)
    OCR("./domi1.jpg", "ac4", 8, post_game=True)
    OCR("./domi3.png", "ac4", 8, post_game=True)
    OCR("./aa1.png", "acr", 8)
    OCR("./domi2.jpg", "ac4", 8, post_game=False)

