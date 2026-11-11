"""Independent check of the rebuilt 4-class dataset (counts from disk, val labels vs submission SCN_001, image bytes vs source)."""
import argparse, collections, hashlib, json, os

p = argparse.ArgumentParser()
p.add_argument("--data", required=True); p.add_argument("--ref-labels", required=True); p.add_argument("--src", required=True)
a = p.parse_args()
md5 = lambda f: hashlib.md5(open(f, "rb").read()).hexdigest()
res = {"splits": {}}
for s in ["train", "val", "test"]:
    idir, ldir = os.path.join(a.data, s, "images"), os.path.join(a.data, s, "labels")
    imgs, labs = os.listdir(idir), os.listdir(ldir)
    c = collections.Counter(); empty = 0
    for f in labs:
        ids = [int(l.split()[0]) for l in open(os.path.join(ldir, f)) if l.split()]
        c.update(ids); empty += not ids
    same_img = sum(md5(os.path.join(idir, f)) == md5(os.path.join(a.src, s, "images", f)) for f in imgs)
    res["splits"][s] = dict(images=len(imgs), labels=len(labs), stem_mismatch=len({x[:-4] for x in imgs} ^ {x[:-4] for x in labs}),
                            class_ids=sorted(c), boxes=dict(sorted(c.items())), total_boxes=sum(c.values()), empty_labels=empty,
                            images_md5_equal_source=same_img)
vl, rl = os.path.join(a.data, "val", "labels"), a.ref_labels
new, ref = set(os.listdir(vl)), set(os.listdir(rl))
norm = lambda f: sorted(tuple([l.split()[0]] + [f"{float(v):.6f}" for v in l.split()[1:]]) for l in open(f) if l.split())
byte_eq = sum(open(os.path.join(vl, f), "rb").read() == open(os.path.join(rl, f), "rb").read() for f in new & ref)
num_eq = sum(norm(os.path.join(vl, f)) == norm(os.path.join(rl, f)) for f in new & ref)
res["val_vs_submission_SCN_001"] = dict(new=len(new), ref=len(ref), common=len(new & ref), only_new=len(new - ref), only_ref=len(ref - new),
                                        byte_identical=byte_eq, numerically_identical=num_eq)
print(json.dumps(res, indent=1))
