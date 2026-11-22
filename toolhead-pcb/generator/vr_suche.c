// SPDX-License-Identifier: GPL-3.0-or-later
/* [Fassung 7, 12i] Kern des Gitter-Routers (A*, 8 Richtungen, Lagenwechsel über Vias) für kopfplatine.py.
   Gleiche Kosten wie die Python-Fassung _vr_weg: gerade 1, diagonal 1,4142, Via via_k (3 mm in Rasterzellen); dazu je Zelle die Zusatzkosten
   kosten[] (Ripup-Strafe bzw. Stau-Kosten der Verhandlung) und je Via-Platz kosten_via[]. Zielzellen sind immer betretbar. Übersetzt vom Generator selbst (gcc -O2 -shared -fPIC). */
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#include <float.h>

typedef struct { double f, g; int32_t idx; } knoten;
typedef struct { knoten *a; int64_t n, cap; } haufen;

static int hp_push(haufen *h, knoten k) {
    if (h->n == h->cap) {
        int64_t c = h->cap ? h->cap * 2 : 65536;
        knoten *na = realloc(h->a, (size_t)c * sizeof(knoten));
        if (!na) return -1;
        h->a = na; h->cap = c;
    }
    int64_t i = h->n++;
    while (i > 0) {
        int64_t p = (i - 1) / 2;
        if (h->a[p].f <= k.f) break;
        h->a[i] = h->a[p]; i = p;
    }
    h->a[i] = k;
    return 0;
}

static knoten hp_pop(haufen *h) {
    knoten top = h->a[0], last = h->a[--h->n];
    int64_t i = 0;
    for (;;) {
        int64_t l = 2 * i + 1, r = l + 1, m = i;
        double fm = last.f;
        if (l < h->n && h->a[l].f < fm) { m = l; fm = h->a[l].f; }
        if (r < h->n && h->a[r].f < fm) { m = r; }
        if (m == i) break;
        h->a[i] = h->a[m]; i = m;
    }
    if (h->n) h->a[i] = last;
    return top;
}

/* karte/straf/start/ziel: nl*ny*nx (uint8), viamask: ny*nx. Ergebnis: pfad (l,i,j)-Tripel vom Start zum Ziel,
   Rückgabe Knotenzahl, -1 = kein Weg, -2 = Speicher, -3 = Pfadpuffer zu klein. */
int vr_suche(int nl, int nx, int ny, const uint8_t *karte, const float *kosten, const float *kosten_via,
             const uint8_t *viamask, int mit_via, const uint8_t *start, const uint8_t *ziel,
             int fx0, int fy0, int fx1, int fy1, int zi0, int zi1, int zj0, int zj1,
             int32_t *pfad, int max_pfad, double via_k) {
    int64_t n = (int64_t)nl * nx * ny, ebene = (int64_t)nx * ny;
    double *dist = malloc((size_t)n * sizeof(double));
    int32_t *vor = malloc((size_t)n * sizeof(int32_t));
    uint8_t *fertig = calloc((size_t)n, 1);
    haufen h = {0, 0, 0};
    int erg = -1;
    if (!dist || !vor || !fertig) { erg = -2; goto ende; }
    for (int64_t k = 0; k < n; k++) { dist[k] = DBL_MAX; vor[k] = -1; }
    if (fx0 < 0) fx0 = 0;
    if (fy0 < 0) fy0 = 0;
    if (fx1 > nx - 1) fx1 = nx - 1;
    if (fy1 > ny - 1) fy1 = ny - 1;
#define REST(i, j) hypot((double)((zi0 - (i)) > 0 ? (zi0 - (i)) : (((i) - zi1) > 0 ? ((i) - zi1) : 0)), \
                         (double)((zj0 - (j)) > 0 ? (zj0 - (j)) : (((j) - zj1) > 0 ? ((j) - zj1) : 0)))
    for (int64_t k = 0; k < n; k++) {
        if (start[k]) {
            int i = (int)(k % nx), j = (int)((k / nx) % ny);
            dist[k] = 0.0;
            knoten q = {REST(i, j), 0.0, (int32_t)k};
            if (hp_push(&h, q)) { erg = -2; goto ende; }
        }
    }
    static const int di[8] = {1, -1, 0, 0, 1, 1, -1, -1}, dj[8] = {0, 0, 1, -1, 1, -1, 1, -1};
    static const double dc[8] = {1.0, 1.0, 1.0, 1.0, 1.4142, 1.4142, 1.4142, 1.4142};
    int32_t ende_k = -1;
    while (h.n) {
        knoten q = hp_pop(&h);
        if (q.g > dist[q.idx] || fertig[q.idx]) continue;
        fertig[q.idx] = 1;
        if (ziel[q.idx]) { ende_k = q.idx; break; }
        int s = (int)(q.idx / ebene), j = (int)((q.idx % ebene) / nx), i = (int)(q.idx % nx);
        const uint8_t *k = karte + (int64_t)s * ebene;
        for (int r = 0; r < 8; r++) {
            int a = i + di[r], b = j + dj[r];
            if (a < fx0 || a > fx1 || b < fy0 || b > fy1) continue;
            int64_t nk = (int64_t)s * ebene + (int64_t)b * nx + a;
            if (!ziel[nk]) {
                if (k[(int64_t)b * nx + a]) continue;
                if (di[r] && dj[r] && (k[(int64_t)j * nx + a] || k[(int64_t)b * nx + i])) continue;
            }
            double nd = q.g + dc[r];
            if (kosten) nd += kosten[nk];
            if (nd < dist[nk]) {
                dist[nk] = nd; vor[nk] = q.idx;
                knoten m = {nd + REST(a, b), nd, (int32_t)nk};
                if (hp_push(&h, m)) { erg = -2; goto ende; }
            }
        }
        if (mit_via && viamask[(int64_t)j * nx + i]) {
            double zus = kosten_via ? kosten_via[(int64_t)j * nx + i] : 0.0;
            for (int l = 0; l < nl; l++) {
                if (l == s) continue;
                int64_t nk = (int64_t)l * ebene + (int64_t)j * nx + i;
                double nd = q.g + via_k + zus;
                if (nd < dist[nk]) {
                    dist[nk] = nd; vor[nk] = q.idx;
                    knoten m = {nd + REST(i, j), nd, (int32_t)nk};
                    if (hp_push(&h, m)) { erg = -2; goto ende; }
                }
            }
        }
    }
    if (ende_k >= 0) {
        int cnt = 0;
        for (int32_t k = ende_k; k >= 0; k = vor[k]) cnt++;
        if (cnt > max_pfad) { erg = -3; goto ende; }
        int pos = cnt - 1;
        for (int32_t k = ende_k; k >= 0; k = vor[k], pos--) {
            pfad[3 * pos] = (int32_t)(k / ebene);
            pfad[3 * pos + 1] = (int32_t)(k % nx);
            pfad[3 * pos + 2] = (int32_t)((k % ebene) / nx);
        }
        erg = cnt;
    }
ende:
    free(dist); free(vor); free(fertig); free(h.a);
    return erg;
}
