#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""[12p] Differenzielle Impedanz eines kantengekoppelten Paars auf L3 (JLC06161H-7628): quasi-statisch, 2D-Laplace
(finite Differenzen), homogenes Dielektrikum (Kern 0,4 mm über dem Paar, Prepreg 7628 darunter; εr gemittelt 4,5).
Bezug oben: GND-Lage L2 (0,4 mm). Unten zwei Fälle: (A) nächste Kupferfläche erst L5 (0,2028 + 0,0152 + 0,4 mm),
(B) Kupfer auf L4 direkt darunter (0,2028 mm).  Aufruf: zdiff_l3.py [Lücke mm]"""
import sys, numpy as np
EPS0, C0, ER, T = 8.854e-12, 2.998e8, 4.5, 0.0152
def zdiff(w, s, h_oben, h_unten, h=0.005, breite=4.0):
    nx, ny = int(breite / h) + 1, int((h_oben + T + h_unten) / h) + 1
    phi = np.zeros((ny, nx)); fest = np.zeros((ny, nx), bool)
    fest[0, :] = fest[-1, :] = True; fest[:, 0] = fest[:, -1] = True
    j0, j1 = int(round(h_oben / h)), int(round((h_oben + T) / h))
    mitte = breite / 2
    for vz, (a, b) in ((1.0, (mitte + s / 2, mitte + s / 2 + w)), (-1.0, (mitte - s / 2 - w, mitte - s / 2))):
        i0, i1 = int(round(a / h)), int(round(b / h))
        phi[j0:j1 + 1, i0:i1 + 1] = vz; fest[j0:j1 + 1, i0:i1 + 1] = True
    frei = ~fest
    J, I = np.indices(phi.shape)
    om = 2.0 / (1.0 + np.pi / max(nx, ny) * 2)          # Überrelaxation (Rot-Schwarz-SOR)
    for it in range(20000):
        d_max = 0.0
        for farbe in (0, 1):
            m = frei & (((I + J) & 1) == farbe)
            mittel = np.zeros_like(phi)
            mittel[1:-1, 1:-1] = 0.25 * (phi[2:, 1:-1] + phi[:-2, 1:-1] + phi[1:-1, 2:] + phi[1:-1, :-2])
            d = om * (mittel[m] - phi[m])
            phi[m] += d
            d_max = max(d_max, np.abs(d).max())
        if d_max < 2e-7:
            break
    gx, gy = np.diff(phi, axis=1), np.diff(phi, axis=0)
    c_odd = 0.5 * EPS0 * ((gx ** 2).sum() + (gy ** 2).sum())        # F/m je Ader gegen die Symmetrieebene (±1 V)
    return 2.0 / (C0 * np.sqrt(ER) * c_odd)
s = float(sys.argv[1]) if len(sys.argv) > 1 else 0.15
for name, hu in (("A  unten erst L5 (0,618 mm)", 0.618), ("B  Kupfer auf L4 (0,203 mm)", 0.2028)):
    print(name)
    for w in (0.15, 0.2, 0.25, 0.3, 0.35, 0.4):
        z = [zdiff(w, s, 0.4, hu, h) for h in (0.02, 0.01)]
        print(f"   Bahn {w:.2f} / Lücke {s:.2f} mm: Zdiff ≈ {2 * z[1] - z[0]:.0f} Ω  (Gitter 20 µm {z[0]:.0f}, 10 µm {z[1]:.0f})")
