"""Verify the CompoundTagControl and CompoundTagItemControl empty-payload guards and the Balefire Bomb container name (REVIEW-FIXES-CONTROL-NBT-NULL.md).

Read-only for both worktrees. Writes only a unique build/migration/review-fixes/control-nbt-null/verify/<id> run directory.
No game, Gradle or network; javap only with --jar.

- Static (A): the original NBTControlPacket dispatches to receiveControl only inside `if(nbt != null)`; NEO CompoundTagControl.handleServer
  returns on a null tag before enqueueWork and before every receiveControl call, and its only change from the frozen start is that guard
  (comment, guard, blank line). The codec, payload type, registration and IControlReceiver are unchanged. All 26 files that declare
  receiveControl are listed, classified (2 interfaces, 21 block-entity IControlReceiver implementors, 3 IItemControlReceiver items) and
  checked against the recorded set; no item implements IControlReceiver, so the guard covers every receiver CompoundTagControl can reach.
- Static (C): the same for the item control packet: the original NBTItemControlPacket guards `nbt != null` before its only receiveControl call;
  NEO CompoundTagItemControl.handleServer returns on a null tag before enqueueWork and before its only receiveControl call, changes nothing else
  from the frozen start, and keeps its codec, type id, registration and IItemControlReceiver. The classes implementing IItemControlReceiver
  (3) and the senders of the packet (4 sites in 3 screens, none able to pass null) are listed and checked against the recorded sets.
- Static (B): container.nuke_fstbmb is the block name and the original container.nukeFstbmb / tile.nuke_fstbmb.name text; the map entry is
  `upstream` with that source and no local reason; English is unchanged; apart from that one key and entry nothing else in zh_cn.json or the
  map differs from the frozen start (so chem.balefire and container.burntime.balefire, which have no original counterpart, are untouched).
- Tree: the stamp records the edited Java and Chinese file and the generated English file is unchanged.
- JAR (--jar): javap of the built CompoundTagControl.handleServer and CompoundTagItemControl.handleServer start with aload_0, getfield tag,
  ifnonnull, return; the previous release's classes (control) do not; the JAR differs from the previous release in those two classes and
  the Chinese file only.
- Mutations: every static check must reject an anchored regression; the frozen start form must fail the static suite.

python -B -X utf8 tools/migration/verify_review_control_nbt_null.py [--jar build/libs/hbmsntm-198A.jar] [--previous-jar PATH]
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_fixes.block_stubs import method
from verify_goal9b import jdk

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
SOURCE = ROOT / "src/main/java"
BATCH = ROOT / "build/migration/review-fixes/control-nbt-null"
START = BATCH / "baseline-files"
PREVIOUS_JAR = ROOT / "build/migration/releases/goal21a/hbmsntm-198A-goal21a.jar"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"

CTC = "com/hbm/network/toserver/CompoundTagControl.java"
NET = "com/hbm/network/NtmNetwork.java"
ICR = "com/hbm/interfaces/IControlReceiver.java"
PROVIDER = "com/hbm/datagen/NtmLanguageProvider.java"
ICTC = "com/hbm/network/toserver/CompoundTagItemControl.java"
IICR = "com/hbm/items/IItemControlReceiver.java"
TAGS_UTIL = "com/hbm/util/TagsUtil.java"
ORIGINAL_PACKET = "src/main/java/com/hbm/packet/toserver/NBTControlPacket.java"
ORIGINAL_ITEM_PACKET = "src/main/java/com/hbm/packet/toserver/NBTItemControlPacket.java"
ORIGINAL_EN = "src/main/resources/assets/hbm/lang/en_US.lang"
ORIGINAL_ZH = "src/main/resources/assets/hbm/lang/zh_CN.lang"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
EN = "src/generated/resources/assets/hbmsntm/lang/en_us.json"
MAP = "migration/localization/zh_cn-map.json"
GEN_STAMP = "src/generated/resources/.migration-stamp.json"
START_CTC, START_ZH, START_MAP, START_ICTC = (START / n for n in (
    "src__main__java__com__hbm__network__toserver__CompoundTagControl.java",
    "src__main__resources__assets__hbmsntm__lang__zh_cn.json",
    "migration__localization__zh_cn-map.json",
    "src__main__java__com__hbm__network__toserver__CompoundTagItemControl.java"))
CLASS = "com/hbm/network/toserver/CompoundTagControl.class"
ITEM_CLASS = "com/hbm/network/toserver/CompoundTagItemControl.class"
ZH_IN_JAR = "assets/hbmsntm/lang/zh_cn.json"

KEY = "container.nuke_fstbmb"
ORIGINAL_CONTAINER_KEY, ORIGINAL_TILE_KEY = "container.nukeFstbmb", "tile.nuke_fstbmb.name"
GUARD = "        if(packet.tag == null) return;"
GUARD_COMMENT = "        // readNbt() yields null for an empty (TAG_End) payload; drop it before any receiver sees it, as the original NBTControlPacket does."
DECODE = "return new CompoundTagControl(buf.readNbt(), buf.readBlockPos());"
ENCODE = "buf.writeNbt(packet.tag);"
TYPE = 'new Type<>(NuclearTechMod.withDefaultNamespace("compound_tag_control"))'
REGISTER = "registrar.playToServer(CompoundTagControl.TYPE, CompoundTagControl.STREAM_CODEC, CompoundTagControl::handleServer);"
ICR_LINES = ("boolean hasPermission(Player player);", "void receiveControl(CompoundTag tag);", "default void receiveControl(Player player, CompoundTag tag) { }")
HANDLE = "public static void handleServer(CompoundTagControl packet, IPayloadContext context)"
ITEM_GUARD_COMMENT = "        // readNbt() yields null for an empty (TAG_End) payload; drop it before any receiver sees it, as the original NBTItemControlPacket does."
ITEM_HANDLE = "public static void handleServer(CompoundTagItemControl packet, IPayloadContext context)"
ITEM_DECODE = "return new CompoundTagItemControl(buf.readNbt());"
ITEM_TYPE = 'new Type<>(NuclearTechMod.withDefaultNamespace("compound_tag_item_control"))'
ITEM_REGISTER = "registrar.playToServer(CompoundTagItemControl.TYPE, CompoundTagItemControl.STREAM_CODEC, CompoundTagItemControl::handleServer);"
IICR_LINE = "void receiveControl(Player player, ItemStack stack, CompoundTag tag);"
ITEM_SENDERS = ("com/hbm/inventory/screens/FluidScreen.java", "com/hbm/inventory/screens/SatCoordScreen.java", "com/hbm/inventory/screens/ToolAbilityScreen.java")
SENDER = "new CompoundTagItemControl("

# The 26 files declaring `void receiveControl(` when this batch was written (all relative to src/main/java/com/hbm).
INTERFACES = ("interfaces/IControlReceiver.java", "items/IItemControlReceiver.java")
BLOCK_ENTITIES = (
    "blockentity/bomb/NukeBalefireBlockEntity.java", "blockentity/network/RadioTorchBaseBlockEntity.java",
    "blockentity/machine/MachineAssemblyMachineBlockEntity.java", "blockentity/machine/MachineArcWelderBlockEntity.java",
    "blockentity/machine/MachineChemicalPlantBlockEntity.java", "blockentity/machine/MachineCrucibleBlockEntity.java",
    "blockentity/machine/heater/HeaterElectricBlockEntity.java", "blockentity/machine/heater/HeaterHeatexBlockEntity.java",
    "blockentity/machine/MachineDieselBlockEntity.java", "blockentity/machine/MachineCompressorBlockEntity.java",
    "blockentity/machine/heater/HeaterOilburnerBlockEntity.java", "blockentity/machine/MachineMixerBlockEntity.java",
    "blockentity/machine/MachineCombustionEngineBlockEntity.java", "blockentity/machine/MachineRadarBlockEntity.java",
    "blockentity/machine/MachineSolderingStationBlockEntity.java", "blockentity/machine/MachineWoodBurnerBlockEntity.java",
    "blockentity/machine/SoyuzLauncherBlockEntity.java", "blockentity/machine/ReactorZirnoxBlockEntity.java",
    "blockentity/machine/storage/BarrelBlockEntity.java", "blockentity/machine/storage/MachineFluidTankBlockEntity.java",
    "blockentity/machine/storage/BatteryBaseBlockEntity.java",
)
ITEMS = ("items/tools/ToolAbilityItem.java", "items/machine/FluidIDMultiItem.java", "items/tools/SatInterfaceItem.java")
RECEIVER_FILES = tuple("com/hbm/" + p for p in INTERFACES + BLOCK_ENTITIES + ITEMS)
DECLARES = "void receiveControl("


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read(path):
    return norm(path.read_text(encoding="utf-8-sig"))


class Checks:
    def __init__(self):
        self.count = 0

    def __call__(self, condition, label):
        self.count += 1
        if not condition:
            raise AssertionError(label)


def unique_pairs(pairs):
    keys = [k for k, _ in pairs]
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    assert not dupes, f"duplicate JSON keys: {dupes[:5]}"
    return dict(pairs)


def load_json(text):
    return json.loads(text, object_pairs_hook=unique_pairs)


def lang_lines(text):
    """key=value lines of a .lang file with their 1-based line numbers."""
    return {line.split("=", 1)[0]: (n, line.split("=", 1)[1]) for n, line in enumerate(text.splitlines(), 1) if "=" in line and not line.startswith("#")}


# ---------------------------------------------------------------- inputs

def original_texts():
    head = subprocess.check_output(["git", "-c", "safe.directory=" + ORIGINAL.as_posix(), "rev-parse", "HEAD"], cwd=ORIGINAL).decode().strip()
    # --no-optional-locks: status must not refresh the original repository's index.
    status = subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + ORIGINAL.as_posix(), "status", "--porcelain=v1"], cwd=ORIGINAL).decode()
    assert head == ORIGINAL_HEAD and status == "", (head, status)
    return {p: read(ORIGINAL / p) for p in (ORIGINAL_PACKET, ORIGINAL_ITEM_PACKET, ORIGINAL_EN, ORIGINAL_ZH)}


def neo_texts():
    texts = {p: read(SOURCE / p) for p in (CTC, ICTC, NET, ICR, IICR, TAGS_UTIL, PROVIDER) + RECEIVER_FILES + ITEM_SENDERS}
    texts.update({p: read(ROOT / p) for p in (ZH, EN, MAP)})
    # Classes implementing IItemControlReceiver and files constructing the item control packet, anywhere in the tree.
    texts["implementingItem"] = sorted(p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob("*.java") if re.search(r"\bimplements\b[^{]*\bIItemControlReceiver\b", read(p)))
    # The packet's own codec constructs it from readNbt(); every other construction is a sender.
    texts["itemSenders"] = sorted(rel for rel in (p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob("*.java")) if rel != ICTC and SENDER in read(SOURCE / rel))
    # Any other source file declaring receiveControl would show up here as drift from the recorded 26.
    texts["declaring"] = sorted(p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob("*.java") if DECLARES in p.read_text(encoding="utf-8-sig"))
    # Every class that directly implements IControlReceiver, and every item class (so an item gaining IControlReceiver, which would make
    # CompoundTagControl's hand branch live, is seen even if it were added outside the recorded set).
    pattern = re.compile(r"\bimplements\b[^{]*\bIControlReceiver\b")
    texts["implementing"] = sorted(p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob("*.java") if pattern.search(read(p)))
    for p in (SOURCE / "com/hbm/items").rglob("*.java"):
        texts.setdefault(p.relative_to(SOURCE).as_posix(), read(p))
    return texts


def start_texts():
    return dict(ctc=read(START_CTC), ictc=read(START_ICTC), zh=read(START_ZH), map=read(START_MAP))


# ---------------------------------------------------------------- original (read-only)

def original_suite(original, check):
    packet = original[ORIGINAL_PACKET]
    handler = method(packet, "public IMessage onMessage(NBTControlPacket m, MessageContext ctx)")
    check(packet.count("if(nbt != null) {") == 1 and handler.count("receiveControl(") == 1, "original NBTControlPacket has one nbt != null test and one receiveControl call")
    guard = handler.index("if(nbt != null) {")
    check(handler.index("readNBTTagCompoundFromBuffer") < guard < handler.index("tile.receiveControl(p, nbt)"),
          "original guard sits between the NBT read and the only receiveControl call")
    check(handler.index("tile.hasPermission(p)") > guard, "original permission check is inside the guard")
    item = method(original[ORIGINAL_ITEM_PACKET], "public IMessage onMessage(NBTItemControlPacket m, MessageContext ctx)")
    check(original[ORIGINAL_ITEM_PACKET].count("if(nbt != null) {") == 1 and item.count("receiveControl(") == 1, "original NBTItemControlPacket has one nbt != null test and one receiveControl call")
    item_guard = item.index("if(nbt != null) {")
    check(item.index("readNBTTagCompoundFromBuffer") < item_guard < item.index(".receiveControl(p, held, nbt)"), "original item guard sits between the NBT read and the only receiveControl call")
    check(item_guard < item.index("p.getHeldItem()"), "original held-item lookup is inside the item guard")
    en, zh = lang_lines(original[ORIGINAL_EN]), lang_lines(original[ORIGINAL_ZH])
    check(zh[ORIGINAL_CONTAINER_KEY][1] == "野火炸弹" and zh[ORIGINAL_TILE_KEY][1] == "野火炸弹", "original zh container and tile names are both 野火炸弹")
    check(en[ORIGINAL_CONTAINER_KEY][1] == "Balefire Bomb" and en[ORIGINAL_TILE_KEY][1] == "Balefire Bomb", "original en container and tile names are both Balefire Bomb")
    unmatched = sorted(k for k in set(en) | set(zh) if k == "chem.balefire" or k.startswith("container.burntime"))
    check(not unmatched, f"original has no chem.balefire / container.burntime* key (record-only items): {unmatched}")
    return dict(original_container=[zh[ORIGINAL_CONTAINER_KEY][0], zh[ORIGINAL_TILE_KEY][0]], guard_line=packet[:packet.index("if(nbt != null)")].count("\n") + 1)


# ---------------------------------------------------------------- NEO static (A)

def control_suite(texts, start, check):
    text = texts[CTC]
    handle = method(text, HANDLE)
    check(handle.count(GUARD.strip()) == 1 and text.count(GUARD.strip()) == 1, "handleServer carries the null guard exactly once")
    check(handle.index(GUARD.strip()) < handle.index("context.enqueueWork"), "guard precedes enqueueWork")
    calls = [m.start() for m in re.finditer(r"\.receiveControl\(", handle)]
    check(len(calls) == 4 and all(c > handle.index(GUARD.strip()) for c in calls), f"all four receiveControl calls follow the guard: {len(calls)}")
    check(re.search(r"if\(packet\.tag == null\) return;", handle) is not None and "packet.pos == null" not in handle, "guard tests the tag and returns")
    check(handle.index(GUARD.strip()) < handle.index("player.level.getBlockEntity"), "no block entity is looked up for a null tag")
    check(text.count(DECODE) == 1 and text.count(ENCODE) == 1 and "buf.writeBlockPos(packet.pos);" in text, "codec unchanged: readNbt then readBlockPos, writeNbt then writeBlockPos")
    check(text.count(TYPE) == 1 and "public record CompoundTagControl(CompoundTag tag, BlockPos pos) implements CustomPacketPayload" in text, "payload type id and record components unchanged")
    check(texts[NET].count(REGISTER) == 1, "NtmNetwork still registers the payload playToServer with the same codec and handler")
    check(all(line in texts[ICR] for line in ICR_LINES), "IControlReceiver signatures unchanged")
    diff = [l for l in difflib.unified_diff(start["ctc"].splitlines(), text.splitlines(), lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    check(diff == ["+" + GUARD_COMMENT, "+" + GUARD, "+"], f"CompoundTagControl change from the frozen start is the comment, the guard and a blank line only: {diff}")
    return len(calls)


# ---------------------------------------------------------------- NEO static (C)

def item_control_suite(texts, start, check):
    text = texts[ICTC]
    handle = method(text, ITEM_HANDLE)
    guard = GUARD.strip()
    check(handle.count(guard) == 1 and text.count(guard) == 1, "item handleServer carries the null guard exactly once")
    check(handle.index(guard) < handle.index("context.enqueueWork"), "item guard precedes enqueueWork")
    calls = [m.start() for m in re.finditer(r"\.receiveControl\(", handle)]
    check(len(calls) == 1 and calls[0] > handle.index(guard), f"the only receiveControl call follows the guard: {len(calls)}")
    check(handle.index(guard) < handle.index("InventoryUtil.getItemsFromBothHands"), "no held item is read for a null tag")
    check(text.count(ITEM_DECODE) == 1 and text.count(ENCODE) == 1, "item codec unchanged: readNbt, writeNbt")
    check(text.count(ITEM_TYPE) == 1 and "public record CompoundTagItemControl(CompoundTag tag) implements CustomPacketPayload" in text,
          "item payload type id and record component unchanged")
    check(texts[NET].count(ITEM_REGISTER) == 1, "NtmNetwork still registers the item payload playToServer with the same codec and handler")
    check(texts[IICR].count(IICR_LINE) == 1, "IItemControlReceiver signature unchanged")
    diff = [l for l in difflib.unified_diff(start["ictc"].splitlines(), text.splitlines(), lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    check(diff == ["+" + ITEM_GUARD_COMMENT, "+" + GUARD, "+"], f"CompoundTagItemControl change from the frozen start is the comment, the guard and a blank line only: {diff}")
    check(texts["implementingItem"] == sorted("com/hbm/" + p for p in ITEMS),
          f"the classes implementing IItemControlReceiver anywhere in src/main/java are exactly the 3 recorded items: {texts['implementingItem']}")
    for rel in ITEMS:
        header = re.search(r"^(?:(?:public|abstract|final|sealed|non-sealed) )*class \w+.*?\{", texts["com/hbm/" + rel], re.M | re.S)
        check(header is not None and re.search(r"\bIItemControlReceiver\b", header[0]) is not None, f"{rel} implements IItemControlReceiver")
    # Senders: every construction passes a locally built tag, so the guard never drops a legitimate control.
    check(texts["itemSenders"] == sorted(ITEM_SENDERS), f"the packet is constructed only in the 3 recorded screens: {texts['itemSenders']}")
    sites = 0
    for rel in ITEM_SENDERS:
        screen = texts[rel]
        # The construction is the argument of PacketDistributor.sendToServer(...), so the statement ends with "));".
        for m in re.finditer(re.escape(SENDER) + r"(.*?)\)\);", screen):
            sites += 1
            arg = m[1].strip()
            if arg == "tag":
                check(re.search(r"CompoundTag tag = new CompoundTag\(\);", screen[:m.start()]) is not None, f"{rel}: tag sent is a locally built CompoundTag")
            else:
                check(arg == "TagsUtil.getCustomData(this.toolStack)", f"{rel}: unexpected packet argument {arg}")
    check(sites == 4, f"4 construction sites in total: {sites}")
    util = texts[TAGS_UTIL]
    check("return customData != null ? customData.copyTag() : new CompoundTag();" in util, "TagsUtil.getCustomData never returns null")
    return dict(item_receivers=list(ITEMS), sender_sites=sites)


def receiver_suite(texts, check):
    declaring = texts["declaring"]
    check(declaring == sorted(RECEIVER_FILES) and len(declaring) == 26,
          f"the 26 receiveControl declarations are exactly the recorded files (drift would need re-review): {declaring}")
    implementors = sorted(k for k, v in texts.items() if k.startswith("com/hbm/items/") and re.search(r"\bimplements\b[^{]*\bIControlReceiver\b", v))
    check(not implementors, f"no item implements IControlReceiver (the hand branch is dead; items use IItemControlReceiver): {implementors}")
    check(texts["implementing"] == sorted("com/hbm/" + p for p in BLOCK_ENTITIES),
          f"the classes directly implementing IControlReceiver anywhere in src/main/java are exactly the 21 recorded block entities: {texts['implementing']}")
    for rel in BLOCK_ENTITIES:
        header = re.search(r"^(?:(?:public|abstract|final|sealed|non-sealed) )*class \w+.*?\{", texts["com/hbm/" + rel], re.M | re.S)
        check(header is not None and re.search(r"\bIControlReceiver\b", header[0]) is not None, f"{rel} implements IControlReceiver")
    for rel in ITEMS:
        text = texts["com/hbm/" + rel]
        check("IItemControlReceiver" in text and "IControlReceiver" not in text.replace("IItemControlReceiver", ""), f"{rel} implements only IItemControlReceiver")
    check(texts["com/hbm/items/IItemControlReceiver.java"].count("void receiveControl(Player player, ItemStack stack, CompoundTag tag);") == 1, "item interface is the separate packet's contract")
    return dict(interfaces=list(INTERFACES), block_entities=list(BLOCK_ENTITIES), items=list(ITEMS))


# ---------------------------------------------------------------- NEO static (B)

def language_suite(original, texts, start, check):
    zh_orig = lang_lines(original[ORIGINAL_ZH])
    en_orig = lang_lines(original[ORIGINAL_EN])
    zh, en, entries = load_json(texts[ZH]), load_json(texts[EN]), load_json(texts[MAP])["entries"]
    start_zh, start_entries = load_json(start["zh"]), load_json(start["map"])["entries"]
    check(zh[KEY] == zh["block.hbmsntm.nuke_fstbmb"] == zh_orig[ORIGINAL_CONTAINER_KEY][1] == zh_orig[ORIGINAL_TILE_KEY][1] == "野火炸弹",
          "container name equals the block name and both original texts: 野火炸弹")
    check(start_zh[KEY] == "异火炸弹", "frozen start had the inconsistent 异火炸弹")
    entry = entries[KEY]
    check(entry == dict(kind="upstream", source_en=en_orig[ORIGINAL_CONTAINER_KEY][1], source_key=ORIGINAL_CONTAINER_KEY, source_zh=zh_orig[ORIGINAL_CONTAINER_KEY][1],
                        target_en=en[KEY], target_zh=zh[KEY]), f"map entry is upstream from container.nukeFstbmb with no local reason: {entry}")
    check(start_entries[KEY]["kind"] == "local" and start_entries[KEY]["target_zh"] == "异火炸弹", "frozen start map entry was local 异火炸弹")
    check(en[KEY] == "Balefire Bomb" and texts[PROVIDER].count(f'this.add("{KEY}", "Balefire Bomb");') == 1, "English container name unchanged and still from the provider")
    check({k: v for k, v in zh.items() if k != KEY} == {k: v for k, v in start_zh.items() if k != KEY} and set(zh) == set(start_zh), "zh_cn.json differs from the frozen start only at container.nuke_fstbmb")
    check({k: v for k, v in entries.items() if k != KEY} == {k: v for k, v in start_entries.items() if k != KEY} and set(entries) == set(start_entries),
          "zh_cn-map.json differs from the frozen start only at container.nuke_fstbmb")
    zh_lines = [l for l in difflib.unified_diff(start["zh"].splitlines(), texts[ZH].splitlines(), lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    check(zh_lines == [f'-  "{KEY}": "异火炸弹",', f'+  "{KEY}": "野火炸弹",'], f"zh_cn.json text diff is that one line: {zh_lines}")
    # chem.balefire and container.burntime.balefire (record-only, no original counterpart) are covered by the "only container.nuke_fstbmb differs" checks above.
    kinds = lambda e: {k: sum(1 for v in e.values() if v["kind"] == k) for k in ("upstream", "local", "deferred")}
    return dict(zh_keys=len(zh), map_entries=len(entries), kinds_start=kinds(start_entries), kinds_now=kinds(entries))


def static_suite(original, texts, start):
    check = Checks()
    facts = original_suite(original, check)
    facts["receiveControl_calls_after_guard"] = control_suite(texts, start, check)
    facts["receivers"] = receiver_suite(texts, check)
    facts["item_control"] = item_control_suite(texts, start, check)
    facts["language"] = language_suite(original, texts, start, check)
    return facts, check.count


def replace_once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def without_declaring(texts, rel):
    out = dict(texts)
    out["declaring"] = [p for p in texts["declaring"] if p != rel]
    return out


MUTATIONS = {
    # label: (target, mutate(text) -> text)
    "guard_removed": ("neo:" + CTC, lambda t: replace_once(t, GUARD_COMMENT + "\n" + GUARD + "\n\n", "")),
    "guard_does_not_return": ("neo:" + CTC, lambda t: replace_once(t, GUARD, "        if(packet.tag == null) { }")),
    "guard_tests_pos": ("neo:" + CTC, lambda t: replace_once(t, GUARD, "        if(packet.pos == null) return;")),
    "guard_moved_inside_lambda": ("neo:" + CTC, lambda t: replace_once(replace_once(t, GUARD + "\n\n", "\n"), "        context.enqueueWork(() -> {\n", "        context.enqueueWork(() -> {\n" + GUARD + "\n")),
    "guard_moved_before_hand_branch": ("neo:" + CTC, lambda t: replace_once(replace_once(t, GUARD + "\n\n", "\n"), "            List<ItemStack> stacks", "            if(packet.tag == null) return;\n            List<ItemStack> stacks")),
    "decode_normalises_null": ("neo:" + CTC, lambda t: replace_once(t, "buf.readNbt()", "java.util.Objects.requireNonNullElseGet(buf.readNbt(), CompoundTag::new)")),
    "type_id_changed": ("neo:" + CTC, lambda t: replace_once(t, '"compound_tag_control"', '"compound_tag_control_v2"')),
    "registered_client_bound": ("neo:" + NET, lambda t: replace_once(t, "registrar.playToServer(CompoundTagControl.TYPE", "registrar.playToClient(CompoundTagControl.TYPE")),
    "receiver_interface_changed": ("neo:" + ICR, lambda t: replace_once(t, "void receiveControl(CompoundTag tag);", "void receiveControl(@Nullable CompoundTag tag);")),
    "receiver_file_dropped": ("drift", lambda t: None),
    "receiver_file_added": ("drift+", lambda t: None),
    "item_implements_icr": ("neo:com/hbm/items/tools/SatInterfaceItem.java", lambda t: replace_once(t, "implements IScreenProvider, IItemControlReceiver", "implements IScreenProvider, IItemControlReceiver, IControlReceiver")),
    "original_guard_removed": ("original:" + ORIGINAL_PACKET, lambda t: replace_once(t, "if(nbt != null) {", "if(true) {")),
    "original_guard_after_call": ("original:" + ORIGINAL_PACKET, lambda t: replace_once(replace_once(t, "if(nbt != null) {", "{"), "tile.receiveControl(p, nbt);", "tile.receiveControl(p, nbt); if(nbt != null) { }")),
    # (C) CompoundTagItemControl
    "item_guard_removed": ("neo:" + ICTC, lambda t: replace_once(t, ITEM_GUARD_COMMENT + "\n" + GUARD + "\n\n", "")),
    "item_guard_does_not_return": ("neo:" + ICTC, lambda t: replace_once(t, GUARD, "        if(packet.tag == null) { }")),
    "item_guard_inverted": ("neo:" + ICTC, lambda t: replace_once(t, GUARD, "        if(packet.tag != null) return;")),
    "item_guard_moved_inside_lambda": ("neo:" + ICTC, lambda t: replace_once(replace_once(t, GUARD + "\n\n", "\n"), "        context.enqueueWork(() -> {\n", "        context.enqueueWork(() -> {\n" + GUARD + "\n")),
    "item_guard_moved_after_hand_lookup": ("neo:" + ICTC, lambda t: replace_once(replace_once(t, GUARD + "\n\n", "\n"), "            List<ItemStack> heldStacks", "            if(packet.tag == null) return;\n            List<ItemStack> heldStacks")),
    "item_decode_normalises_null": ("neo:" + ICTC, lambda t: replace_once(t, "buf.readNbt()", "java.util.Objects.requireNonNullElseGet(buf.readNbt(), CompoundTag::new)")),
    "item_type_id_changed": ("neo:" + ICTC, lambda t: replace_once(t, '"compound_tag_item_control"', '"compound_tag_item_control_v2"')),
    "item_registered_client_bound": ("neo:" + NET, lambda t: replace_once(t, "registrar.playToServer(CompoundTagItemControl.TYPE", "registrar.playToClient(CompoundTagItemControl.TYPE")),
    "item_interface_changed": ("neo:" + IICR, lambda t: replace_once(t, IICR_LINE, "void receiveControl(Player player, ItemStack stack, @Nullable CompoundTag tag);")),
    "item_implementor_text_dropped": ("neo:com/hbm/items/tools/SatInterfaceItem.java", lambda t: replace_once(t, "implements IScreenProvider, IItemControlReceiver", "implements IScreenProvider")),
    "item_implementor_dropped": ("drift_item", lambda t: None),
    "item_implementor_added": ("drift_item+", lambda t: None),
    "item_sender_added": ("drift_sender+", lambda t: None),
    "item_sender_passes_null": ("neo:com/hbm/inventory/screens/SatCoordScreen.java", lambda t: replace_once(t, "new CompoundTagItemControl(tag)", "new CompoundTagItemControl(null)")),
    "tagsutil_returns_null": ("neo:" + TAGS_UTIL, lambda t: replace_once(t, "return customData != null ? customData.copyTag() : new CompoundTag();", "return customData != null ? customData.copyTag() : null;")),
    "original_item_guard_removed": ("original:" + ORIGINAL_ITEM_PACKET, lambda t: replace_once(t, "if(nbt != null) {", "if(true) {")),
    "original_item_guard_after_call": ("original:" + ORIGINAL_ITEM_PACKET, lambda t: replace_once(replace_once(t, "if(nbt != null) {", "{"), "receiveControl(p, held, nbt);", "receiveControl(p, held, nbt); if(nbt != null) { }")),
    "original_container_zh_changed": ("original:" + ORIGINAL_ZH, lambda t: replace_once(t, "container.nukeFstbmb=野火炸弹", "container.nukeFstbmb=异火炸弹")),
    "zh_container_reverted": ("neo:" + ZH, lambda t: replace_once(t, f'"{KEY}": "野火炸弹"', f'"{KEY}": "异火炸弹"')),
    "zh_block_name_changed": ("neo:" + ZH, lambda t: replace_once(t, '"block.hbmsntm.nuke_fstbmb": "野火炸弹"', '"block.hbmsntm.nuke_fstbmb": "异火炸弹"')),
    "zh_other_key_changed": ("neo:" + ZH, lambda t: replace_once(t, '"chem.balefire": "异火生产"', '"chem.balefire": "野火生产"')),
    "map_entry_local_again": ("neo:" + MAP, lambda t: replace_once(t, '"source_key": "container.nukeFstbmb",', '"source_key": "container.nukeFstbmb", "reason": "x",')),
    "map_wrong_source_key": ("neo:" + MAP, lambda t: replace_once(t, '"source_key": "container.nukeFstbmb"', '"source_key": "tile.nuke_fstbmb.name"')),
    "map_other_entry_changed": ("neo:" + MAP, lambda t: replace_once(t, '"target_zh": "异火生产"', '"target_zh": "野火生产"')),
    "english_changed": ("neo:" + EN, lambda t: replace_once(t, f'"{KEY}": "Balefire Bomb"', f'"{KEY}": "Balefire Bomb "')),
    "provider_changed": ("neo:" + PROVIDER, lambda t: replace_once(t, f'this.add("{KEY}", "Balefire Bomb");', f'this.add("{KEY}", "Balefire Bomb ");')),
}


def static_mutations(original, texts, start):
    results = {}
    for label, (target, mutate) in MUTATIONS.items():
        o, t = dict(original), dict(texts)
        if target == "drift":
            t = without_declaring(t, "com/hbm/items/tools/ToolAbilityItem.java")
        elif target == "drift+":
            t["declaring"] = sorted(t["declaring"] + ["com/hbm/blockentity/machine/MachineNewBlockEntity.java"])
        elif target == "drift_item":
            t["implementingItem"] = [p for p in t["implementingItem"] if p != "com/hbm/items/tools/ToolAbilityItem.java"]
        elif target == "drift_item+":
            t["implementingItem"] = sorted(t["implementingItem"] + ["com/hbm/items/tools/NewControlItem.java"])
        elif target == "drift_sender+":
            t["itemSenders"] = sorted(t["itemSenders"] + ["com/hbm/inventory/screens/NewScreen.java"])
        else:
            side, path = target.split(":", 1)
            bucket = o if side == "original" else t
            bucket[path] = mutate(bucket[path])
        try:
            static_suite(o, t, start)
        except AssertionError as error:
            results[label] = str(error)[:200]
            continue
        raise RuntimeError(f"static mutation not detected: {label}")
    # The frozen start form of each production handler must fail the suite (this is the revert), one at a time and both together.
    for label, reverted in (("frozen_start_form", {CTC: "ctc"}), ("frozen_start_item_form", {ICTC: "ictc"}), ("frozen_start_both_forms", {CTC: "ctc", ICTC: "ictc"})):
        t = dict(texts)
        for path, key in reverted.items():
            t[path] = start[key]
        try:
            static_suite(original, t, start)
        except AssertionError as error:
            results[label] = str(error)[:200]
        else:
            raise RuntimeError(f"{label} not detected")
    return results


# ---------------------------------------------------------------- tree and stamp

def tree_checks(check):
    stamp = json.loads(read(ROOT / GEN_STAMP))
    inputs = stamp["inputs"]
    for rel in ("src/main/java/" + CTC, "src/main/java/" + ICTC, ZH):
        path = ROOT / rel
        data = norm(path.read_text(encoding="utf-8")).encode("utf-8")
        check(inputs.get(rel) == sha(data), f"stamp records the current {rel}")
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    check(sha((ROOT / EN).read_bytes()) == baseline[EN]["start_sha256"], "generated en_us.json unchanged by this batch")
    return dict(stamp_inputs=len(inputs), stamp_generated=len(stamp["generated"]))


# ---------------------------------------------------------------- JAR

INSN = re.compile(r"^\s*(\d+):\s+(\w+)\s*(.*?)\s*$")


def handle_bytecode(javap, class_bytes, where):
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_bytes(class_bytes)
    out = subprocess.run([str(javap), "-c", "-p", str(where)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    body = out[out.index("public static void handleServer("):]
    body = body[:body.index("\n\n")]
    insns = [(m[2], m[3]) for m in map(INSN.match, body.splitlines()) if m]
    return insns


def check_jar(check, jar, previous, javap, run_root):
    classes = (CLASS, ITEM_CLASS)
    with zipfile.ZipFile(jar) as built:
        data = {c: built.read(c) for c in classes}
        built_entries = {n: sha(built.read(n)) for n in built.namelist() if not n.endswith("/")}
        built_zh = built.read(ZH_IN_JAR)
    prefixes, class_hashes = {}, {}
    for c in classes:
        insns = handle_bytecode(javap, data[c], run_root / "jar" / Path(c).name)
        ops = [op for op, _ in insns]
        name = Path(c).stem
        check(ops[:4] == ["aload_0", "getfield", "ifnonnull", "return"] and "Field tag:" in insns[1][1], f"built {name}.handleServer starts aload_0, getfield tag, ifnonnull, return: {insns[:4]}")
        check("invokedynamic" in ops[4:], f"{name}: after the guard's return the non-null path still creates the enqueueWork lambda")
        prefixes[name], class_hashes[name] = ops[:4], sha(data[c])
    check(built_zh == (ROOT / ZH).read_bytes(), "packaged zh_cn.json is the source file, byte for byte")
    check("野火炸弹".encode() in built_zh and '"container.nuke_fstbmb": "野火炸弹"'.encode() in built_zh, "packaged zh_cn.json carries 野火炸弹 for the container")
    facts = dict(path=str(jar.relative_to(ROOT)) if jar.is_relative_to(ROOT) else str(jar), sha256=sha(jar.read_bytes()), bytes=jar.stat().st_size,
                 built_prefix=prefixes, class_sha256=class_hashes)
    if previous.is_file():
        with zipfile.ZipFile(previous) as old:
            old_entries = {n: sha(old.read(n)) for n in old.namelist() if not n.endswith("/")}
            old_classes = {c: old.read(c) for c in classes}
        controls = {}
        for c in classes:
            ops = [op for op, _ in handle_bytecode(javap, old_classes[c], run_root / "jar" / ("previous-" + Path(c).name))]
            check(ops[:4] != ["aload_0", "getfield", "ifnonnull", "return"], f"control (previous release {Path(c).stem}) has no leading guard: {ops[:4]}")
            controls[Path(c).stem] = ops[:4]
        changed = sorted(n for n in built_entries if n in old_entries and built_entries[n] != old_entries[n])
        added, removed = sorted(set(built_entries) - set(old_entries)), sorted(set(old_entries) - set(built_entries))
        check(changed == sorted([CLASS, ITEM_CLASS, ZH_IN_JAR]) and not added and not removed,
              f"JAR differs from the previous release in the two control classes and the Chinese file only: ~{changed} +{added} -{removed}")
        facts.update(previous=str(previous.relative_to(ROOT)) if previous.is_relative_to(ROOT) else str(previous), previous_sha256=sha(previous.read_bytes()),
                     control_prefix=controls, delta=dict(changed=changed, added=added, removed=removed))
    else:
        facts["previous"] = "absent: control and delta checks skipped"
    return facts


# ---------------------------------------------------------------- contracts

SOURCES_JAR = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"


def vanilla_contracts(check):
    """readNbt() returns null for TAG_End: the premise of the guard, from the 1.21.1/NeoForge source."""
    with zipfile.ZipFile(SOURCES_JAR) as archive:
        text = norm(archive.read("net/minecraft/network/FriendlyByteBuf.java").decode("utf-8"))
    check("    @Nullable\n    public CompoundTag readNbt() {\n        return readNbt(this);\n    }" in text, "FriendlyByteBuf.readNbt() is declared @Nullable")
    check("            Tag tag = NbtIo.readAnyTag(new ByteBufInputStream(buffer), nbtAccounter);\n            return tag.getId() == 0 ? null : tag;" in text,
          "FriendlyByteBuf.readNbt(buf, accounter) maps an End tag (id 0) to null")
    check("        if (tag != null && !(tag instanceof CompoundTag)) {\n            throw new DecoderException(\"Not a compound tag: \" + tag);\n        } else {\n            return (CompoundTag)tag;"
          in text, "FriendlyByteBuf.readNbt(buf) passes a null through and rejects non-compound tags")
    check("        if (nbt == null) {\n            nbt = EndTag.INSTANCE;\n        }" in text, "FriendlyByteBuf.writeNbt(null) writes an End tag, the one-byte empty payload")
    return dict(sources_jar=str(SOURCES_JAR.relative_to(ROOT)), sha256=sha(SOURCES_JAR.read_bytes()))


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jar", type=Path)
    parser.add_argument("--previous-jar", type=Path, default=PREVIOUS_JAR)
    parser.add_argument("--static-only", action="store_true", help="skip the cached-source contracts and the stamp check (usable before runData)")
    args = parser.parse_args()

    run_id = uuid.uuid4().hex
    run_root = BATCH / "verify" / run_id
    run_root.mkdir(parents=True)
    production = (CTC, ICTC, NET, ICR, IICR)
    before = {p: sha((SOURCE / p).read_bytes()) for p in production}

    original, texts, start = original_texts(), neo_texts(), start_texts()
    facts, static_count = static_suite(original, texts, start)
    mutations = static_mutations(original, texts, start)
    check = Checks()
    contracts = tree = None
    if not args.static_only:
        contracts = vanilla_contracts(check)
        tree = tree_checks(check)
    report = dict(run_id=run_id, original_head=ORIGINAL_HEAD, static_checks=static_count, mutations=mutations, mutation_count=len(mutations), facts=facts,
                  contracts=contracts, tree=tree, other_checks=check.count)
    if args.jar:
        java, javac = jdk()
        javap = javac.with_name(javac.name.replace("javac", "javap"))
        report["jar"] = check_jar(check, args.jar if args.jar.is_absolute() else ROOT / args.jar, args.previous_jar, javap, run_root)
        report["other_checks"] = check.count
    after = {p: sha((SOURCE / p).read_bytes()) for p in production}
    assert before == after, "production files changed during verification"
    (run_root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"static {static_count} + tree/contract/jar {report['other_checks']} checks passed; mutations {len(mutations)}/{len(mutations) } detected")
    print("receiveControl declaring files:", len(facts["receivers"]["interfaces"]) + len(facts["receivers"]["block_entities"]) + len(facts["receivers"]["items"]))
    print("IItemControlReceiver implementors:", len(facts["item_control"]["item_receivers"]), "| item packet send sites:", facts["item_control"]["sender_sites"])
    print("report:", (run_root / "report.json").relative_to(ROOT))


if __name__ == "__main__":
    main()
