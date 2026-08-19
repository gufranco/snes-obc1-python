#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>

typedef uint8_t uint8;
typedef uint16_t uint16;
typedef uint32_t uint32;
typedef int32_t int32;

struct SOBC1 {
    uint16 address;
    uint16 basePtr;
    uint16 shift;
};

struct SOBC1 OBC1;

static uint8 OBC1RAM[0x2000];

struct FakeMemory {
    uint8 *OBC1RAM;
};

static struct FakeMemory Memory = { OBC1RAM };

#include "obc1_bodies.inc"

int main(void) {
    char line[128];
    memset(OBC1RAM, 0xFF, sizeof(OBC1RAM));
    S9xResetOBC1();

    while (fgets(line, sizeof(line), stdin)) {
        char verb[16];
        long first = 0, second = 0;
        if (sscanf(line, "%15s %li %li", verb, &first, &second) < 1) continue;

        if (!strcmp(verb, "reset")) {
            memset(OBC1RAM, 0xFF, sizeof(OBC1RAM));
            S9xResetOBC1();
        } else if (!strcmp(verb, "reset-keeping")) {
            S9xResetOBC1();
        } else if (!strcmp(verb, "poke")) {
            OBC1RAM[first % 0x2000] = (uint8)second;
        } else if (!strcmp(verb, "r")) {
            printf("%02X\n", S9xGetOBC1((uint16)first));
        } else if (!strcmp(verb, "w")) {
            S9xSetOBC1((uint8)second, (uint16)first);
        } else if (!strcmp(verb, "dump")) {
            for (int at = 0; at < 0x2000; at++) printf("%02X", OBC1RAM[at]);
            printf("\n");
        } else if (!strcmp(verb, "state")) {
            printf("%04X %04X %04X\n", OBC1.basePtr, OBC1.address, OBC1.shift);
        }
    }
    return 0;
}
