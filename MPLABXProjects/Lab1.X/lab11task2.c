#include <xc.h>
#include <stdint.h>

// Configuration Bits for 80 MHz System Clock (adjust POSCMOD if using internal FRC with PLL)
#pragma config FNOSC    = PRIPLL     // Primary Oscillator with PLL
#pragma config POSCMOD  = XT         // Primary Oscillator Mode (XT or HS)
#pragma config FPLLIDIV = DIV_2      // PLL Input Divider (2x divider)
#pragma config FPLLMUL  = MUL_20     // PLL Multiplier (20x multiplier)
#pragma config FPLLODIV = DIV_1      // System PLL Output Clock Divider (1x divider)
#pragma config FWDTEN   = OFF        // Watchdog Timer Disabled

#define SYS_FREQ 80000000UL

void msDelay(uint32_t ms) {
    // Core timer ticks at half the system frequency (SYS_FREQ / 2)
    uint32_t target_ticks = ms * (SYS_FREQ / 2000);
     _CP0_SET_COUNT(0);
    while (_CP0_GET_COUNT() < target_ticks);
}

int main(void) {
    // Optional: Configure cache / flash wait states for 80 MHz performance
    // (If your specific family supports BMX/Chester/Prefetch)
    
    TRISA = 0xFFE1; 
    LATA = 0x0000;  

    while (1) {
        LATA = 0x001E;
        msDelay(1000); // Should now take precisely 1 second
        LATA = 0x0000;
        msDelay(50); // Should now take precisely 3 seconds

        LATA = 0x001E;
        msDelay(500);  
        LATA = 0x0000;
        msDelay(3000);

        // --- Sequence 2
        LATA = 0x001E;
        msDelay(1000); 
        LATA = 0x0000;
        msDelay(50);

        LATA = 0x001E;
        msDelay(500);  
        LATA = 0x0000;
        msDelay(50);

        LATA = 0x001E;
        msDelay(500);  
        LATA = 0x0000;
        msDelay(50);

        LATA = 0x001E;
        msDelay(500);  
        LATA = 0x0000;
        msDelay(3000);

        // --- Sequence 3
        LATA = 0x001E;
        msDelay(1000); 
        LATA = 0x0000;
        msDelay(50);

        LATA = 0x001E;
        msDelay(500);  
        LATA = 0x0000;
        msDelay(50);

        LATA = 0x001E;
        msDelay(1000); 
        LATA = 0x0000;
        msDelay(50);

        LATA = 0x001E;
        msDelay(500);  
        LATA = 0x0000;
        msDelay(3000);
    }

    return 0;
}