"""World settings of a solo run: the world drive.py created (newworld with --gamemode, --difficulty, --seed, --preset)
is the world the server runs, read on the server side; a misspelt preset is refused at the title screen.

Run it in a run of its own with the settings under test, for example
  drive.py run --run worldcheck --world accept-worldcheck --gamemode survival --difficulty normal --preset normal \\
      acceptance-executor/world_settings
A run without the options checks the defaults (creative, peaceful, seed 31, flat).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='acceptance-executor.world_settings',
    feature='acceptance-executor',
    title='World settings: game mode, difficulty, seed and terrain of the run\'s new world; a bad preset is refused',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

DIFFICULTY_ID = dict(peaceful=0, easy=1, normal=2, hard=3)
# WorldPresets.FLAT with the default flat layers: bedrock, two dirt, grass; the surface block is at y = -61
FLAT_SURFACE = -61


EXPECTED = (
    ('world-gamemode', 'the player is in the game mode the run asked for (client inventory state)'),
    ('world-difficulty', 'the server runs the difficulty the run asked for (`difficulty` query on the server)'),
    ('world-seed', 'the server\'s seed is the run\'s seed (`seed` on the server)'),
    ('world-terrain', 'flat preset: the player spawned on the flat surface; normal preset: above it, on generated terrain'),
    ('world-bad-preset', 'at the title screen a newworld step with a misspelt preset fails with "unknown preset" and creates no world'),
)


def expectations():
    return [dict(id='acceptance-executor.' + i, text=t, source='Steps.NewWorld') for i, t in EXPECTED]


def run(ctx):
    world = getattr(ctx.run, 'world', None) or {}
    if world.get('op') != 'newworld':
        for eid, _ in EXPECTED:
            ctx.not_run('acceptance-executor.' + eid, 'the run opened an existing world; its settings are not known to the run')
        return
    want_mode = world.get('gamemode', 'creative')
    inv = ctx.step('inv')
    ctx.check('acceptance-executor.world-gamemode', str(inv.get('game_mode', '')).lower() == want_mode,
              'client game mode %s, run asked for %s' % (inv.get('game_mode'), want_mode))
    difficulty = ctx.server('difficulty')
    want_difficulty = world.get('difficulty', 'peaceful')
    ctx.check('acceptance-executor.world-difficulty', difficulty['result'] == DIFFICULTY_ID[want_difficulty],
              'server difficulty id %s (%s), run asked for %s' % (difficulty['result'], ' / '.join(difficulty['messages']), want_difficulty))
    seed = ctx.server('seed')
    want_seed = world.get('seed', 31)
    text = ' '.join(seed['messages'])
    m = re.search(r'\[(-?\d+)\]', text)
    ctx.check('acceptance-executor.world-seed', bool(m) and int(m.group(1)) == int(want_seed),
              'server reply %r, run asked for %s' % (text[:120], want_seed))
    pos = _lib.data_value(ctx.server('data get entity @p Pos')['messages'][-1])
    flat = world.get('preset', 'flat') == 'flat'
    ok = abs(pos[1] - (FLAT_SURFACE + 1)) < 1.01 if flat else pos[1] > FLAT_SURFACE + 2
    ctx.check('acceptance-executor.world-terrain', ok, 'player at %s, preset %s' % ([round(c, 1) for c in pos], world.get('preset', 'flat')))
    # the title screen refuses a bad preset; the run's world is opened again afterwards
    ctx.step('leave')
    bad = ctx.step('newworld', world=world.get('name', 'x') + '-badpreset', preset='flatt', allow_fail=True)
    ctx.step('openworld', world=world.get('name'))
    ctx.check('acceptance-executor.world-bad-preset', bad.get('status') == 'fail' and 'unknown preset' in str(bad.get('reason')),
              'newworld preset=flatt: %s %s' % (bad.get('status'), bad.get('reason')))
