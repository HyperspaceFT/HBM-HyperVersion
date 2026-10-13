"""Goal18A+18B cumulative package (Goal19A-0 Windows re-run): generated resources, imported assets and bilingual keys after runData.

verify_goal18a_resources.py checks the pre-runData tree (it records the pending generation it cannot perform); this check runs on the
generated tree and is what package_goal18b.py imports. It compares the generated resources with the Goal17B JAR and with the frozen
Goal19A start, so the only accepted generated changes are the four crystallizer files, the 23 English keys and the pickaxe tag (which
also carries the turbofan entry that GOAL17B.md records as fixed after the 17B JAR was packaged)."""
from pathlib import Path
import argparse, json, zipfile

from verify_goal18a_resources import ASSETS, JAVA as JAVA_18A, WIRING, EXPECTED_GENERATED_NEW, EXPECTED_GENERATED_CHANGED, read, sha, normalized_sha

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/migration/goal19a'
SOURCE = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
PREVIOUS = ROOT / 'build/migration/releases/goal17b/hbmsntm-198A-goal17b.jar'
ZH_INPUT = 'src/main/resources/assets/hbmsntm/lang/zh_cn.json'
JAVA = set(JAVA_18A)
GENERATED_NEW = set(EXPECTED_GENERATED_NEW)
GENERATED_CHANGED = set(EXPECTED_GENERATED_CHANGED)
OPTIONAL_GENERATED_CHANGED = set()
# Paths the Windows re-run itself may change relative to the frozen Goal19A start (records are listed by the packager).
EXPECTED_INPUTS = {
    'src/generated/resources/.migration-stamp.json',
    'tools/migration/verify_goal18a_resources.py',
    'tools/migration/verify_goal18b_resources.py',
    'tools/migration/package_goal18b.py',
}
NEW_18A_SOURCES = {'src/main/java/' + p + '.java' for p in JAVA_18A if p.rsplit('/', 1)[1].startswith(('MachineCrystallizer', 'Crystallizer', 'RenderCrystallizer'))}

def verify(source):
    checks = []
    def check(condition, label):
        if not condition: raise AssertionError(label)
        checks.append(label)
    generated = ROOT / 'src/generated/resources'
    start = read(OUT / 'baseline.json')
    owner = read(ROOT / 'migration/goal18a-resource-ownership.json')
    check({(a['source_path'], a['target_path']) for a in owner['assets']} == set(ASSETS), 'Asset ownership still covers exactly the four imported assets')
    for a in owner['assets']:
        target = ROOT / a['target_path']
        # Windows core.autocrlf checkout: acidizer.obj is CRLF while the record hashed the LF form (Goal 7B precedent).
        check(a['sha256'] in (sha(target), normalized_sha(target)), 'Imported asset matches its ownership record: ' + a['target_path'])
        if source is not None:
            check(a['sha256'] in (sha(source / a['source_path']), normalized_sha(source / a['source_path'])), 'Original asset still has the recorded content: ' + a['source_path'])
    for rel, needles in WIRING.items():
        text = (ROOT / 'src/main/java' / rel).read_text(encoding='utf-8')
        for needle in needles: check(needle in text, 'Registration path still includes the crystallizer: ' + rel + ' :: ' + needle.splitlines()[0])

    blockstate = read(generated / 'assets/hbmsntm/blockstates/machine_crystallizer.json')
    check(blockstate == {'variants': {'': {'model': 'hbmsntm:block/machine_crystallizer_particle'}}}, 'Generated blockstate points at the particle-only model')
    check(read(generated / 'assets/hbmsntm/models/block/machine_crystallizer_particle.json') == {'textures': {'particle': 'hbmsntm:block/machine_crystallizer'}}, 'Particle model uses the imported block texture')
    check((ROOT / 'src/main/resources/assets/hbmsntm/textures/block/machine_crystallizer.png').is_file(), 'Particle texture exists in the hand-written resources')
    check(read(generated / 'assets/hbmsntm/models/item/machine_crystallizer.json') == {'parent': 'minecraft:builtin/entity', 'gui_light': 'side'}, 'Item model is the built-in entity model like the turbofan')
    loot = read(generated / 'data/hbmsntm/loot_table/blocks/machine_crystallizer.json')
    check(loot['type'] == 'minecraft:block' and len(loot['pools']) == 1 and loot['pools'][0]['entries'] == [{'type': 'minecraft:item', 'name': 'hbmsntm:machine_crystallizer'}]
          and loot['pools'][0]['conditions'] == [{'condition': 'minecraft:survives_explosion'}], 'Loot table drops the machine itself (dropSelf)')
    pickaxe = read(generated / 'data/minecraft/tags/block/mineable/pickaxe.json')['values']
    check('hbmsntm:machine_crystallizer' in pickaxe and pickaxe.count('hbmsntm:machine_crystallizer') == 1, 'Pickaxe tag lists the crystallizer once')
    check('hbmsntm:machine_turbofan' in pickaxe, 'Pickaxe tag keeps the turbofan entry from the 17B review fix')

    review = read(ROOT / 'migration/goal18a-localization-review.json')
    en = read(generated / 'assets/hbmsntm/lang/en_us.json')
    zh = read(ROOT / ZH_INPUT)
    mapping = read(ROOT / 'migration/localization/zh_cn-map.json')['entries']
    check(len(review['new_keys']) == 23 and not review['modified_keys'], 'Review still lists 23 new keys and no modified keys')
    for key, entry in review['new_keys'].items():
        check(en.get(key) == entry['target_en'], 'Generated English carries the reviewed wording: ' + key)
        check(zh.get(key) == entry['target_zh'] and mapping.get(key) == entry, 'Chinese and mapping agree with the review: ' + key)
    for key, value in review['reviewed_related_existing_keys'].items():
        check(en.get(key) == value['target_en'] and zh.get(key) == value['target_zh'], 'Related bilingual identity retained: ' + key)
    check(len(en) == 2299 and len(zh) == 2191 and len(mapping) == 2299, 'English 2,299, Chinese 2,191 and mapping 2,299 keys')
    check(sum(1 for v in mapping.values() if v['kind'] == 'deferred') == 108, 'All 108 old localization deferrals retained, none added')

    stamp = read(generated / '.migration-stamp.json')
    stale = sorted(p for p, h in stamp['inputs'].items() if not (ROOT / p).is_file() or normalized_sha(ROOT / p) != h)
    check(not stale, 'Every recorded generation input matches the current tree')
    check(all(normalized_sha(generated / p) == h for p, h in stamp['generated'].items()), 'Every generated resource matches the stamp')
    java_now = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'src/main/java').rglob('*.java')}
    check(java_now <= set(stamp['inputs']), 'Every Java source is a recorded generation input')
    check(NEW_18A_SOURCES <= set(stamp['inputs']) and len(NEW_18A_SOURCES) == 10, 'The ten new Goal18A sources are recorded inputs')
    check({b for a, b in ASSETS} <= set(stamp['inputs']), 'The four imported assets are recorded inputs')
    check(len(stamp['generated']) == 4025, '4,025 generated resources (4,021 + the four crystallizer files)')

    start_stamp = read(OUT / 'baseline-files/src/generated/resources/.migration-stamp.json')
    with zipfile.ZipFile(PREVIOUS) as prior:
        prior_names = {i.filename for i in prior.infolist() if not i.is_dir()}
        generated_names = set(stamp['generated'])
        added = sorted(generated_names - prior_names)
        removed = sorted(set(start_stamp['generated']) - generated_names)
        changed = sorted(p for p in generated_names & prior_names if prior.read(p) != (generated / p).read_bytes())
    check(not removed, 'runData retired no generated resource')
    check(added == sorted(GENERATED_NEW), 'Relative to the 17B JAR only the four crystallizer files are new generated resources')
    check(changed == sorted(GENERATED_CHANGED), 'Relative to the 17B JAR only en_us.json and the pickaxe tag changed among generated resources')
    start_changed = sorted(p for p in generated_names if start['files'].get('src/generated/resources/' + p) != sha(generated / p))
    check(start_changed == sorted(GENERATED_NEW | GENERATED_CHANGED), 'Relative to the frozen Goal19A start runData changed exactly the expected six generated files')
    check(start['stamp_state']['generated_differing_from_goal17b_jar'] == ['data/minecraft/tags/block/mineable/pickaxe.json'], 'The start recorded the post-17B pickaxe fix as the only earlier JAR drift')

    result = dict(checks=len(checks), passed=checks, failures=[], english=len(en), chinese=len(zh), mapping=len(mapping), deferred=108,
                  generated_resources=len(stamp['generated']), generation_inputs=len(stamp['inputs']), added_vs_goal17b_jar=added, changed_vs_goal17b_jar=changed,
                  changed_since_goal19a_start=start_changed,
                  changed_inputs=sorted((set(stamp['inputs']) - set(start_stamp['inputs'])) | {p for p, h in start_stamp['inputs'].items() if stamp['inputs'].get(p) != h}),
                  source_compared=source is not None,
                  source_hashes={('src/main/java/' + p + '.java'): sha(ROOT / 'src/main/java' / (p + '.java')) for p in sorted(JAVA)},
                  asset_hashes={b: sha(ROOT / b) for a, b in ASSETS}, zh_sha256=sha(ROOT / ZH_INPUT),
                  evidence='Generated files, stamp, bilingual sources and imported asset bytes after the Windows runData; render, sound, save, GUI, multiplayer and server remain unverified.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'goal18b-resource-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--source', type=Path, default=None, help='original Hbm-s-Nuclear-Tech-GIT worktree for byte comparison')
    args = parser.parse_args()
    source = args.source if args.source else (SOURCE if SOURCE.is_dir() else None)
    result = verify(source)
    print(json.dumps({k: result[k] for k in ('checks', 'english', 'chinese', 'mapping', 'deferred', 'generated_resources', 'generation_inputs')}, ensure_ascii=False))
    print(json.dumps({k: result[k] for k in ('added_vs_goal17b_jar', 'changed_vs_goal17b_jar', 'changed_since_goal19a_start')}, ensure_ascii=False))
