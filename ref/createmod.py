r"""Create mod / Edit game file / Create about.cfg (docs/plan.md G17; M11):
the twin of the game side's new-mod files (src/states/qmnewmod.pas).

A new local mod is a folder `mods\<Folder>` with three files; the game
registers the folder at its next start (verified since the capability
probes: every folder in mods\ is registered and enabled, even without a
mod.ini). The files:

  mod.ini           the layout of a local mod's mod.ini - the one the
                    local mods here have (mods\SW_Frontline_Protocol\mod.ini,
                    mods\UnofficialPatch\mod.ini: the same 21 keys between
                    section.begin and section.end, CRLF, 3-space indent, an
                    empty line at the end), title and folder filled in
  about.cfg         ref/about.py draft: id, name, version, type, exclusive
  data\readme.txt   where the mod's files go

The folder name is the player's name with every character outside
A-Z a-z 0-9 _ dropped (a space becomes `_`), at most 40 characters, a
letter first; its id is its lower case. A name that leaves nothing, or a
folder that is a registered mod already, is refused.
"""
from ref import about as A

__all__ = ["FOLDER_MAX", "folder_of", "mod_ini", "about_cfg", "readme", "files", "TYPES",
           "EXCLUSIVE", "draft_id", "draft_for"]

FOLDER_MAX = 40
TYPES = (b"mod", b"totalConversion")
EXCLUSIVE = (b"",) + A.SLOTS

_OK = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_")


def folder_of(name):
    """The folder a typed name makes, b"" when it makes none."""
    out = bytearray()
    for c in name:
        if c == 32:
            c = 95
        if c in _OK and len(out) < FOLDER_MAX:
            out.append(c)
    while out and not (65 <= out[0] <= 90 or 97 <= out[0] <= 122):
        del out[0]
    return bytes(out)


MOD_INI_KEYS = (
    b"publishedfileid = 0", b"creatorappid = 0", b"consumerappid = 0",
    b"contentfolder = mods\\{folder}", b"previewfile = ", b"ownersteamid = 0",
    b"timecreated = 0", b"timeupdated = 0", b"visibility = 0", b"banned = False",
    b"title = {title}", b"description[*] = ;A mod made with Quartermaster.", b"tags = ",
    b"filename = {folder}", b"filesize = 0", b"previewfilesize = 0", b"url = ",
    b"filetype = 0", b"acceptedforuse = False", b"changenote[*] = ;First version.")


def mod_ini(folder, title):
    lines = [b"section.begin"]
    for k in MOD_INI_KEYS:
        lines.append(b"   " + k.replace(b"{folder}", folder).replace(b"{title}", title))
    lines += [b"section.end", b""]
    return b"".join(ln + b"\r\n" for ln in lines)


def about_cfg(folder, title, kind=b"mod", exclusive=b""):
    text = A.draft(folder.lower(), title, overhaul=(kind == b"totalConversion"))
    if exclusive:
        text += b"exclusive = " + exclusive + b"\r\n"
    return text


README = (b"This is a mod made with Quartermaster.",
          b"Put the game files it changes under data\\, in the same folders as in the",
          b"game's own data\\ folder: data\\gui\\menu.inc\\oncamera.inc, say.",
          b"about.cfg says what the mod is; the Quartermaster Workshop page lists the keys.")


def readme():
    return b"".join(ln + b"\r\n" for ln in README)


def draft_id(folder):
    """An about.cfg id for an existing folder: folded, every character outside
    a-z 0-9 _ . - as `_`."""
    out = bytearray()
    for c in folder.lower():
        out.append(c if (97 <= c <= 122 or 48 <= c <= 57 or c in b"_.-") else 95)
    return bytes(out)


def draft_for(folder, title, tags=b"", camera=False):
    """Create about.cfg for an existing local mod (M8 task 6, M11): a total
    conversion when its Workshop tags say Overhaul, the camera slot when it
    ships gui\\menu.inc\\oncamera.inc."""
    text = A.draft(draft_id(folder), title, overhaul=b"overhaul" in tags.lower())
    if camera:
        text += b"exclusive = camera\r\n"
    return text


def files(folder, title, kind=b"mod", exclusive=b""):
    """`{relpath: bytes}` of a new mod, relative to mods\\<folder>\\."""
    return {b"mod.ini": mod_ini(folder, title),
            b"about.cfg": about_cfg(folder, title, kind, exclusive),
            b"data\\readme.txt": readme()}
