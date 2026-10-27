"""Join rendered chapters, lay the ducked music bed under them, level to YouTube loudness, write chapters + .srt.

  python assemble.py edited_videos/<video> 1080 v1   -> <video>/<video>-v1.mp4, <video>/extras/{chapters.txt, <video>.srt}

Chapter renders already carry voice + SFX; only the music is added here (ducked against the voice stem,
-10 dB, 2.6 kHz dip, 2 s fade in / 3 s fade out), then loudnorm to -14 LUFS, -1.5 dBTP.
"""
import json, os, subprocess, sys
V = os.path.abspath(sys.argv[1]); res, tag = sys.argv[2], sys.argv[3]; name = os.path.basename(V)
B = os.path.join(V, '_work', 'build'); R = os.path.join(V, '_work', 'renders', res)
cfg = json.load(open(os.path.join(B, 'plan.json'), encoding='utf-8')); CH = json.load(open(os.path.join(B, 'chapters.json')))
tmp = os.path.join(V, '_work', 'renders', f'_tmp_{res}'); os.makedirs(tmp, exist_ok=True)
def run(*a): subprocess.run(a, check=True)
def dur(f): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).decode())
lst = os.path.join(tmp, 'list.txt')
open(lst, 'w').write(''.join(f"file '{os.path.join(R, f'ch{c['n']}.mp4').replace(os.sep, '/')}'\n" for c in CH))
joined = os.path.join(tmp, 'joined.mp4'); run('ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', joined)
T = dur(joined)
key = os.path.join(tmp, 'voice-key.wav')
ins = sum([['-i', os.path.join(B, f'ch{c["n"]}', 'voice.wav')] for c in CH], [])
run('ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ''.join(f'[{i}:a]' for i in range(len(CH))) + f'concat=n={len(CH)}:v=0:a=1[o]', '-map', '[o]', '-ar', '48000', key)
music = os.path.join(V, cfg['music']); out = os.path.join(V, f'{name}-{tag}.mp4')
fc = (f'[1:a]atrim=0:{T:.3f},asetpts=PTS-STARTPTS,volume=-10dB,equalizer=f=2600:t=q:w=1.2:g=-5[m];'
      f'[m][2:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[d];'
      f'[d]afade=t=in:d=2,afade=t=out:st={T - 3:.3f}:d=3[bed];'
      f'[0:a][bed]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]')
run('ffmpeg', '-v', 'error', '-y', '-i', joined, '-i', music, '-i', key, '-filter_complex', fc,
    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-movflags', '+faststart', out)
ex = os.path.join(V, 'extras'); os.makedirs(ex, exist_ok=True)
def mmss(t): return '%d:%02d' % (t // 60, t % 60)
open(os.path.join(ex, 'chapters.txt'), 'w').write('\n'.join(f"{mmss(c['g0'])} {c['name']}" for c in CH) + '\n')
def tc(t): return '%02d:%02d:%02d,%03d' % (t // 3600, t % 3600 // 60, t % 60, round((t % 1) * 1000) % 1000)
lines, k = [], 1
for c in CH:
    for a, b, t in json.load(open(os.path.join(B, f"ch{c['n']}", 'subs.json'), encoding='utf-8')):
        lines.append(f"{k}\n{tc(c['g0'] + a)} --> {tc(c['g0'] + b)}\n{t}\n"); k += 1
open(os.path.join(ex, f'{name}.srt'), 'w', encoding='utf-8').write('\n'.join(lines))
print(f'{out}  {dur(out):.2f}s')
