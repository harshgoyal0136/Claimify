"""Clean medical-report (discharge summary) PDFs → data/docs/clean/medical_<n>.pdf + .json.
Same writer and sidecar format as invoices.py.
Usage: python scripts/gen/medical.py [--n 50]
"""
import argparse
import datetime as dt
import random

from invoices import NAMES, Page, money, save

HOSPITALS = [("St. Anne's Multispeciality Hospital", ("F1", "F2"), "%d/%m/%Y", "Microsoft Word 2016"),
             ("Riverside Trauma & Ortho Centre", ("F3", "F4"), "%Y-%m-%d", "HIS Report Server 4.2"),
             ("Lotus Medical Institute", ("F1", "F2"), "%d %b %Y", "Crystal Reports")]
DIAGNOSES = [("S82.0", "Fracture of patella"), ("S52.5", "Fracture of lower end of radius"),
             ("S06.0", "Concussion"), ("S13.4", "Sprain of ligaments of cervical spine"),
             ("S43.0", "Dislocation of shoulder joint"), ("S22.3", "Fracture of rib"),
             ("S83.5", "Sprain of cruciate ligament of knee")]
CHARGES = [("Room charges (per day)", 4500), ("Consultation", 1500), ("X-ray", 1200),
           ("CT scan", 6500), ("Surgery", 45000), ("Physiotherapy session", 900),
           ("Pharmacy", 3800), ("Nursing (per day)", 1800)]


def report(i, rng):
    name, (reg, bold), datefmt, producer = rng.choice(HOSPITALS)
    adm = dt.date(2026, 1, 1) + dt.timedelta(days=rng.randrange(0, 230))
    dis = adm + dt.timedelta(days=rng.randint(1, 9))
    code, dx = rng.choice(DIAGNOSES)
    p, L = Page(), 50
    p.text(L, 780, 16, bold, name, "hospital")
    p.text(L, 760, 12, bold, "DISCHARGE SUMMARY")
    p.text(L, 730, 10, reg, "Patient: " + rng.choice(NAMES), "patient")
    p.text(L, 716, 10, reg, f"Age: {rng.randint(18, 80)}    UHID: {rng.randrange(10**7, 10**8)}", "uhid")
    p.text(L, 702, 10, reg, "Admitted: " + adm.strftime(datefmt), "admission_date")
    p.text(L, 688, 10, reg, "Discharged: " + dis.strftime(datefmt), "discharge_date")
    p.text(L, 660, 10, bold, "Diagnosis")
    p.text(L, 646, 10, reg, f"{dx} (ICD-10 {code})", "diagnosis")
    p.text(L, 618, 10, bold, "Charges")
    p.line(L, 612, 545, 612)
    y, total = 612, 0
    for k, (desc, unit) in enumerate(rng.sample(CHARGES, rng.randint(3, 6))):
        amt = round(unit * rng.uniform(0.8, 1.3), -1) * (dis - adm).days if "per day" in desc \
            else round(unit * rng.uniform(0.8, 1.3), -1)
        y -= 18
        p.text(L, y, 10, reg, desc, f"item{k}_desc")
        p.text(450, y, 10, reg, money(amt), f"item{k}_amount")
        total += amt
    p.line(L, y - 8, 545, y - 8)
    p.text(330, y - 26, 10, bold, "Total (INR)")
    p.text(450, y - 26, 10, bold, money(total), "total")
    p.text(L, 100, 9, reg, "Attending physician: Dr. " + rng.choice(NAMES).split()[1])
    created = dt.datetime.combine(dis, dt.time(rng.randrange(10, 20), rng.randrange(60)))
    return p, producer, created, {"icd10": code}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    n = ap.parse_args().n
    for i in range(n):
        save(f"medical_{i:04d}", *report(i, random.Random(f"medical/{i}")))
    print(f"wrote {n} medical reports")


if __name__ == "__main__":
    main()
