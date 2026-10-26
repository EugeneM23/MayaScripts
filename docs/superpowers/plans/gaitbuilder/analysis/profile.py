import sys, os, cProfile, pstats, io
sys.path.insert(0, "C:/!!!Work/MayaScripts/docs/superpowers/plans/gaitbuilder")
import gates
ours, theirs, _ = gates.read(sys.argv[1] if len(sys.argv) > 1 else "asd")
ours.evaluate({})
pr = cProfile.Profile(); pr.enable()
for _ in range(3): ours.evaluate({})
pr.disable()
s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats(sys.argv[2] if len(sys.argv) > 2 else "tottime").print_stats(35); print(s.getvalue()[:7000])
