#include "control_tap.h"
#include <cstdlib>
#include <iostream>

void check(bool passed) { if (!passed) { std::cerr << "Ctrl tap invariant failed\n"; std::exit(1); } }

void cleanTap(unsigned modifier)
{
    ModifierTap tap(modifier);
    check(!tap.key(modifier, true, true));
    for (int i = 0; i < 100; ++i) check(!tap.key(modifier, true, true));
    check(tap.key(modifier, false, true));
    check(!tap.key(modifier, false, true));
    check(!tap.key(modifier, true, true));
    check(tap.key(modifier, false, true));
}

void combinations(unsigned modifier)
{
    for (unsigned other = 0; other < 256; ++other) {
        if (other == modifier) continue;
        for (bool otherFirst : {false, true}) {
            for (bool controlReleasedFirst : {false, true}) {
                ModifierTap tap(modifier);
                check(!tap.key(otherFirst ? other : modifier, true, true));
                check(!tap.key(otherFirst ? modifier : other, true, true));
                check(!tap.key(controlReleasedFirst ? modifier : other, false, true));
                check(!tap.key(controlReleasedFirst ? other : modifier, false, true));
                check(!tap.key(modifier, true, true));
                check(tap.key(modifier, false, true)); // Cancellation must not poison next tap.
            }
        }
    }
}

void lifecycle(unsigned modifier)
{
    ModifierTap tap(modifier);
    check(!tap.key(modifier, true, true));
    tap.cancel();
    check(!tap.key(modifier, false, true));
    check(!tap.key(modifier, true, false));
    check(!tap.key(modifier, false, true));
    check(!tap.key(modifier, true, true));
    check(!tap.key(modifier, false, false));
    std::array<bool, 256> snapshot{};
    snapshot[modifier] = true;
    tap.synchronize(snapshot);
    check(!tap.key(modifier, false, true)); // Held before focus entry.
    snapshot[modifier] = false;
    snapshot[99] = true;
    tap.synchronize(snapshot);
    check(!tap.key(modifier, true, true));
    check(!tap.key(99, false, true));
    check(!tap.key(modifier, false, true));
    check(!tap.key(modifier, true, true));
    check(!tap.key(999, true, true));
    check(!tap.key(modifier, false, true));
    ModifierTap unavailable(0);
    check(!unavailable.key(0, true, true));
    check(!unavailable.key(0, false, true));
}

int main()
{
    for (unsigned modifier : {37u, 50u}) { cleanTap(modifier); combinations(modifier); lifecycle(modifier); }
    std::cout << "PASS standalone/repeat, 2040 combination sequences (Ctrl and Shift), focus/disable/pre-held/invalid cases\n";
}
