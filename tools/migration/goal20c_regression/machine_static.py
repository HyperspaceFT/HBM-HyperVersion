"""Goal20C static freeze of the spent fuel pool drum against the original (read-only): MachineWasteDrumBlockEntity, MachineWasteDrumBlock,
MachineWasteDrumMenu, MachineWasteDrumScreen, FuelPoolRecipes and the client-only boundaries. Every check takes `ck(condition, label)` and
source text, so verify_goal20c_machine.py can run the same function on an edited copy and expect its AssertionError."""
import re

ORIGINAL_TE = 'src/main/java/com/hbm/tileentity/machine/TileEntityWasteDrum.java'
ORIGINAL_BLOCK = 'src/main/java/com/hbm/blocks/machine/WasteDrum.java'
ORIGINAL_CONTAINER = 'src/main/java/com/hbm/inventory/container/ContainerWasteDrum.java'
ORIGINAL_GUI = 'src/main/java/com/hbm/inventory/gui/GUIWasteDrum.java'
ORIGINAL_FUELPOOL = 'src/main/java/com/hbm/inventory/recipes/FuelPoolRecipes.java'
ORIGINAL_MODBLOCKS = 'src/main/java/com/hbm/blocks/ModBlocks.java'
ORIGINAL_FILES = (ORIGINAL_TE, ORIGINAL_BLOCK, ORIGINAL_CONTAINER, ORIGINAL_GUI, ORIGINAL_FUELPOOL, ORIGINAL_MODBLOCKS)

BE = 'com/hbm/blockentity/machine/MachineWasteDrumBlockEntity.java'
BLOCK = 'com/hbm/blocks/machine/MachineWasteDrumBlock.java'
MENU = 'com/hbm/inventory/menus/MachineWasteDrumMenu.java'
SCREEN = 'com/hbm/inventory/screens/MachineWasteDrumScreen.java'
FUELPOOL = 'com/hbm/inventory/recipes/FuelPoolRecipes.java'
SYNC = 'com/hbm/inventory/recipes/FuelPoolRecipeSync.java'
CLIENT_SYNC = 'com/hbm/handler/FuelPoolRecipeClientSync.java'
PACKET = 'com/hbm/network/toclient/FuelPoolRecipesPacket.java'
JEI = 'com/hbm/handler/jei/FuelPoolRecipeHandler.java'
JEI_PLUGIN = 'com/hbm/handler/jei/NtmJeiPlugin.java'
ITEM = 'com/hbm/items/machine/DepletedFuelItem.java'
BLOCKS = 'com/hbm/blocks/NtmBlocks.java'
MENU_BASE = 'com/hbm/inventory/menus/MenuBase.java'
CLIENT = 'com/hbm/main/NuclearTechModClient.java'
NETWORK = 'com/hbm/network/NtmNetwork.java'
SERIALIZABLE = 'com/hbm/inventory/recipes/loader/SerializableRecipe.java'
SOURCES = (BE, BLOCK, MENU, SCREEN, FUELPOOL, SYNC, CLIENT_SYNC, PACKET, JEI, JEI_PLUGIN, ITEM, BLOCKS, MENU_BASE, CLIENT, NETWORK, SERIALIZABLE)

# Common (both sides) Goal20C classes: none may import or name client-only Minecraft classes.
COMMON = (BE, BLOCK, MENU, FUELPOOL, SYNC, PACKET, ITEM)
FORBIDDEN_IN_DRUM = ('ChunkRadiationManager', 'HazardSystem', 'RadiationSavedData', 'playSound', 'SoundEvent', 'NtmSoundEvents', 'ContaminationUtil', 'addParticle')


def lf(text): return text.replace('\r\n', '\n')


def body(text, signature):
    """The method text from `signature` (exactly once) through its matching brace."""
    text = lf(text)
    count = text.count(signature)
    if count != 1: raise AssertionError(f'{signature!r} found {count} times (need 1)')
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: return text[start:i + 1]
    raise AssertionError('unbalanced braces after ' + signature)


def one(text, needle): return lf(text).count(needle) == 1


def original_facts(read):
    """read(rel) -> original text. Parsed facts with line numbers."""
    te = lf(read(ORIGINAL_TE)); te_lines = te.split('\n')
    def line(text_lines, needle):
        hits = [i + 1 for i, l in enumerate(text_lines) if needle in l]
        if len(hits) != 1: raise AssertionError(f'original {needle!r} on {len(hits)} lines')
        return hits[0]
    update = body(te, 'public void updateEntity() {')
    facts = {
        'slot_count': int(re.search(r'slots = new ItemStack\[(\d+)\];', te).group(1)),
        'stack_limit': int(re.search(r'getInventoryStackLimit\(\) \{\s*return (\d+);', te).group(1)),
        'face_slots': [int(x) for x in re.search(r'slots_arr = new int\[\] \{([^}]*)\}', te).group(1).split(',')],
        'decay_expr': re.search(r'int r = ([0-9 *]+) / water;', update).group(1).strip(),
        'directions': 'ForgeDirection.VALID_DIRECTIONS' in update,
        'water_blocks': 'Blocks.water' in update and 'Blocks.flowing_water' in update,
        'roll': 'worldObj.rand.nextInt(r) == 0' in update,
        'non_null_slot': 'if(slots[i] != null) {' in update,
        'server_only': 'if(!worldObj.isRemote) {' in update,
        'water_gate': 'if(water > 0) {' in update,
        'no_mark_dirty': 'markDirty' not in update,
        'extract_rule': '!FuelPoolRecipes.recipes.containsKey(new ComparableStack(getStackInSlot(i)))' in body(te, 'public boolean canExtractItem('),
        'update_lines': f'{ORIGINAL_TE}:{line(te_lines, "public void updateEntity() {")}-{line(te_lines, "public void updateEntity() {") + update.count(chr(10))}',
        'decay_line': line(te_lines, 'int r = 60 * 60 * 20 / water;'),
    }
    facts['decay_ticks'] = eval(facts['decay_expr'], {'__builtins__': {}})
    container = lf(read(ORIGINAL_CONTAINER))
    facts['slots_xy'] = [(int(i), int(x), int(y)) for i, x, y in re.findall(r'new Slot\(tedf, (\d+), (\d+), (\d+)\)', container)]
    m = re.search(r'new Slot\(invPlayer, j \+ i \* 9 \+ 9, 8 \+ j \* 18, (\d+) \+ i \* 18 \+ (\d+)\)', container)
    facts['player_inv_y'] = int(m.group(1)) + int(m.group(2))
    m = re.search(r'new Slot\(invPlayer, i, 8 \+ i \* 18, (\d+) \+ (\d+)\)', container)
    facts['hotbar_y'] = int(m.group(1)) + int(m.group(2))
    facts['shift_click_checks_extract'] = 'canExtractItem' in container
    gui = lf(read(ORIGINAL_GUI))
    facts['gui_size'] = (int(re.search(r'this\.xSize = (\d+);', gui).group(1)), int(re.search(r'this\.ySize = (\d+);', gui).group(1)))
    facts['info_stat'] = re.search(r'this\.drawCustomInfoStat\(mouseX, mouseY, (guiLeft - 16, guiTop \+ 36, 16, 16, guiLeft - 8, guiTop \+ 36 \+ 16), text\);', gui).group(1)
    facts['info_panel'] = re.search(r'this\.drawInfoPanel\((guiLeft - 16, guiTop \+ 36), 16, 16, (\d+)\);', gui).groups()
    facts['info_lines'] = re.findall(r'"([^"]+)"', re.search(r'String\[\] text = new String\[\] \{(.*?)\};', gui, re.S).group(1))
    facts['gui_texture'] = re.search(r'":textures/gui/(\w+\.png)"', gui).group(1)
    block = lf(read(ORIGINAL_BLOCK))
    tick = body(block, 'public void randomDisplayTick(')
    facts['particles_skip_down'] = 'if(dir == ForgeDirection.DOWN)' in tick and 'continue;' in tick
    facts['particle'] = re.search(r'world\.spawnParticle\("(\w+)", ix, iy, iz, ([\d.]+), ([\d.]+), ([\d.]+)\);', tick).groups()
    facts['block_textures'] = re.findall(r'registerIcon\(RefStrings\.MODID \+ ":(\w+)"\)', block)
    mb = lf(read(ORIGINAL_MODBLOCKS))
    m = re.search(r'machine_waste_drum = new WasteDrum\(Material\.iron\)\.setBlockName\("machine_waste_drum"\)\.setHardness\(([\d.]+)F\)\.setResistance\(([\d.]+)F\)', mb)
    facts['strength'] = (float(m.group(1)), float(m.group(2)))
    fp = lf(read(ORIGINAL_FUELPOOL))
    facts['fuelpool_file'] = re.search(r'return "(hbm\w+\.json)";', fp).group(1)
    return facts


def check_original(facts, ck):
    ck(facts['slot_count'] == 12 and facts['stack_limit'] == 1 and facts['face_slots'] == list(range(12)),
       'original TileEntityWasteDrum: 12 slots, stack limit 1, every face exposes 0..11 (:27-32, :82-84, :173-175)')
    ck(facts['decay_expr'] == '60 * 60 * 20' and facts['decay_ticks'] == 72000 and facts['decay_line'] == 206, 'original r = 60 * 60 * 20 / water = 72000 / water (:206)')
    ck(all(facts[k] for k in ('directions', 'water_blocks', 'roll', 'non_null_slot', 'server_only', 'water_gate', 'no_mark_dirty', 'extract_rule')),
       'original updateEntity: server only, six VALID_DIRECTIONS water/flowing_water, water > 0 gate, a roll per non-null slot, no markDirty; canExtractItem refuses table keys')
    ck(len(facts['slots_xy']) == 12 and [s[0] for s in facts['slots_xy']] == list(range(12)) and facts['player_inv_y'] == 107 and facts['hotbar_y'] == 165
       and not facts['shift_click_checks_extract'], 'original ContainerWasteDrum: 12 slots, player inventory y 107, hotbar 165, transferStackInSlot ignores canExtractItem')
    ck(facts['gui_size'] == (176, 189) and facts['info_panel'][1] == '2' and len(facts['info_lines']) == 3 and facts['gui_texture'] == 'gui_waste_drum.png',
       'original GUIWasteDrum: 176x189, gui_waste_drum.png, info panel type 2 at guiLeft - 16, guiTop + 36, three hard-coded lines')
    ck(facts['particles_skip_down'] and facts['particle'] == ('bubble', '0.0', '0.2', '0.0') and facts['block_textures'] == ['waste_drum', 'waste_drum_side'],
       'original WasteDrum: bubbles (0, 0.2, 0) next to water except below; icons waste_drum (top/bottom) and waste_drum_side')
    ck(facts['strength'] == (5.0, 10.0) and facts['fuelpool_file'] == 'hbmFuelpool.json', 'original machine_waste_drum hardness 5, resistance 10 (ModBlocks.java:2276); table file hbmFuelpool.json')


def check_block_entity(text, facts, ck):
    t = lf(text)
    decay = re.search(r'public static final int DECAY_TICKS = (\d+);', t)
    ck(decay is not None and int(decay.group(1)) == facts['decay_ticks'], f'DECAY_TICKS equals the original 60 * 60 * 20 = {facts["decay_ticks"]}')
    ck(one(t, f'/** Original updateEntity (:{facts["decay_line"]}): 60 * 60 * 20 ticks with one water neighbour, divided by the number of water neighbours. */\n    public static final int DECAY_TICKS'),
       f'the DECAY_TICKS javadoc cites the original formula at :{facts["decay_line"]}')
    ck(one(t, 'public static final int SLOT_COUNT = 12;') and int(re.search(r'SLOT_COUNT = (\d+);', t).group(1)) == facts['slot_count'], '12 slots (SLOT_COUNT)')
    slots = re.search(r'private static final int\[\] SLOTS = \{([^}]*)\};', t)
    ck(slots is not None and [int(x) for x in slots.group(1).split(',')] == facts['face_slots'], 'SLOTS is 0..11 like the original slots_arr')
    ck(one(t, '@Override public int[] getSlotsForFace(Direction direction) { return SLOTS; }'), 'every face exposes SLOTS (no face filter)')
    ck(one(t, '@Override public int getMaxStackSize() { return 1; }'), 'slot stack limit 1')
    ck(one(t, '@Override public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction) { return !this.isKey(this.getItem(slot)); }'),
       'automation extraction refuses a slot whose content is a table key (the original reads getStackInSlot(i), not the passed stack)')
    place = body(t, 'public boolean canPlaceItem(int slot, ItemStack stack) {')
    ck('return !stack.isEmpty() && this.isKey(stack);' in place, 'canPlaceItem accepts table keys only')
    ck(one(t, '@Override public boolean canPlaceItemThroughFace(int slot, ItemStack stack, @Nullable Direction direction) { return this.getItem(slot).isEmpty() && this.canPlaceItem(slot, stack); }'),
       'automation fills only empty slots with table keys, the same on every face (a vanilla hopper stacked 14 into slot 0 otherwise; NEO-only guard)')
    update = body(t, 'public void updateEntity() {')
    lines = [l.strip() for l in update.split('\n') if l.strip() and not l.strip().startswith('//')]
    ck(lines[1] == 'if(this.level == null || this.level.isClientSide) return;', 'updateEntity returns on the client first (original !worldObj.isRemote)')
    ck('int water = this.countWater();' in lines and 'if(water <= 0) return;' in lines, 'no water: no roll (original water > 0 gate)')
    ck('int r = DECAY_TICKS / water;' in lines, 'r = DECAY_TICKS / water (integer division, :206)')
    ck('for(int i = 0; i < SLOT_COUNT; i++) {' in lines and 'if(stack.isEmpty()) continue;' in lines, 'the loop visits all twelve slots and skips only empty ones')
    loop = update[update.index('for(int i = 0; i < SLOT_COUNT; i++) {'):]
    roll_at = loop.index('this.random().nextInt(r) == 0')
    ck(loop.count('continue;') == 1 and loop.index('if(stack.isEmpty()) continue;') < roll_at and 'isKey' not in loop[:roll_at],
       'every non-empty slot rolls, cool waste included (no key filter before the roll, original :210-218)')
    ck('ItemStack output = FuelPoolRecipes.getOutput(stack);' in lines and 'if(output != null) {' in lines and 'this.slots.set(i, output.copyWithCount(1));' in lines,
       'a roll of 0 replaces a table key with one copy of the row output; a non-key stays')
    ck(lines.count('changed = true;') == 1 and lines[-2] == 'if(changed) this.setChanged();' and t.count('setChanged()') == 1,
       'setChanged only after a replacement, once per tick (NEO-only; the original never marked the drum dirty)')
    water = body(t, 'public int countWater() {')
    wl = [l.strip() for l in water.split('\n') if l.strip()]
    ck('for(Direction dir : Direction.values()) {' in wl and 'continue;' not in water.replace('if(!this.level.isLoaded(neighbour)) continue;', ''),
       'countWater looks at all six Directions (DOWN included, original VALID_DIRECTIONS)')
    ck(wl.index('if(!this.level.isLoaded(neighbour)) continue;') < wl.index('Fluid fluid = this.level.getFluidState(neighbour).getType();'),
       'an unloaded neighbour is skipped before its fluid state is read')
    ck('if(fluid == Fluids.WATER || fluid == Fluids.FLOWING_WATER) water++;' in wl, 'water = fluid state WATER or FLOWING_WATER (waterlogged blocks count, local interpretation)')
    ck(one(t, 'public void setDecayRandom(@Nullable RandomSource random) {') and 'return this.decayRandom != null ? this.decayRandom : this.level.random;' in t,
       'setDecayRandom is the public test hook; the level random is used otherwise')
    key = body(t, 'private boolean isKey(ItemStack stack) {')
    ck('this.level != null && this.level.isClientSide ? FuelPoolRecipeClientSync.isKey(stack) : FuelPoolRecipes.isKey(stack)' in key,
       'the client asks the synced table, the server its own table')
    ck(t.count('FuelPoolRecipeClientSync.') == 1, 'FuelPoolRecipeClientSync is named only in the client branch of isKey')
    for forbidden in FORBIDDEN_IN_DRUM:
        ck(forbidden not in t, f'the drum block entity has no {forbidden} (no chunk radiation, sound or particles; original :191-229)')
    ck('Component.translatable("container.machine_waste_drum")' in body(t, 'protected Component getDefaultName() {'), 'default name container.machine_waste_drum')


def check_block(text, blocks_text, facts, ck):
    t = lf(text)
    m = re.search(r'MACHINE_WASTE_DRUM = register\("machine_waste_drum", \(\) -> new MachineWasteDrumBlock\(BlockBehaviour\.Properties\.of\(\)\.strength\(([\d.]+)F, ([\d.]+)F\)', lf(blocks_text))
    ck(m is not None and (float(m.group(1)), float(m.group(2))) == facts['strength'], f'machine_waste_drum strength {facts["strength"]} (hardness 5, resistance 10)')
    ck(one(blocks_text, 'MACHINE_WASTE_DRUM = register("machine_waste_drum", () -> new MachineWasteDrumBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F)'
                        '.sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops()));'),
       'machine_waste_drum requires the correct tool for drops (the original Material.iron requires a tool)')
    tick = body(t, 'public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {')
    head = t[:t.index('public void animateTick(')]
    ck(head.rstrip().endswith('@Override\n    @OnlyIn(Dist.CLIENT)'), 'animateTick is @OnlyIn(Dist.CLIENT)')
    ck('if(dir == Direction.DOWN) continue;' in tick and 'for(Direction dir : Direction.values()) {' in tick, 'bubbles skip the neighbour below (original :67-68)')
    ck('level.getFluidState(pos.relative(dir)).is(FluidTags.WATER)' in tick, 'bubbles next to water (original Material.water)')
    ck('level.addParticle(ParticleTypes.BUBBLE, ix, iy, iz, 0.0D, 0.2D, 0.0D);' in tick and t.count('addParticle') == 1, 'one BUBBLE particle with velocity (0, 0.2, 0) per water face, only in animateTick')
    remove = body(t, 'public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {')
    ck('Containers.dropContents(level, pos, container);' in remove and 'if(!state.is(newState.getBlock())) {' in remove, 'breaking the drum drops every slot')
    use = body(t, 'protected InteractionResult useWithoutItem(')
    ck('if(level.isClientSide) return InteractionResult.SUCCESS;' in use and 'if(!player.isShiftKeyDown()) {' in use and 'player.openMenu(' in use,
       'right click without sneaking opens the menu on the server (original :89-104)')
    ticker = body(t, 'public <T extends BlockEntity> BlockEntityTicker<T> getTicker(')
    ck('if(level.isClientSide) return null;' in ticker, 'no client ticker')
    for forbidden in ('ChunkRadiationManager', 'HazardSystem', 'playSound', 'net.minecraft.client'):
        ck(forbidden not in t, f'the drum block has no {forbidden}')


def check_menu(text, menu_base, facts, ck):
    t = lf(text)
    slots = [(int(i), int(x), int(y)) for i, x, y in re.findall(r'this\.addSlot\(new SlotNonRetarded\(be, (\d+), (\d+), (\d+)\)\);', t)]
    ck(slots == facts['slots_xy'], f'the twelve slot coordinates equal ContainerWasteDrum.java:19-30: {slots}')
    ck(one(t, f'this.playerInv(inventory, 8, {facts["player_inv_y"]});'), f'player inventory at x 8, y {facts["player_inv_y"]}')
    ck(one(lf(menu_base), 'this.playerInv(inventory, playerInvX, playerInvY, playerInvY + 58);') and facts['player_inv_y'] + 58 == facts['hotbar_y'],
       f'hotbar at y {facts["hotbar_y"]} (MenuBase default offset 58)')
    quick = body(menu_base, 'public ItemStack quickMoveStack(Player player, int index) {')
    ck('canTakeItemThroughFace' not in quick and 'this.moveItemStackTo(stack, be.getContainerSize(), this.slots.size(), true)' in quick
       and 'this.moveItemStackTo(stack, 0, be.getContainerSize(), false)' in quick,
       'shift-click moves through slot validity only; the player may take hot waste out (original transferStackInSlot)')


def check_screen(text, facts, ck):
    t = lf(text)
    ck(one(t, f'this.imageWidth = {facts["gui_size"][0]};') and one(t, f'this.imageHeight = {facts["gui_size"][1]};'), f'screen {facts["gui_size"][0]}x{facts["gui_size"][1]}')
    ck(one(t, 'this.drawCustomInfoStat(guiGraphics, mouseX, mouseY, this.leftPos - 16, this.topPos + 36, 16, 16, this.leftPos - 8, this.topPos + 36 + 16, info);'),
       'info hover area at leftPos - 16, topPos + 36 (16x16), tooltip at leftPos - 8, topPos + 52 (original :34)')
    ck(one(t, f'this.drawInfoPanel(guiGraphics, this.leftPos - 16, this.topPos + 36, {facts["info_panel"][1]});'), 'info panel type 2 at leftPos - 16, topPos + 36 (original :51)')
    ck(one(t, 'I18nUtil.resolveKeyArray("desc.gui.wasteDrum.info")'), 'the info text is the desc.gui.wasteDrum.info key')
    ck(one(t, f'"textures/gui/{facts["gui_texture"]}"'), 'background textures/gui/gui_waste_drum.png')
    ck('this.titleLabelY = 6;' in t and 'this.inventoryLabelY = this.imageHeight - 96 + 5;' in t, 'title at y 6, inventory label at imageHeight - 96 + 5 (original drawGuiContainerForegroundLayer)')


def check_fuelpool(text, serializable, facts, ck):
    t = lf(text)
    ck(one(t, f'@Override public String getFileName() {{ return "{facts["fuelpool_file"]}"; }}'), 'file name hbmFuelpool.json')
    ck(one(lf(serializable), 'import com.hbm.inventory.recipes.FuelPoolRecipes;') and one(lf(serializable), 'recipeHandlers.add(new FuelPoolRecipes());'),
       'FuelPoolRecipes is imported and in the SerializableRecipe handler list')
    ck(one(t, 'public static List<FuelPoolRecipe> readSnapshot(String json) { return readSnapshot(json, false); }'), 'the public snapshot reader (sync) is strict')
    stream = body(t, '@Override public void readRecipeStream(Reader reader) {')
    ck('List<FuelPoolRecipe> replacement = readSnapshot(text.toString(), true);' in stream and 'table.clear(); table.addAll(replacement);' in stream,
       'only the config-file path is lenient, and it replaces the table after the whole file parsed')
    guard = 'try { encodeSnapshot(writeRows(replacement)); }'
    ck(guard in stream and 'catch(IOException ex) { throw invalid("cannot write the sync snapshot: " + ex.getMessage()); }' in stream
       and 'catch(IllegalArgumentException ex) { throw invalid("the canonical sync snapshot of this file exceeds 256 KiB"); }' in stream
       and 0 <= stream.index(guard) < stream.index('table.clear(); table.addAll(replacement);'),
       'readRecipeStream encodes the canonical sync snapshot of the replacement rows before it replaces the table and rejects a file whose snapshot cannot be written')
    ck('if(lenient) handler.readRecipeLenient(rows.get(i), i);' in t and 'else handler.readRecipe(rows.get(i));' in t, 'lenient rows go through readRecipeLenient, strict rows through readRecipe')
    ck('String result = writeRows(RECIPES); readSnapshot(result); return result;' in body(t, 'public static String writeSnapshot() throws IOException {')
       and 'private static String writeRows(List<FuelPoolRecipe> rows) throws IOException {' in t, 'writeSnapshot = writeRows(RECIPES) plus the strict readSnapshot self-check')
    ck('return stack != null && !stack.isEmpty() && stack.getItem() == input && MetaHelper.getMeta(stack) == inputMeta;' in t, 'a row matches item and exact META')


def check_client_isolation(texts, ck):
    for rel in COMMON:
        t = lf(texts[rel])
        ck('import net.minecraft.client' not in t and 'Minecraft.getInstance' not in t and 'import com.mojang.blaze3d' not in t, f'{rel} names no client-only class')
    packet = lf(texts[PACKET])
    handle = body(packet, 'private static void handleClient(FuelPoolRecipesPacket packet) {')
    ck(packet.count('FuelPoolRecipeClientSync.') == 1 and 'FuelPoolRecipeClientSync.receive' in handle
       and packet[:packet.index('private static void handleClient(')].rstrip().endswith('@OnlyIn(Dist.CLIENT)'),
       'the packet reaches FuelPoolRecipeClientSync only from the @OnlyIn(Dist.CLIENT) handler')
    ck('context.enqueueWork(() -> handleClient(packet));' in packet, 'the payload handler defers to the client method on the main thread')
    ck(one(texts[CLIENT_SYNC], '@EventBusSubscriber(modid = NuclearTechMod.MODID, value = Dist.CLIENT)'), 'FuelPoolRecipeClientSync subscribes on the client only')
    ck(one(texts[SYNC], '@EventBusSubscriber(modid = NuclearTechMod.MODID)') and 'OnDatapackSyncEvent' in texts[SYNC] and 'FuelPoolRecipes.writeSnapshot()' in texts[SYNC],
       'the server sends the strict snapshot on datapack sync (login and reload)')
    ck(one(texts[NETWORK], 'registrar.playToClient(FuelPoolRecipesPacket.TYPE, FuelPoolRecipesPacket.STREAM_CODEC, FuelPoolRecipesPacket::handleCommon);'),
       'FuelPoolRecipesPacket is a play-to-client payload')
    client = lf(texts[CLIENT])
    ck(one(client, 'event.register(NtmMenuTypes.MACHINE_WASTE_DRUM.get(), MachineWasteDrumScreen::new);') and '@Mod(value = NuclearTechMod.MODID, dist = Dist.CLIENT)' in client,
       'the screen is registered from the client-only entry point')
    for rel in (BE, BLOCK, MENU, FUELPOOL, SYNC, PACKET, ITEM, CLIENT_SYNC):
        ck('MachineWasteDrumScreen' not in texts[rel] and 'FuelPoolRecipeHandler' not in texts[rel], f'{rel} does not name the screen or the JEI category')
    ck(one(texts[JEI], 'return Component.translatable("container.machine_waste_drum");'), 'the JEI category is titled container.machine_waste_drum')
    ck(one(texts[JEI_PLUGIN], 'new FuelPoolRecipeHandler(guiHelper),'), 'NtmJeiPlugin registers the fuel pool category')
