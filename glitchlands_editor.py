import math, os, json, subprocess
from functools import partial
from tkinter import*
from tkinter.messagebox import*
from tkinter.simpledialog import*
from tkinter.filedialog import*
from tkinter.ttk import Button, Combobox
from tkinter import Button as tkButton
from PIL import Image, ImageTk, ImageEnhance, ImageDraw
from lib_glitchlands import*

TILEW = 16
S = 2
TS = TILEW*S
WIDTH = 800
HEIGHT = 480
INF = float("inf")
HIGHLIGHT_COLOR = "red"
GUIDE_COLOR_1, GUIDE_COLOR_2 = "gray", "darkgray"
FONT_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ    0123456789.,:?!()+-'"
FONT_DECORATORS = "@#"
FONT_CHARW, FONT_CHARH = 12, 14
PLAYTEST_SLOT = 0
EDITOR_SAVE_FILE = os.path.abspath(os.path.join("save", "editor.json"))
MAP_DATA_FILE = os.path.abspath(os.path.join("assets_glitchlands", "map", "data.json"))
TERRAIN_STYLE_OFFSETS = [ # terrain id: x offset, y offset
    {
        0: (6, 0),
        1: (6, 4),
        2: (6, 8),
        3: (0, 0),
        4: (0, 4),
        5: (0, 8),
        6: (17, 4),
        7: (21, 0),
    },
    {
        0: (12, 0),
        1: (12, 4),
        2: (12, 8),
        3: (17, 8),
        4: (22, 8),
    },
    {
        0: (17, 1),
        1: (17, 2),
        2: (17, 0),
    },
    {
        0: (0, 3),
    }
]
TILE_OFFSETS = [ # pretty id: x offset, y offset
    {
        0: (0, 0),
        1: (1, 0),
        2: (2, 0),
        3: (0, 1),
        4: (1, 1),
        5: (2, 1),
        6: (0, 2),
        7: (1, 2),
        8: (2, 2),
        9: (3, 0),
        10: (4, 0),
        11: (3, 1),
        12: (4, 1),
        13: (3, 2),
    },
    {
        0: (0, 0),
        1: (1, 0),
        2: (2, 0),
        3: (3, 0),
        4: (3, 1),
        5: (3, 2),
        6: (1, 1),
        7: (2, 1),
        8: (1, 2),
        9: (2, 2),
        10: (0, 1),
    },
    {
        0: (0, 0),
        1: (1, 0),
        2: (2, 0),
    },
    {
        0: (0, 0),
        1: (1, 0),
        2: (2, 0),
        3: (3, 0),
    }
]
SIDEBAR_TILES = [ # pretty id, type, sidebar x, sidebar y
    (0, 0, 0, 0),
    (1, 0, 1, 0),
    (2, 0, 2, 0),
    (3, 0, 0, 1),
    (4, 0, 1, 1),
    (5, 0, 2, 1),
    (6, 0, 0, 2),
    (7, 0, 1, 2),
    (8, 0, 2, 2),
    (9, 0, 0, 3),
    (10, 0, 1, 3),
    (11, 0, 0, 4),
    (12, 0, 1, 4),
    (13, 0, 2, 3),
    (0, -1, 0, 5),
    (1, -1, 1, 5),
    (2, -1, 2, 5),
    (3, -1, 0, 6),
    (4, -1, 0, 7),
    (5, -1, 0, 8),
    (6, -1, 1, 6),
    (7, -1, 2, 6),
    (8, -1, 1, 7),
    (9, -1, 2, 7),
    (10, -1, 1, 8),
    (0, -2, 0, 9),
    (1, -2, 1, 9),
    (2, -2, 2, 9),
    (0, -3, 0, 10),
    (1, -3, 0, 11),
    (2, -3, 1, 10),
    (3, -3, 1, 11),
    (0, OBJTYPE_GLITCHZONE, 0, 12),
    (1, OBJTYPE_GLITCHZONE, 1, 12),
    (2, OBJTYPE_GLITCHZONE, 2, 12),
]

data = {}
levelpos = None
images = {}
notfound = None
objects = {}
history = []
sidebartiles = {}
objnum, objtype = None, None
tool = None
shift = False
bgphoto, bgobj = None, None
terrainstyle = [0, 0, 0]

class Object:
    def __init__(self, num, typ, x, y):
        global objects
        self.num = num
        self.type = typ
        self.x = x
        self.y = y
        self.xrep = 1
        self.yrep = 1
        self.layer = 0
        self.style = None
        self.other = {}
        self.photo = ImageTk.PhotoImage(images.get(get_image_name(self), notfound))
        self.obj = canvas.create_image((x, y), image=self.photo, anchor=NW, tag="object")
        objects[self.obj] = self
    def get_data(self):
        d = {"num": self.num, "type": self.type, "x": self.x, "y": self.y,
             "xrep": self.xrep, "yrep": self.yrep, "layer": self.layer, "style": self.style}
        for k, v in self.other.items():
            if v is not None: d[k] = v
        if d.get("xrep", 1) == 1: del d["xrep"]
        if d.get("yrep", 1) == 1: del d["yrep"]
        if d.get("layer", 0) == 0: del d["layer"]
        if d.get("style") is None: del d["style"]
        return d
    def update_pos(self):
        canvas.coords(self.obj, self.x, self.y)
    def update_image(self):
        im = get_concat_tile_repeat(images.get(get_image_name(self), notfound), self.xrep, self.yrep)
        if self.layer != 0:
            en = ImageEnhance.Brightness(im)
            im = en.enhance(1.2 if self.layer > 0 else .7)
        self.photo = ImageTk.PhotoImage(im)
        canvas.itemconfig(self.obj, image=self.photo)
    def delete(self):
        global objects
        canvas.delete(self.obj)
        del objects[self.obj]

class SidebarImage:
    def __init__(self, num, typ, x, y):
        global sidebartiles
        self.num = num
        self.type = typ
        self.x = x
        self.y = y
        self.style = None
        self.photo = ImageTk.PhotoImage(images.get(get_image_name(self), notfound))
        self.obj = sidebar.create_image((x, y), image=self.photo, anchor=NW, tag="tile")
        sidebartiles[self.obj] = self

def cur(e=None):
    if e is None:
        n = canvas.find_withtag("current")
    else:
        x, y = canvas.canvasx(e.x), canvas.canvasy(e.y)
        n = canvas.find_closest(x, y)
    if len(n) == 0 or "bg" in canvas.gettags(n[0]): return
    return objects[n[0]]

def isnum(n):
    if type(n) == int: return True
    if len(n) == 0: return False
    if n[0] == "-": n = n[1:]
    return n.isdigit()

def isfloat(n):
    if type(n) == float: return True
    if len(n) == 0: return False
    if n[0] == "-": n = n[1:]
    if n.count(".") > 1: return False
    return n.replace(".", "").isdigit()

def init():
    global images, notfound, levelpos
    os.chdir("assets_glitchlands")
    im = Image.open(os.path.join("objects", "terrain.png"))
    for typ in range(len(TERRAIN_STYLE_OFFSETS)):
        for style, pos in TERRAIN_STYLE_OFFSETS[typ].items():
            for num, ofs in TILE_OFFSETS[typ].items():
                images[f"{num}_{-typ}_{style}"] = resize_by_scale(im.crop((
                    (pos[0]+ofs[0])*TILEW, (pos[1]+ofs[1])*TILEW, (pos[0]+ofs[0]+1)*TILEW, (pos[1]+ofs[1]+1)*TILEW
                    )))
    im = Image.open(os.path.join("ui", "font_outlined.png"))
    for y in range(im.height//FONT_CHARH):
        for x in range(im.width//FONT_CHARW):
            images["font_"+FONT_CHARSET[x+y*(im.width//FONT_CHARW)]] = resize_by_scale(im.crop((
                x*FONT_CHARW, y*FONT_CHARH, (x+1)*FONT_CHARW, (y+1)*FONT_CHARH
                )))
    im = Image.open(os.path.join("ui", "backgrounds.png"))
    for y in range(im.height//64):
        for x in range(im.width//64):
            images[f"bg_{x+y*(im.width//64)}"] = im.crop((
                x*64, y*64, (x+1)*64, (y+1)*64
                ))
    images["glitch_0"] = Image.new("RGB", (TS, TS), (255, 0, 0))
    images["glitch_1"] = Image.new("RGB", (TS, TS), (0, 255, 0))
    images["glitch_2"] = Image.new("RGB", (TS, TS), (0, 0, 255))
    notfound = Image.new("RGBA", (TS, TS), (0, 0, 0, 255))
    draw = ImageDraw.Draw(notfound)
    draw.rectangle((0, 0, TS//2, TS//2), (255, 0, 255))
    draw.rectangle((TS//2, TS//2, TS, TS), (255, 0, 255))
    if os.path.isfile(EDITOR_SAVE_FILE):
        with open(EDITOR_SAVE_FILE) as f:
            editordata = json.load(f)
            levelpos = tuple(editordata.get("level_pos", levelpos))
    load_zone(isinit=True)

def get_image_name(obj):
    if obj.type <= OBJTYPE_BLOCK:
        if obj.style is None:
            if -obj.type < len(TERRAIN_STYLE_OFFSETS)-1: s = terrainstyle[-obj.type]
            else: s = 0
        elif obj.type == OBJTYPE_SPIKE: s = 0
        else: s = obj.style
        return f"{obj.num}_{obj.type}_{s}"
    if obj.type == OBJTYPE_TEXT:
        return f"font_{str(obj.num).upper()}"
    if obj.type == OBJTYPE_GLITCHZONE:
        return f"glitch_{obj.num}"

def get_font_width(text):
    return sum(int((0 if char in FONT_DECORATORS else .66 if char in " .,!'" else 1)*FONT_CHARW*S) for char in text)

def get_concat_h_repeat(im, column):
    dst = Image.new("RGBA", (im.width*column, im.height))
    for x in range(column): dst.paste(im, (x*im.width, 0))
    return dst

def get_concat_v_repeat(im, row):
    dst = Image.new("RGBA", (im.width, im.height*row))
    for y in range(row): dst.paste(im, (0, y*im.height))
    return dst

def get_concat_tile_repeat(im, x, y):
    dst_h = get_concat_h_repeat(im, x)
    return get_concat_v_repeat(dst_h, y)

def resize_by_scale(im):
    return im.resize((im.width*S, im.height*S), Image.Resampling.NEAREST)

def cycle_background(e=None):
    global data
    data["background"] = data["background"]+1 if f"bg_{data['background']+1}" in images else 0
    load_level()

def cycle_terrain_style(typ, e=None):
    global terrainstyle, data
    data["terrain_style"] = terrainstyle = \
        terrainstyle[:typ]+((terrainstyle[typ]+1)%len(TERRAIN_STYLE_OFFSETS[typ]),)+terrainstyle[typ+1:]
    refresh_sidebar(keephighlight=True)
    load_level()

def set_shift(pressed):
    global shift
    shift = pressed

def push_history(e=None):
    global history
    load_level(canv=False)
    history.append(json.dumps(data))

def pop_history(e=None):
    global history, data
    if len(history) == 0: return
    data = json.loads(history.pop())
    load_level(save=False)

def spinbox(f, text, val, y, mn, mx, float=False, focus=False, **kw):
    v = StringVar(value=val)
    Label(f, text=text).grid(row=y, column=0, padx=5, pady=1)
    sb = Spinbox(f, from_=mn, to=mx, width=18, textvariable=v, format="%.2f" if float else None, **kw)
    sb.grid(row=y, column=1, sticky=W)
    if val is None: v.set("")
    if y == 0 or focus:
        v.set("" if val is None else val) # this is required for some reason DO NOT REMOVE
        sb.focus_set()
        sb.selection_range(0, END)
    return v

def entry(f, text, val, y, focus=False, **kw):
    v = StringVar(value=val)
    Label(f, text=text).grid(row=y, column=0, padx=5, pady=1)
    e = Entry(f, width=20, textvariable=v, **kw)
    e.grid(row=y, column=1, sticky=W)
    if val is None: v.set("")
    if y == 0 or focus:
        v.set("" if val is None else val)
        e.focus_set()
        e.selection_range(0, END)
    return v

def dropdown(f, text, vals, num, y, **kw):
    v = StringVar()
    Label(f, text=text).grid(row=y, column=0, padx=5, pady=1)
    cb = Combobox(f, width=16, textvariable=v, values=vals, state="readonly", **kw)
    cb.current(num)
    cb.grid(row=y, column=1, sticky=W)
    return (cb, v)

def checkbox(f, text, state, y, **kw):
    v = IntVar()
    Label(f, text=text).grid(row=y, column=0, padx=5, pady=1)
    cb = Checkbutton(f, pady=0, variable=v, **kw)
    cb.grid(row=y, column=1, sticky=W)
    if state: cb.select()
    return v

def save(e=None, conf=False):
    global data
    load_level(canv=False)
    with open(levelfn(), "w") as f:
        json.dump(data, f, separators=(",", ":"))
    if os.path.isfile(MAP_DATA_FILE) and levelpos[0] != 0:
        with open(MAP_DATA_FILE) as f:
            mapdata = json.load(f)
        mapdata[levelpos[0]].setdefault("levels", {})
        mapdata[levelpos[0]]["levels"].setdefault(f"{levelpos[1]},{levelpos[2]}", {})
        mapdata[levelpos[0]]["levels"][f"{levelpos[1]},{levelpos[2]}"]["color"] = data["background"]
        with open(MAP_DATA_FILE, "w") as f:
            json.dump(mapdata, f, indent=2)
    if conf: showinfo("Save", "Successfully saved level.")

def save_editor(e=None):
    editordata = {"level_pos": levelpos}
    os.makedirs(os.path.dirname(EDITOR_SAVE_FILE), exist_ok=True)
    with open(EDITOR_SAVE_FILE, "w") as f:
        json.dump(editordata, f, indent=2)

def levelfn():
    return os.path.join("levels", ",".join([str(n) for n in levelpos])+".json")

def refresh_sidebar(keephighlight=False):
    sidebar.delete("tile", "levelpos")
    for t in SIDEBAR_TILES:
        SidebarImage(t[0], t[1], t[2]*TS, t[3]*TS)
    if keephighlight: sidebar.tag_raise("highlight")
    else: sidebar.delete("highlight")
    sidebar.create_text(TS*3//2, HEIGHT-2, text=str(tuple(levelpos)), anchor="s",
                        fill="black", font="Helvetica 10 bold", tag="levelpos")

def settings(e=None):
    def apply(e=None):
        global terrainstyle
        bg = cv["bg"].get()
        if not isnum(bg) or (f"bg_{bg}" not in images and int(bg) >= 0):
            showerror("Background", "Invalid value for background")
            return
        cpos = cv["checkpoint_left"].get(), cv["checkpoint_top"].get(), cv["checkpoint_right"].get()
        if any(p != "" and not isfloat(p) for p in cpos):
            showerror("Checkpoint", "Invalid value for checkpoint position")
            return
        transition = cv["transition"][0].current()-1
        if transition < 0: transition = None
        style1, style2, style3 = cv["style1"].get(), cv["style2"].get(), cv["style3"].get()
        if not isnum(style1) or not isnum(style2) or not isnum(style3):
            showerror("Terrain style", "Invalid value for terrain style")
            return
        bottomxl, bottomxr = cv["bottom_exit_left"].get(), cv["bottom_exit_right"].get()
        if not (bottomxl == "" or isnum(bottomxl)) or not (bottomxr == "" or isnum(bottomxr)):
            showerror("Bottom exit", "Invalid value for bottom exit left/right")
            return
        data["background"] = int(bg)
        data["checkpoint_positions"] = tuple(None if p == "" else int(float(p)*TS) for p in cpos)
        data["scroll_left"] = bool(cv["scroll_left"].get())
        data["scroll_right"] = bool(cv["scroll_right"].get())
        data["rookie_checkpoints"] = bool(cv["rookie_checkpoints"].get())
        data["bottom_exit_left"] = None if bottomxl == "" else int(bottomxl)*TS
        data["bottom_exit_right"] = None if bottomxr == "" else int(bottomxr)*TS
        data["transition"] = transition
        data["terrain_style"] = terrainstyle = (int(style1), int(style2), int(style3))
        load_level()
        refresh_sidebar(keephighlight=True)
        t.destroy()
    def clos(e=None):
        if changedroom > 0: apply()
        else: t.destroy()
    def set_checkpoint_left():
        cv["checkpoint_left"].set(HEIGHT//TS-2)
    def set_checkpoint_right():
        cv["checkpoint_right"].set(HEIGHT//TS-2)
    def set_checkpoint_top():
        cv["checkpoint_top"].set(WIDTH//TS/2)
    t = Toplevel(root)
    t.title("Settings")
    t.geometry("270x360+300+200")
    t.protocol("WM_DELETE_WINDOW", clos)
    t.grab_set()
    t.bind_all("<Return>", apply)
    t.bind_all("<Escape>", clos)
    Label(t, text="Settings").pack()
    changedroom = 0
    cv = {}

    r = Frame(t)
    cv["bg"] = spinbox(r, "Background", data.get("background", 0), 0, -3, 15)
    cppos = [None if p is None else p/TS for p in data.get("checkpoint_positions", [None, None, None])]
    cv["checkpoint_left"] = spinbox(r, "Checkpoint left Y", cppos[0], 1, -1, HEIGHT//TS-1)
    cv["checkpoint_right"] = spinbox(r, "Checkpoint right Y", cppos[2], 2, -1, HEIGHT//TS-1)
    cv["checkpoint_top"] = spinbox(r, "Checkpoint top X", cppos[1], 3, -1, WIDTH//TS-1, float=True)
    bottomxl = data.get("bottom_exit_left")
    if bottomxl is not None: bottomxl /= TS
    bottomxr = data.get("bottom_exit_right")
    if bottomxr is not None: bottomxr /= TS
    cv["bottom_exit_left"] = spinbox(r, "Bottom exit left", bottomxl, 4, 0, WIDTH//TS-1)
    cv["bottom_exit_right"] = spinbox(r, "Bottom exit right", bottomxr, 5, 0, WIDTH//TS-1)
    cv["scroll_left"] = checkbox(r, "Scroll left", data.get("scroll_left", True), 6)
    cv["scroll_right"] = checkbox(r, "Scroll right", data.get("scroll_right", True), 7)
    transition = data.get("transition")
    if transition is None: transition = 0
    else: transition += 1
    cv["transition"] = dropdown(r, "Transition", ["None", "Flash black", "Flash white", "Fade to black", "Fade to white", "Virus"],
                                transition, 8)
    cv["rookie_checkpoints"] = checkbox(r, "Rookie checkpoints", data.get("rookie_checkpoints", False), 9)
    cv["style1"] = spinbox(r, "Terrain style 1", terrainstyle[0], 10, 0, len(TERRAIN_STYLE_OFFSETS[0])-1)
    cv["style2"] = spinbox(r, "Terrain style 2", terrainstyle[1], 11, 0, len(TERRAIN_STYLE_OFFSETS[1])-1)
    cv["style3"] = spinbox(r, "Terrain style 3", terrainstyle[2], 12, 0, len(TERRAIN_STYLE_OFFSETS[2])-1)
    tkButton(r, text="13", command=set_checkpoint_left, width=2).grid(row=1, column=2)
    tkButton(r, text="13", command=set_checkpoint_right, width=2).grid(row=2, column=2)
    tkButton(r, text=".5", command=set_checkpoint_top, width=2).grid(row=3, column=2)
    r.pack()
    Button(t, text="OK", command=apply).pack()

def block_options(e=None):
    def apply(e=None):
        num = cv["num"].get()
        if isnum(num): num = int(num)
        typ = cv["type"].get()
        x = cv["x"].get()
        y = cv["y"].get()
        xrep = cv["xrep"].get()
        yrep = cv["yrep"].get()
        layer = cv["layer"].get()
        style = cv["style"].get() if "style" in cv else None
        remdiff = cv["removal_range"].get() if "removal_range" in cv else None
        physics = cv["physics"].get() if "physics" in cv else None
        warp = cv["warp"].get() if "warp" in cv else None
        if not isnum(num) or not isnum(typ) or not isfloat(x) or not isfloat(y) or not isnum(xrep) or not isnum(yrep) or \
           not isnum(layer) or not (style == "" or style is None or isnum(style)) or int(xrep) < 1 or int(yrep) < 1:
            showerror("Invalid value", "A field has an invalid value")
            return
        if physics is not None:
            try: json.loads(physics)
            except json.decoder.JSONDecodeError:
                showerror("Invalid physics", "Invalid value for physics")
                return
        push_history()
        b.type = int(typ)
        b.num = int(num)
        x = float(x)*TS
        y = float(y)*TS
        if b.x != x or b.y != y:
            b.x = x
            b.y = y
            b.update_pos()
        b.xrep = int(xrep)
        b.yrep = int(yrep)
        b.layer = int(layer)
        if style is not None:
            b.style = None if style == "" else int(style)
        if remdiff is not None:
            if remdiff == "": b.other["removal_range"] = None
            else:
                b.other["removal_range"] = [None if n == "" else int(n) for n in remdiff.split(",", 1)]
                while len(b.other["removal_range"]) < 2: b.other["removal_range"].append(None)
        if physics is not None:
            b.other["physics"] = json.loads(physics)
        if warp is not None:
            b.other["warp"] = [int(n) for n in warp.split(",")]
        b.update_image()
        clos()
    def clos(e=None):
        canvas.delete(hr)
        t.destroy()
    def set_id_to_current():
        cv["num"].set(objnum)
        cv["type"].set(objtype)
    b = cur()
    t = Toplevel(root)
    t.title("Object Configuration")
    t.geometry("250x260+300+200")
    t.protocol("WM_DELETE_WINDOW", clos)
    t.grab_set()
    t.bind_all("<Return>", apply)
    t.bind_all("<Escape>", clos)
    hr = canvas.create_rectangle(b.x, b.y, b.x-1+b.photo.width(), b.y-1+b.photo.height(),
                                 width=1, outline=HIGHLIGHT_COLOR)
    lbl = Label(t, text="Object Configuration")
    lbl.pack()
    f = Frame(t)
    cv = {}
    if isnum(b.num): cv["num"] = spinbox(f, "ID", b.num, 0, -INF, INF)
    else: cv["num"] = entry(f, "ID", b.num, 0)
    cv["type"] = spinbox(f, "Tile type", b.type, 1, -INF, INF)
    cv["x"] = spinbox(f, "X pos", b.x/TS, 2, -INF, INF, float=True, focus=True)
    cv["y"] = spinbox(f, "Y pos", b.y/TS, 3, -INF, INF, float=True)
    cv["xrep"] = spinbox(f, "X count", b.xrep, 4, 1, INF)
    cv["yrep"] = spinbox(f, "Y count", b.yrep, 5, 1, INF)
    cv["layer"] = spinbox(f, "Layer", b.layer, 6, -INF, INF)
    if b.type == 7:
        if b.num == 1: cv["warp"] = entry(f, "Warp to", ",".join([str(n) for n in b.other.get("warp", [0, 0, 0])]), 7)
        elif b.num == 2: cv["physics"] = entry(f, "Physics mod", json.dumps(b.other.get("physics", {})), 7)
    else:
        cv["style"] = spinbox(f, "Style", b.style, 7, 0, INF)
        remdiff = ""
        if b.other.get("removal_range"):
            r = b.other["removal_range"]
            while len(r) < 2: r.append(None)
            if r[0] is not None: remdiff += str(r[0])
            remdiff += ","
            if r[1] is not None: remdiff += str(r[1])
        cv["removal_range"] = entry(f, "Removal range", remdiff, 8)
    if objnum is not None: tkButton(f, text="C", command=set_id_to_current, width=1).grid(row=0, column=2)
    f.pack()
    Button(t, text="OK", command=apply).pack()

def text_tool(x, y):
    def apply(e=None):
        text = cv["text"].get().encode().decode("unicode-escape")
        if len(text) == 0:
            clos()
            return
        if any(char.upper() not in FONT_CHARSET+FONT_DECORATORS+"\n" for char in text):
            showerror("Text", "The text provided contains an unsupported character.")
            return
        push_history()
        align = cv["alignment"][0].current()
        tx, ty = x*TS, y*TS
        if align == 1: tx += FONT_CHARW//2*S
        sx = tx
        lines = text.split("\n")
        order = max(o.other.get("ordering", -1) for o in objects.values())+1 if len(objects) > 0 else 0
        deco = 0
        for ln in lines:
            w = get_font_width(ln)
            for char in ln:
                if char in FONT_DECORATORS:
                    deco = FONT_DECORATORS.index(char)+1
                    continue
                nx = tx
                if align == 1: nx -= w//2
                if nx > -FONT_CHARW*S and nx < WIDTH and char != " ":
                    obj = Object(char, OBJTYPE_TEXT, nx, ty)
                    obj.other["ordering"] = order
                    if deco > 0:
                        obj.other["style"] = deco
                        deco = 0
                tx += get_font_width(char)
                order += 1
            ty += TS
            if ty > HEIGHT: break
            tx = sx
        clos()
    def clos(e=None):
        canvas.delete(hr)
        t.destroy()
    if x == WIDTH//TS//2: x = (WIDTH//2-FONT_CHARW*S//2)/TS
    t = Toplevel(root)
    t.title("Text Tool")
    t.geometry("220x210+300+200")
    t.protocol("WM_DELETE_WINDOW", clos)
    t.grab_set()
    t.bind_all("<Return>", apply)
    t.bind_all("<Escape>", clos)
    hr = canvas.create_rectangle(x*TS, y*TS, x*TS+FONT_CHARW*S-1, y*TS+FONT_CHARH*S-1,
                                 width=1, outline=HIGHLIGHT_COLOR)
    lbl = Label(t, text="Text Tool")
    lbl.pack()
    f = Frame(t)
    cv = {}
    cv["text"] = entry(f, "Text", "", 0)
    cv["alignment"] = dropdown(f, "Alignment", ["Left", "Center"], 1, 1)
    f.pack()
    Button(t, text="OK", command=apply).pack()

def physics_calculator(e=None):
    def calculate(e=None):
        g = cv["gravity"].get()
        gh = cv["gravity_hold_mult"].get()
        sd = cv["speed_decay"].get()
        d = cv["jump_distance"].get()
        hmax = cv["jump_height"].get()
        if not isfloat(g) or not isfloat(gh) or not isfloat(sd) or not isfloat(d) or not isfloat(hmax):
            showerror("Invalid value", "A field has an invalid value")
            return
        g = float(g)
        gh = float(gh)
        sd = float(sd)
        d = float(d)*TS-(64-13*2+2)
        hmax = float(hmax)*-TS
        gt = g+g*gh
        p = (gt+math.sqrt(-8*hmax*gt))/(2*g)
        hland = -2+2*p*g/gt
        s = d*(1-sd)/(sd*math.floor(hland))
        rv["speed"]["text"] = f"Speed: {math.ceil(s*1000)/1000}"
        rv["speed"].pack()
        rv["jump_power"]["text"] = f"Jump power: {math.ceil(p*1000)/1000}"
        rv["jump_power"].pack()
    t = Toplevel(root)
    t.title("Physics Calculator")
    t.geometry("240x210+300+200")
    t.grab_set()
    t.bind_all("<Return>", calculate)
    t.bind_all("<Escape>", lambda e: t.destroy())
    lbl = Label(t, text="Physics Calculator")
    lbl.pack()
    f = Frame(t)
    cv = {}
    cv["jump_distance"] = spinbox(f, "Gap jump distance", 6.4, 0, 0, INF, float=True)
    cv["jump_height"] = spinbox(f, "Jump height", 5.3, 1, 0, INF, float=True)
    cv["gravity"] = spinbox(f, "Gravity", 1.1, 2, 0, INF, float=True)
    cv["gravity_hold_mult"] = spinbox(f, "Gravity hold mult", -0.3, 3, -INF, 0, float=True)
    cv["speed_decay"] = spinbox(f, "Speed decay", .8, 4, 0, INF, float=True)
    f.pack()
    Button(t, text="Go", command=calculate).pack()
    r = Frame(t)
    rv = {}
    rv["speed"] = Label(r, text="Speed")
    rv["jump_power"] = Label(r, text="Jump power")
    r.pack()

def left_click(e):
    x, y = int(e.x//TS), int(e.y//TS)
    if cur() is None or shift:
        if tool is not None: # use tool
            if tool == 0: text_tool(x, y)
        elif objnum is not None: # place object
            push_history()
            Object(objnum, objtype, x*TS, y*TS)
    else: block_options()

def middle_click(e):
    global objnum, objtype
    c = cur()
    if c is None: return
    for o in sidebartiles.values():
        if o.num == c.num and o.type == c.type:
            set_block(o)
            return
    sidebar.delete("highlight")
    objnum = c.num
    objtype = c.type

def right_click(e):
    c = cur(e)
    if c is None: return
    push_history()
    c.delete()

def sidebar_left_click(e):
    x, y = sidebar.canvasx(e.x), sidebar.canvasy(e.y)
    n = sidebar.find_closest(x, y)
    if len(n) == 0 or n[0] not in sidebartiles: return
    t = sidebartiles[n[0]]
    if objnum == t.num and objtype == t.type: set_block(None)
    else: set_block(t)

def set_block(t):
    global objnum, objtype, tool
    sidebar.delete("highlight")
    tool = None
    if t is None:
        objnum = None
        objtype = None
    else:
        objnum = t.num
        objtype = t.type
        sidebar.create_rectangle(t.x, t.y, t.x-1+t.photo.width(), t.y-1+t.photo.height(),
                                 width=1, outline=HIGHLIGHT_COLOR, tag="highlight")

def change_selection(xofs=0, yofs=0):
    pos = None
    for t in sidebartiles.values():
        if t.num == objnum and t.type == objtype:
            pos = t.x, t.y
    if pos is None: pos = (0, 0)
    else: pos = (pos[0]+xofs*TS, pos[1]+yofs*TS)
    for t in sidebartiles.values():
        if t.x == pos[0] and t.y == pos[1]:
            set_block(t)
            return

def change_tile_repetition(xofs=0, yofs=0):
    c = cur()
    if c is None: return
    c.xrep = max(c.xrep+xofs, 1)
    c.yrep = max(c.yrep+yofs, 1)
    c.update_image()

def load_zone(wofs=0, xofs=0, yofs=0, isinit=False):
    global levelpos, data, terrainstyle, history
    if not isinit: save()
    history = []
    prevpos = levelpos[:]
    if wofs == 0: levelpos = (levelpos[0], levelpos[1]+xofs, levelpos[2]+yofs)
    else: levelpos = (levelpos[0]+wofs, 0, 0)
    if os.path.isfile(levelfn()):
        with open(levelfn()) as f:
            data = json.load(f)
    else:
        if not askokcancel("Load zone", f"No level exists at {levelpos}. Create one now?"):
            if isinit:
                levelpos = (1, 0, 0)
                load_zone(isinit=True)
            else: levelpos = prevpos
            return
        data = data.copy()
        for k in ("checkpoint_positions", "bottom_exit_left", "bottom_exit_right", "scroll_left", "scroll_right",
                  "transition", "warp_top", "warp_bottom", "warp_left", "warp_right", "rookie_checkpoints"):
            if k in data: del data[k]
        data["objects"] = [
            {"num":1,"type":0,"x":0,"y":416,"xrep":25},
            {"num":4,"type":0,"x":0,"y":448,"xrep":25}
        ]
    data.setdefault("background", 0)
    data.setdefault("terrain_style", (0, 0, 0))
    data.setdefault("scroll_left", True)
    data.setdefault("scroll_right", True)
    data.setdefault("checkpoint_positions", [None, None, None])
    data.setdefault("bottom_exit_left", None)
    data.setdefault("bottom_exit_right", None)
    data.setdefault("rookie_checkpoints", False)
    terrainstyle = tuple(data["terrain_style"][:])
    refresh_sidebar(keephighlight=True)
    load_level(save=False)

def check_save():
    if os.path.isfile(levelfn()):
        with open(levelfn()) as f:
            bk = json.load(f)
        load_level(canv=False)
        if bk != data:
            conf = askyesnocancel("Save", "Save the current level?")
            if conf is None: return
            if conf: save(conf=False)
    else:
        save(conf=False)
    save_editor()
    root.destroy()

def save_and_exit(e=None):
    if not shift: save()
    save_editor()
    root.destroy()

def test(e=None):
    save()
    save_editor()
    root.withdraw()
    savefile = os.path.join(os.getcwd(), os.pardir, "save", "glitchlands", f"slot{PLAYTEST_SLOT}.json")
    if os.path.isfile(savefile) and any(p is not None for p in data.get("checkpoint_positions", [])):
        with open(savefile, "r+") as f:
            savedata = json.load(f)
            cp = {"level_pos": levelpos, "facing_right": True}
            if data["checkpoint_positions"][1] is not None:
                cp["top"] = 0
                cp["centerx"] = data["checkpoint_positions"][1]
            elif data["checkpoint_positions"][0] is not None:
                cp["left"] = 0
                cp["bottom"] = data["checkpoint_positions"][0]
            elif data["checkpoint_positions"][2] is not None:
                cp["right"] = WIDTH
                cp["bottom"] = data["checkpoint_positions"][2]
                cp["facing_right"] = False
            savedata["checkpoint"] = cp
            f.seek(0)
            f.truncate()
            json.dump(savedata, f, separators=(",", ":"))
    subprocess.call(["python", "glitchlands.py", "--slot", str(PLAYTEST_SLOT)], cwd=os.path.join(os.getcwd(), os.pardir))
    root.deiconify()

def set_tool(n=None):
    global tool, objnum, objtype
    tool = n
    objnum = None
    objtype = None
    sidebar.delete("highlight")

def show_help(e=None):
    t = Toplevel(root)
    t.title("Help")
    t.geometry("410x440+300+200")
    t.grab_set()
    t.bind_all("<Escape>", lambda e: t.destroy())
    t.bind_all("<Return>", lambda e: t.destroy())
    text = """\
Controls:
Left click in the sidebar to select the block to be placed.
Left click on an empty space in the editor to place the selected block.
Left click on a placed block to change its properties.
Shift-click on a placed block to place a block over it.
Right click on a placed block to delete it.
Middle click on a placed block to set it as your selected block.

Shortcuts:
WASD - Change seleted object
P - Save and test
T - Open text tool
Q/E - Change X repetition of hovered tile
Shift+Q/E - Change Y repetition of hovered tile
Tab - Settings
Left/right - Save and go to left/right zone
Up/down - Save and go to above/below zone
Shift+Up/down - Save and go to zone 0, 0 of next/previous world
0 - Cycle background
1/2/3 - Cycle terrain style for that number
Ctrl+S - Save level
Ctrl+Z - Undo
Escape - Save and exit
Shift+Escape - Exit without saving"""
    Label(t, text="Help").pack()
    Label(t, text=text).pack(pady=10)
    okbtn = Button(t, text="OK", command=t.destroy)
    okbtn.pack()
    okbtn.focus_set()

def load_level(save=True, canv=True):
    global data, objects, terrainstyle, bgphoto, bgobj
    if save and data is not None:
        data["objects"] = []
        for o in objects.values():
            data["objects"].append(o.get_data())
        data["objects"].sort(key=lambda o: o.get("layer", 0))
    if canv:
        bgtile = images[f"bg_{max(data.get('background', 0), 0)}"]
        im = get_concat_tile_repeat(bgtile, WIDTH//bgtile.width+1, HEIGHT//bgtile.height+1)
        draw = ImageDraw.Draw(im)
        for x in list(range(2, 11, 2))+list(range(15, 24, 2)):
            for y in list(range(2, 8, 2))+list(range(9, 14, 2)):
                draw.line(((x*TS, 0), (x*TS, HEIGHT)), fill=GUIDE_COLOR_2, width=1)
                draw.line(((0, y*TS), (WIDTH, y*TS)), fill=GUIDE_COLOR_2, width=1)
        draw.line(((WIDTH//2, 0), (WIDTH//2, HEIGHT)), fill=GUIDE_COLOR_1, width=1)
        draw.line(((0, HEIGHT//2), (WIDTH, HEIGHT//2)), fill=GUIDE_COLOR_1, width=1)
        bgphoto = ImageTk.PhotoImage(im)
        if bgobj is None: bgobj = canvas.create_image((0, 0), image=bgphoto, anchor=NW, tag="bg")
        else: canvas.itemconfig(bgobj, image=bgphoto)
        canvas.delete("object")
        objects = {}
        for o in data.get("objects", []):
            b = Object(o.get("num", 0), o.get("type", 0), o.get("x", 0), o.get("y", 0))
            b.xrep = o.get("xrep", 1)
            b.yrep = o.get("yrep", 1)
            b.layer = o.get("layer", 0)
            b.style = o.get("style")
            b.other = {k: o[k] for k in o.keys() - {"num", "type", "x", "y", "xrep", "yrep", "layer", "style"}}
            b.update_image()

root = Tk()
root.title("Glitchlands Level Editor")
root.geometry(f"{WIDTH+TS*3+20}x{HEIGHT}+100+50")
root.protocol("WM_DELETE_WINDOW", check_save)
root.bind("<KeyPress-Shift_L>", lambda e: set_shift(True))
root.bind("<KeyRelease-Shift_L>", lambda e: set_shift(False))
root.bind("<Escape>", save_and_exit)
root.bind("<Control-z>", pop_history)
root.bind("<Control-s>", lambda e: save(conf=True))
root.bind("p", test)
root.bind("t", lambda e: set_tool(0))
root.bind("<Tab>", settings)
root.bind("q", lambda e: change_tile_repetition(xofs=-1))
root.bind("e", lambda e: change_tile_repetition(xofs=1))
root.bind("Q", lambda e: change_tile_repetition(yofs=-1))
root.bind("E", lambda e: change_tile_repetition(yofs=1))
root.bind("a", lambda e: change_selection(xofs=-1))
root.bind("d", lambda e: change_selection(xofs=1))
root.bind("w", lambda e: change_selection(yofs=-1))
root.bind("s", lambda e: change_selection(yofs=1))
root.bind("<Left>", lambda e: load_zone(xofs=-1))
root.bind("<Right>", lambda e: load_zone(xofs=1))
root.bind("<Up>", lambda e: load_zone(yofs=-1))
root.bind("<Down>", lambda e: load_zone(yofs=1))
root.bind("<Shift-Up>", lambda e: load_zone(wofs=1))
root.bind("<Shift-Down>", lambda e: load_zone(wofs=-1))
root.bind("0", cycle_background)
for typ in range(len(TERRAIN_STYLE_OFFSETS)):
    root.bind(str(typ+1), partial(cycle_terrain_style, typ))
content = Frame(root)
sidebar = Canvas(content, bg="lightgray", width=TS*3, height=HEIGHT, bd=-2)
sidebar.grid(row=0, column=1)
sidebar.bind("<Button-1>", sidebar_left_click)
sidebar.bind("<MouseWheel>", lambda e: sidebar.yview_scroll(int(-.01*e.delta), UNITS))
sidescroll = Scrollbar(content, orient=VERTICAL, command=sidebar.yview)
sidescroll.grid(row=0, column=0, sticky=NS)
sidebar.config(yscrollcommand=sidescroll.set)
canvas = Canvas(content, bg="white", width=WIDTH, height=HEIGHT, bd=-2)
canvas.grid(row=0, column=2)
canvas.bind("<Button-1>", left_click)
canvas.bind("<Button-2>", middle_click)
canvas.bind("<Button-3>", right_click)
canvas.bind("<B3-Motion>", right_click)
content.pack(expand=True)
menu = Menu(root)
menu.add_command(label="Save", command=save)
menu.add_command(label="Playtest (P)", command=test)
menu.add_command(label="Settings (Tab)", command=settings)
toolsmenu = Menu(root, tearoff=True)
toolsmenu.add_command(label="Text (T)", command=lambda: set_tool(0))
toolsmenu.add_command(label="Physics calculator", command=physics_calculator)
menu.add_cascade(label="Tools", menu=toolsmenu)
menu.add_command(label="Help", command=show_help)
root.config(menu=menu)
init()
root.mainloop()
