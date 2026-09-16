#include <xc.h>
#include <stdint.h>

#define FSY 80000000UL // System Clock = 80 MHz

void __delay_ms(uint32_t ms) {
    uint32_t start_count = _CP0_GET_COUNT();
    uint32_t target_duration = (FSY / 2000) * ms;
    while ((_CP0_GET_COUNT() - start_count) < target_duration);
}

int main(void) {
    TRISA = 0xFFE1; 
    LATA = 0x0000;  

    while (1) {
        LATA = 0x001E;
        __delay_ms(1000); // Long
        LATA = 0x0000;
        __delay_ms(3000);

        LATA = 0x001E;
        __delay_ms(500);  // Short
        LATA = 0x0000;
        __delay_ms(3000);

        // --- Sequence 2
        LATA = 0x001E;
        __delay_ms(1000); // Long
        LATA = 0x0000;
        __delay_ms(3000);

        LATA = 0x001E;
        __delay_ms(500);  // Short 1
        LATA = 0x0000;
        __delay_ms(3000);

        LATA = 0x001E;
        __delay_ms(500);  // Short 2
        LATA = 0x0000;
        __delay_ms(3000);

        LATA = 0x001E;
        __delay_ms(500);  // Short 3
        LATA = 0x0000;
        __delay_ms(3000);

        // --- Sequence 3
        LATA = 0x001E;
        __delay_ms(1000); // Long
        LATA = 0x0000;
        __delay_ms(3000);

        LATA = 0x001E;
        __delay_ms(500);  // Short
        LATA = 0x0000;
        __delay_ms(3000);

        LATA = 0x001E;
        __delay_ms(1000); // Long
        LATA = 0x0000;
        __delay_ms(3000);

        LATA = 0x001E;
        __delay_ms(500);  // Short
        LATA = 0x0000;
        __delay_ms(3000);
    }

    return 0;
}