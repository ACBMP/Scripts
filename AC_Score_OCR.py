import vapoursynth as vs
core = vs.core
core.max_cache_size=64
from functools import partial
import os

os.environ['LC_ALL'] = 'C'

def OCR(screenshot: str, game: str, players: int):
    """
    Screenshot OCR function using VapourSynth and Tesseract.

    :param screenshot: path to screenshot file
    :param game: game initials to change settings
    :param players: total number of players in the match
    :return: OCRed match data string formatted for eloupdate
    """
    players = int(players)
    img = core.ffms2.Source(screenshot)
    if type(img) == list:
        img = img[0]
    img = img.resize.Point(format=vs.GRAY8, matrix_s="709")
    if game.lower() == "acb":
        # these are for 6-man lobbies only atm
        scale = img.width / 1280
        left = 230 * scale
        top = 148 * scale
        right = 525 * scale
        bottom = 420 + (25 * abs(6 - players)) * scale
        binarize = [120, 145] # highlight, rest
        img = img.std.Crop(left=left, top=top, right=right, bottom=bottom)
        blue_v = [255, 0]
        common = {
                "$S": "$5",
                "$g": "$9",
                "Tha$Fazz": "Tha Fazz",
                "EtermityEzioWolf": "EternityEzioWolf",
                "DevelSpnt": "DevelSpirit",
                "DaokO": "Daok0",
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
                }
    elif game.lower() == "acr":
        scale = img.width / 1280
        left = 518 * scale
        top = [194 * scale, 360 * scale]
        right=352 * scale
        bottom = [430 * scale, 264 * scale]
        binarize = [150, 115]
        t = img.std.Crop(left=left, top=top[0], right=right, bottom=bottom[0])
        b = img.std.Crop(left=left, top=top[1], right=right, bottom=bottom[1])
        img = core.std.StackVertical([t, b])
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
                "nyxies": "Onyxies"
                }
    else:
        return OCR(screenshot, "acb", players)
   
    # upscaling helps lol
    # too high -> OOM
    img = img.resize.Spline16(img.width * 3, img.height * 3)
    
    # can't use a sophisticated denoising algorithm so just use this to reduce noise & ringing
    img = img.std.Convolution(matrix=[1, 2, 1, 2, 4, 2, 1, 2, 1]) 
    
    # split players
    img_arr = []
    m = players
    for i in range(1, m + 1):
        img_arr.append(img.std.Crop(bottom=img.height / m * (m - i), top=img.height / m * (i - 1)))
    
    img = img_arr[0]
    for i in img_arr[1:]:
        img += i
    
    # invert if main player (the one taking the screenshot) and binarize
    def check_invert(n, f, c):
        if f.props.PlaneStatsMin > 75:
            return c.std.Binarize(binarize[0], v0=blue_v[0], v1=blue_v[1])
        else:
            return c.std.Binarize(binarize[1])
    
    img = img.std.FrameEval(partial(check_invert, c=img), img.std.PlaneStats())
      
    # and finally a quick sharpen (not that importnat tbh)
    img = img.warp.AWarpSharp2()
    # alternatively (this is less than ideal)
    #img = img.std.Convolution(matrix=[0, -1, 0, -1, 5, -1 , 0, -1, 0])
     
    # the actual OCR
    img = img.ocr.Recognize(datapath="/home/dell/tessdata/", language="eng", options=["tessedit_char_whitelist", "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-_ "])
    
    # print OCR results onto frame
    def print_subs(n, f, c, result_f):
        # prepare AN format for each player
        # store n so we can sort and don't have to do this single-threaded
        result = str(n) + str(f.props.OCRString).replace("b'", "").replace("'", "").replace(" ", "$").replace("\\n", ", ")
        # common mistakes
        for m in [*common]:
            result = result.replace(m, common[m])
        result_f.append(result)
        return c#.sub.Subtitle(result, style="sans-serif,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,10,10,10,1")
    
    # prepare list which will store all the results
    result_f = []
    
    # progress update
    def __vs_out_updated(c, t):
        if c == t:
            print("Frame: {}/{}".format(c, t), end="\n")
        else:
            print("Frame: {}/{}".format(c, t), end="\r")
    
    
    # run script
    with open(os.devnull, 'wb') as f:
        processed = img.std.FrameEval(partial(print_subs, c=img, result_f=result_f), img)
        processed.output(f, progress_update=__vs_out_updated)
    
    # remove n from earlier and join
    return ", ".join([p[1:] for p in sorted(result_f)]).replace("$O", "$0")


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
    print(OCR("screenshots/2021-07-12 21:13:01.853292.png", "acb", 6))
