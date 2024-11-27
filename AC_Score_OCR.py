import vapoursynth as vs
core = vs.core
core.max_cache_size=64
from functools import partial
import os
import re

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
    img = core.ffms2.Source(screenshot)
    if type(img) == list:
        img = img[0]
    img = img.resize.Point(format=vs.GRAY8, matrix_s="709")
    if game.lower() == "acb":
        # these are for 6-man lobbies only atm
        scale = img.width / 1280
        left = 228 * scale
        top = 145 * scale
        width = 546 * scale
        height = players * 26 * scale
        binarize = [120, 145] # highlight, rest
        img = img.std.CropAbs(left=left, top=top, width=width, height=height)
        blue_v = [255, 0]
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
                "nyxies": "Onyxies",
                "OOnyxies": "Onyxies",
                "Sugarfree$": "Sugarfree.$",
                "iQueazo4": "iQueazo24"
                }
    elif game.lower() == "ac4":
        scale = img.width / 1920
        scale_y = img.height / 1080
        blue_v = [0, 255]
        if not ffa:
            # although supported post-game screenshots tend to perform worse
            if not post_game:
                left = 650 * scale
                top = [660 * scale_y, 890 * scale_y]
                right = 486 * scale
                bottom = [267 * scale_y, 39 * scale_y]
                binarize = [140, 90]
            else:
                left = 906 * scale
                top = [526 * scale_y, 755 * scale_y]
                right = 196 * scale
                bottom = [402 * scale_y, 174 * scale_y]
                binarize = [150, 130]
            t = img.std.Crop(left=left, top=top[0], right=right, bottom=bottom[0])
            b = img.std.Crop(left=left, top=top[1], right=right, bottom=bottom[1])
            img = core.std.StackVertical([t, b])
        else:
            left = 650 * scale
            top = 682 * scale_y
            right = 486 * scale
            bottom = 90 * scale_y
            binarize = [140, 90]
            img = img.std.Crop(left=left, top=top, right=right, bottom=bottom)
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
   
    # upscaling helps lol
    # too high -> OOM
    img = img.resize.Spline16(img.width * 3, img.height * 3)
    
    # can't use a sophisticated denoising algorithm so just use this to reduce noise & ringing
    img = img.std.Convolution(matrix=[1, 2, 1, 2, 4, 2, 1, 2, 1]) 
    
    # split players
    img_arr = []
    m = players
    for i in range(1, m + 1):
        img_arr.append(img.std.CropAbs(top=img.height / m * (i - 1), width=img.width, height=img.height / players))
    
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
    out = ", ".join([p[1:] for p in sorted(result_f)]).replace("$O", "$0")
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


def main():
    return OCR("test.jpg", "ac4", 8, False, True)

if __name__ == "__main__":
    #print(OCR("screenshots/2021-07-12 21:13:01.853292.png", "acb", 6))
    main()

# import vapoursynth as vs
# core = vs.core
# core.max_cache_size=64
# from functools import partial
# import os
# import re

# os.environ['LC_ALL'] = 'C'

# def OCR(screenshot: str, game: str, players: int, post_game: bool = False):
#     """
#     Screenshot OCR function using VapourSynth and Tesseract.

#     :param screenshot: path to screenshot file
#     :param game: game initials to change settings
#     :param players: total number of players in the match
#     :param post_game: switch to post_game screenshotting style (currently only AC4)
#     :return: OCRed match data string formatted for eloupdate
#     """
#     players = int(players)
#     img = core.ffms2.Source(screenshot)
#     # img = core.imwri.Read(screenshot)
#     # img = img.resize.Bicubic(1920, 1080)
#     s = img
#     if type(img) == list:
#         img = img[0]
#     img = img.resize.Point(format=vs.GRAY8, matrix_s="709")
#     if game.lower() == "acb":
#         # these are for 6-man lobbies only atm
#         scale = img.width / 1280
#         left = 228 * scale
#         top = 145 * scale
#         width = 546 * scale
#         height = players * 26 * scale
#         binarize = [120, 145] # highlight, rest
#         img = img.std.CropAbs(left=left, top=top, width=width, height=height)
#         blue_v = [255, 0]
#         extra_crop = 0
#         map_name = None
#         common = {
#                 "$S": "$5",
#                 "$g": "$9",
#                 "Tha$Fazz": "Tha Fazz",
#                 "EtermityEzioWolf": "EternityEzioWolf",
#                 "EtemnityEzioWolf": "EternityEzioWolf",
#                 "DevelSpnt": "DevelSpirit",
#                 "DevelSpint": "DevelSpirit",
#                 "DaokO": "Daok0",
#                 "Daoko": "Daok0",
#                 "piesiol": "piesio1",
#                 "Mrtirox": "MrEirox",
#                 "MtEirox": "MrEirox",
#                 "DevelSpnt": "DevelSpirit",
#                 "Dnft": "Drift",
#                 "Dnift": "Drift",
#                 "Delipit": "Dellpit",
#                 "Deilpit": "Dellpit",
#                 "Etemity": "Eternity",
#                 "ThaF$azz": "Tha Fazz",
#                 "Fox92": "Auditore92",
#                 "F_o_x$92": "Auditore92",
#                 "Fox9_2": "Auditore92",
#                 "Fox_9_2": "Auditore92",
#                 "F_ox_92": "Auditore92",
#                 "F_ox9_2": "Auditore92",
#                 "F$ox9$2": "Auditore92",
#                 "Fo$x9$2": "Auditore92",
#                 "F$o$x9$2": "Auditore92",
#                 "F_o$x$92": "Auditore92",
#                 "F_ox92": "Auditore92",
#                 "F_ox_9_2": "Auditore92",
#                 "Tha$_Fazz": "Tha_Fazz",
#                 "95On": "95on",
#                 "950n": "95on",
#                 "Crispi$Kreme": "Crispi Kreme",
#                 "Leviathan$B": "Levi",
#                 "F$ox92": "Auditore92",
#                 "Fox$92": "Auditore92",
#                 "F_ox$92": "Auditore92",
#                 "XxdJlantitou": "XxJlantitou",
#                 "JIantitou": "Jlantitou",
#                 "Vinny$Fe": "Vinny_Fe",
#                 "Crispi_$": "Crispi_",
#                 }
#     elif game.lower() == "acr":
#         scale = img.width / 1280
#         left = 518 * scale
#         top = [194 * scale, 360 * scale]
#         right=352 * scale
#         bottom = [430 * scale, 264 * scale]
#         binarize = [150, 115]
#         t = img.std.Crop(left=left, top=top[0], right=right, bottom=bottom[0])
#         b = img.std.Crop(left=left, top=top[1], right=right, bottom=bottom[1])
#         img = core.std.StackVertical([t, b])
#         blue_v = [0, 255]
#         extra_crop = 0
#         map_name = None
#         common = {
#                 "piesiol": "piesio1",
#                 "piesio[": "piesio1",
#                 "$M": "$11",
#                 "$N": "$11",
#                 "$n": "$11",
#                 "IQueazo": "iQueazo",
#                 "DurandaISword": "DurandalSword",
#                 "|DurZa": "DurZa",
#                 "O0": "0",
#                 "0O": "0",
#                 "TneAngryRiver": "TheAngryRiver",
#                 "|IDurZa": "DurZa",
#                 "iiDurZa": "DurZa",
#                 "piesio]": "piesio1",
#                 "TneAngrwaer": "TheAngryRiver",
#                 "iiQueazo": "iQueazo",
#                 "iQueazol": "iQueazo",
#                 "nyxies": "Onyxies",
#                 "OOnyxies": "Onyxies",
#                 "Sugarfree$": "Sugarfree.$",
#                 "iQueazo4": "iQueazo24"
#                 }
#     elif game.lower() == "ac4":
#         scale = img.width / 1920
#         left = 904 * scale
#         top = [525 * scale, 754 * scale]
#         right = 150 * scale
#         bottom = [401 * scale, 172 * scale]
#         binarize = [140] * 2
#         # although supported post-game screenshots tend to perform worse
#         # if not post_game:
#         #     left = 650 * scale
#         #     top = [660 * scale, 890 * scale]
#         #     right = 486 * scale
#         #     bottom = [267 * scale, 39 * scale]
#         #     binarize = [160, 135]
#         # else:
#         #     left = 906 * scale
#         #     top = [526 * scale, 755 * scale]
#         #     right = 196 * scale
#         #     bottom = [402 * scale, 174 * scale]
#         #     binarize = [150, 130]
#         map_name = img.std.Crop(top=162 * scale, left=200 * scale, right=1294 * scale, bottom=890 * scale)
#         v1 = img.std.Crop(left=left, right=648 * scale)
#         v2 = img.std.Crop(left=1290 * scale, right=466 * scale)
#         v3 = img.std.Crop(left=1474 * scale, right=298 * scale)
#         v4 = img.std.Crop(left=1628 * scale, right=right)
#         img = core.std.StackHorizontal([v1, v2, v3, v4])
#         t = img.std.Crop(top=top[0], bottom=bottom[0])
#         b = img.std.Crop(top=top[1], bottom=bottom[1])
#         img = core.std.StackVertical([t, b])
#         extra_crop = 10
#         blue_v = [0, 255]
#         common = {
#                 "She$Who": "She_Who",
#                 "Who$Knows": "Who_Knows",
#                 "El$Pig": "El_Pig",
#                 "EI$Pig": "El_Pig",
#                 "E|$Pig": "El_Pig",
#                 "The$Shmush": "The_Shmush",
#                 "$The_Shmush": "The_Shmush",
#                 "Iltoxic": "iltoxic",
#                 "iItoxic": "iltoxic",
#                 "i|toxic": "iltoxic",
#                 "Lunaire$.-": "Lunaire.-",
#                 "Arunl991": "Arun1991",
#                 "yOssi100": "y0ssi100",
#                 "KirkkoMain69": "KirikoMain69",
#                 "KirlkoMain69": "KirikoMain69",
#                 "katswya": "Katsvya",
#                 "katsvya": "Katsvya",
#                 "$Xanthe$x": "Xanthex",
#                 "$Xanthex": "Xanthex",
#                 "chrlstlanC": "Chr1st1anC"
#                 }
#     else:
#         return OCR(screenshot, "acb", players)

#     # upscaling helps lol
#     # too high -> OOM
#     img = img.resize.Spline16(img.width * 3, img.height * 3)

#     # can't use a sophisticated denoising algorithm so just use this to reduce noise & ringing
#     img = img.std.Convolution(matrix=[1, 2, 1, 2, 4, 2, 1, 2, 1])

#     # split players
#     img_arr = []
#     m = players
#     for i in range(1, m + 1):
#         img_arr.append(img.std.CropAbs(top=img.height / m * (i - 1) + int(extra_crop * scale), width=img.width, height=img.height / players - int(2 * extra_crop * scale)))

#     img = img_arr[0]
#     for i in img_arr[1:]:
#         img += i

#     # invert if main player (the one taking the screenshot) and binarize
#     def check_invert(n, f, c):
#         if f.props.PlaneStatsMin > 75:
#             return c.std.Binarize(binarize[0], v0=blue_v[0], v1=blue_v[1])
#         else:
#             return c.std.Binarize(binarize[1])

#     img = img.std.FrameEval(partial(check_invert, c=img), img.std.PlaneStats())

#     # and finally a quick sharpen (not that importnat tbh)
#     img = img.warp.AWarpSharp2()
#     # alternatively (this is less than ideal)
#     #img = img.std.Convolution(matrix=[0, -1, 0, -1, 5, -1 , 0, -1, 0])

#     # the actual OCR
#     img = img.ocr.Recognize(datapath="/home/dell/tessdata/", language="eng", options=["tessedit_char_whitelist", "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-_ []"])
#     if map_name is not None:
#         map_name = map_name.ocr.Recognize(datapath="/home/dell/tessdata/", language="eng", options=["tessedit_char_whitelist", "1234ABCDEFGHIJKLMNOPQRSTUVWXYZ"])

#     # print OCR results onto frame
#     def print_subs(n, f, c, result_f):
#         # prepare AN format for each player
#         # store n so we can sort and don't have to do this single-threaded
#         result = str(n) + str(f.props.OCRString).replace("b'", "").replace("'", "").replace(" ", "$").replace("\\n", ", ")
#         # common mistakes
#         for m in [*common]:
#             result = result.replace(m, common[m])
#         result_f.append(result)
#         return c#.sub.Subtitle(result, style="sans-serif,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,10,10,10,1")

#     # prepare list which will store all the results
#     result_f = []

#     # progress update
#     def __vs_out_updated(c, t):
#         if c == t:
#             print("Frame: {}/{}".format(c, t), end="\n")
#         else:
#             print("Frame: {}/{}".format(c, t), end="\r")


#     # run script
#     with open(os.devnull, 'wb') as f:
#         if map_name is not None:
#             map_name = map_name.std.FrameEval(partial(print_subs, c=map_name, result_f=result_f), map_name)
#             map_name.output(f, progress_update=__vs_out_updated)
#         processed = img.std.FrameEval(partial(print_subs, c=img, result_f=result_f), img)
#         processed.output(f, progress_update=__vs_out_updated)

#     # remove n from earlier and join
#     out = ", ".join([p[1:] for p in sorted(result_f)]).replace("$O", "$0")
#     return re.sub("[\\[].*?[\\]]", "", out)#, img, s


# def correct_score(match: str, correction: int, team: int):
#     """
#     Score correction script to evenly add points to a team.

#     :param match: match as eloupdate formatted string
#     :param correction: points to add
#     :param team: team to add points to
#     :return: match with adjusted points
#     """
#     # we only have int corrections
#     correction = int(correction)
#     team = int(team) - 1
#     # extract teams and players
#     players = match.split(", ")
#     isfloat = correction % (len(players) / 2)
#     correction /= len(players) / 2
#     if not isfloat:
#         correction = int(correction)
#     middle = int(len(players) / 2)
#     teams = [players[:middle], players[middle:]]
#     affected_split = [player.split("$") for player in teams[team]]
#     for i in range(len(affected_split)):
#         affected_split[i][1] = str(int(affected_split[i][1]) + correction)
#     # combine it all
#     combine = ["$".join(player) for player in affected_split]
#     teams[team] = combine
#     teams = [", ".join(team) for team in teams]
#     return ", ".join(teams)


# if __name__ == "__main__":
#     print(OCR("screenshots/2021-07-12 21:13:01.853292.png", "acb", 6))
