/* LD_PRELOAD shim: when UTRP_SIM_SEED is set, feed a deterministic
 * splitmix64 stream to getrandom()/getentropy()/syscall(SYS_getrandom)
 * so rand::thread_rng() inside the untouched utrp theory code becomes
 * reproducible. Without the env var every call falls through to libc.
 *
 * Build: gcc -shared -fPIC -O2 -o libseedrandom.so seedrandom.c -ldl
 * Use:   UTRP_SIM_SEED=42 LD_PRELOAD=$PWD/libseedrandom.so utrp-sim ...
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

static int seeded = -1;          /* -1 unknown, 0 passthrough, 1 seeded */
static uint64_t state;

static void init(void) {
    const char *s = getenv("UTRP_SIM_SEED");
    if (s && *s) {
        state = 0x9e3779b97f4a7c15ULL ^ strtoull(s, NULL, 10);
        seeded = 1;
    } else {
        seeded = 0;
    }
}

static uint64_t splitmix64(void) {
    uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

static void fill(void *buf, size_t n) {
    unsigned char *p = buf;
    while (n) {
        uint64_t v = splitmix64();
        size_t k = n < 8 ? n : 8;
        memcpy(p, &v, k);
        p += k;
        n -= k;
    }
}

ssize_t getrandom(void *buf, size_t buflen, unsigned int flags) {
    if (seeded == -1) init();
    if (seeded) {
        fill(buf, buflen);
        return (ssize_t)buflen;
    }
    static ssize_t (*real)(void *, size_t, unsigned int);
    if (!real) real = dlsym(RTLD_NEXT, "getrandom");
    return real(buf, buflen, flags);
}

int getentropy(void *buf, size_t buflen) {
    if (seeded == -1) init();
    if (seeded) {
        fill(buf, buflen);
        return 0;
    }
    static int (*real)(void *, size_t);
    if (!real) real = dlsym(RTLD_NEXT, "getentropy");
    return real(buf, buflen);
}

long syscall(long number, ...) {
    va_list ap;
    long a[6];
    va_start(ap, number);
    for (int i = 0; i < 6; i++) a[i] = va_arg(ap, long);
    va_end(ap);
    if (number == SYS_getrandom) {
        if (seeded == -1) init();
        if (seeded) {
            fill((void *)a[0], (size_t)a[1]);
            return a[1];
        }
    }
    static long (*real)(long, long, long, long, long, long, long);
    if (!real) real = dlsym(RTLD_NEXT, "syscall");
    return real(number, a[0], a[1], a[2], a[3], a[4], a[5]);
}
