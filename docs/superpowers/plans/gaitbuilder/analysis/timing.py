import sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality
ev, walk = quality.wb_eval("asd")
def t(g, label):
    best = 9
    for _ in range(3):
        t0 = time.time(); ev(g); best = min(best, time.time() - t0)
    print("%-40s %.3f s" % (label, best))
t({}, "defaults")
t({"balance": 0}, "balance off")
t({"balance": 0, "arm_drag": 0, "torso_drag": 0, "head_drag": 0}, "balance+springs off")
t({"balance": 0, "arm_drag": 0, "torso_drag": 0, "head_drag": 0, "foot_placement": 0}, "+ placement off")
